#!/usr/bin/env python3
"""Transactional outbox and idempotent inbox lab.

The application database and the simulated broker intentionally use separate
SQLite files. This makes the dangerous boundary visible: publishing to the
broker and marking the outbox row as published cannot be one local transaction.

The safe design uses:
- one transaction for business state plus outbox insertion
- at-least-once relay publication
- a stable event_id
- a consumer inbox table with a uniqueness constraint
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_APP_DB = Path("app.db")
DEFAULT_BROKER_DB = Path("broker.db")


@dataclass(frozen=True)
class Paths:
    app_db: Path
    broker_db: Path


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize(paths: Paths) -> None:
    with connect(paths.app_db) as app:
        app.executescript(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS outbox (
                event_id TEXT PRIMARY KEY,
                aggregate_type TEXT NOT NULL,
                aggregate_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                published_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_outbox_pending
                ON outbox(published_at, created_at);

            CREATE TABLE IF NOT EXISTS consumer_inbox (
                event_id TEXT PRIMARY KEY,
                consumer_name TEXT NOT NULL,
                processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS fulfillment (
                order_id TEXT PRIMARY KEY,
                state TEXT NOT NULL,
                source_event_id TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(source_event_id) REFERENCES consumer_inbox(event_id)
            );
            """
        )

    with connect(paths.broker_db) as broker:
        broker.executescript(
            """
            CREATE TABLE IF NOT EXISTS deliveries (
                delivery_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                published_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                consumed_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_deliveries_unconsumed
                ON deliveries(consumed_at, delivery_id);
            """
        )

    print(f"initialized application database: {paths.app_db}")
    print(f"initialized broker database:      {paths.broker_db}")


def reset(paths: Paths) -> None:
    for path in (paths.app_db, paths.broker_db):
        if path.exists():
            path.unlink()
            print(f"removed {path}")
    initialize(paths)


def create_order(
    paths: Paths, order_id: str, customer_id: str, amount_cents: int
) -> str:
    if amount_cents < 0:
        raise ValueError("amount_cents must not be negative")

    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "order_id": order_id,
        "customer_id": customer_id,
        "amount_cents": amount_cents,
        "status": "CREATED",
    }

    with connect(paths.app_db) as app:
        # The order and outbox row are one atomic local transaction.
        app.execute("BEGIN IMMEDIATE")
        app.execute(
            """
            INSERT INTO orders(order_id, customer_id, amount_cents, status)
            VALUES (?, ?, ?, 'CREATED')
            """,
            (order_id, customer_id, amount_cents),
        )
        app.execute(
            """
            INSERT INTO outbox(
                event_id, aggregate_type, aggregate_id, event_type, payload_json
            ) VALUES (?, 'order', ?, 'OrderCreated', ?)
            """,
            (event_id, order_id, json.dumps(payload, sort_keys=True)),
        )
        app.commit()

    print(f"created order {order_id} and outbox event {event_id} atomically")
    return event_id


def pending_outbox(app: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return list(
        app.execute(
            """
            SELECT event_id, event_type, payload_json
            FROM outbox
            WHERE published_at IS NULL
            ORDER BY created_at, event_id
            LIMIT ?
            """,
            (limit,),
        )
    )


def relay(
    paths: Paths,
    limit: int,
    crash_after_publish: bool,
    duplicate_each: int,
) -> int:
    if duplicate_each < 1:
        raise ValueError("duplicate_each must be at least 1")

    app = connect(paths.app_db)
    broker = connect(paths.broker_db)
    published_events = 0

    try:
        rows = pending_outbox(app, limit)
        if not rows:
            print("no pending outbox events")
            return 0

        for row in rows:
            event_id = row["event_id"]

            # Publishing is committed in the broker before the application
            # database marks the outbox row. A process crash in this gap causes
            # a duplicate publication on the next relay run.
            for _ in range(duplicate_each):
                broker.execute(
                    """
                    INSERT INTO deliveries(event_id, event_type, payload_json)
                    VALUES (?, ?, ?)
                    """,
                    (event_id, row["event_type"], row["payload_json"]),
                )
            broker.commit()
            print(
                f"published event {event_id} to broker "
                f"({duplicate_each} delivery row(s))"
            )

            if crash_after_publish:
                print(
                    "SIMULATED CRASH: broker commit succeeded, but outbox was not marked"
                )
                return 75

            app.execute(
                """
                UPDATE outbox
                SET published_at = CURRENT_TIMESTAMP
                WHERE event_id = ? AND published_at IS NULL
                """,
                (event_id,),
            )
            app.commit()
            published_events += 1
            print(f"marked outbox event {event_id} as published")

        return published_events
    finally:
        broker.close()
        app.close()


def unconsumed_deliveries(
    broker: sqlite3.Connection, limit: int
) -> list[sqlite3.Row]:
    return list(
        broker.execute(
            """
            SELECT delivery_id, event_id, event_type, payload_json
            FROM deliveries
            WHERE consumed_at IS NULL
            ORDER BY delivery_id
            LIMIT ?
            """,
            (limit,),
        )
    )


def process_delivery(
    app: sqlite3.Connection, row: sqlite3.Row, consumer_name: str
) -> bool:
    payload = json.loads(row["payload_json"])
    event_id = row["event_id"]
    order_id = payload["order_id"]

    try:
        app.execute("BEGIN IMMEDIATE")
        app.execute(
            """
            INSERT INTO consumer_inbox(event_id, consumer_name)
            VALUES (?, ?)
            """,
            (event_id, consumer_name),
        )
        app.execute(
            """
            INSERT INTO fulfillment(order_id, state, source_event_id)
            VALUES (?, 'READY', ?)
            ON CONFLICT(order_id) DO UPDATE SET
                state = excluded.state,
                source_event_id = excluded.source_event_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (order_id, event_id),
        )
        app.commit()
        print(
            f"processed delivery {row['delivery_id']} for event {event_id}; "
            f"fulfillment {order_id}=READY"
        )
        return True
    except sqlite3.IntegrityError:
        app.rollback()
        print(
            f"deduplicated delivery {row['delivery_id']}: "
            f"event {event_id} already exists in consumer inbox"
        )
        return False


def consume(paths: Paths, consumer_name: str, limit: int) -> tuple[int, int]:
    app = connect(paths.app_db)
    broker = connect(paths.broker_db)
    processed = 0
    duplicates = 0

    try:
        rows = unconsumed_deliveries(broker, limit)
        if not rows:
            print("no unconsumed broker deliveries")
            return 0, 0

        for row in rows:
            if process_delivery(app, row, consumer_name):
                processed += 1
            else:
                duplicates += 1

            broker.execute(
                """
                UPDATE deliveries
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE delivery_id = ?
                """,
                (row["delivery_id"],),
            )
            broker.commit()

        print(f"consumer result: processed={processed}, duplicates={duplicates}")
        return processed, duplicates
    finally:
        broker.close()
        app.close()


def rows_as_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, object]]:
    return [dict(row) for row in rows]


def show(paths: Paths) -> None:
    with connect(paths.app_db) as app, connect(paths.broker_db) as broker:
        state = {
            "orders": rows_as_dicts(
                app.execute("SELECT * FROM orders ORDER BY created_at, order_id")
            ),
            "outbox": rows_as_dicts(
                app.execute("SELECT * FROM outbox ORDER BY created_at, event_id")
            ),
            "broker_deliveries": rows_as_dicts(
                broker.execute("SELECT * FROM deliveries ORDER BY delivery_id")
            ),
            "consumer_inbox": rows_as_dicts(
                app.execute(
                    "SELECT * FROM consumer_inbox ORDER BY processed_at, event_id"
                )
            ),
            "fulfillment": rows_as_dicts(
                app.execute("SELECT * FROM fulfillment ORDER BY order_id")
            ),
        }
    print(json.dumps(state, indent=2, sort_keys=True))


def demo(paths: Paths) -> None:
    print("\n1. Reset databases")
    reset(paths)

    print("\n2. Create one order and its outbox event")
    create_order(paths, "order-1001", "customer-42", 12900)

    print("\n3. Publish, then crash before marking the outbox row")
    relay(paths, limit=10, crash_after_publish=True, duplicate_each=1)

    print("\n4. Restart relay; the same stable event is published again")
    relay(paths, limit=10, crash_after_publish=False, duplicate_each=1)

    print("\n5. Consume both broker deliveries")
    consume(paths, consumer_name="fulfillment-service", limit=100)

    print("\n6. Final state")
    show(paths)

    print(
        "\nExpected proof: two broker deliveries exist for one event_id, but the "
        "consumer inbox and fulfillment side effect contain one logical result."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app-db", type=Path, default=DEFAULT_APP_DB)
    parser.add_argument("--broker-db", type=Path, default=DEFAULT_BROKER_DB)

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init")
    subparsers.add_parser("reset")
    subparsers.add_parser("show")
    subparsers.add_parser("demo")

    create = subparsers.add_parser("create-order")
    create.add_argument("--order-id", required=True)
    create.add_argument("--customer-id", required=True)
    create.add_argument("--amount-cents", required=True, type=int)

    relay_parser = subparsers.add_parser("relay")
    relay_parser.add_argument("--limit", type=int, default=100)
    relay_parser.add_argument("--crash-after-publish", action="store_true")
    relay_parser.add_argument(
        "--duplicate-each",
        type=int,
        default=1,
        help="publish each stable event this many times",
    )

    consume_parser = subparsers.add_parser("consume")
    consume_parser.add_argument("--consumer", default="fulfillment-service")
    consume_parser.add_argument("--limit", type=int, default=100)

    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = Paths(app_db=args.app_db, broker_db=args.broker_db)

    try:
        if args.command == "init":
            initialize(paths)
        elif args.command == "reset":
            reset(paths)
        elif args.command == "create-order":
            initialize(paths)
            create_order(paths, args.order_id, args.customer_id, args.amount_cents)
        elif args.command == "relay":
            initialize(paths)
            result = relay(
                paths,
                limit=args.limit,
                crash_after_publish=args.crash_after_publish,
                duplicate_each=args.duplicate_each,
            )
            if result == 75:
                return 75
        elif args.command == "consume":
            initialize(paths)
            consume(paths, args.consumer, args.limit)
        elif args.command == "show":
            initialize(paths)
            show(paths)
        elif args.command == "demo":
            demo(paths)
        else:
            raise AssertionError(f"unhandled command: {args.command}")
    except (sqlite3.Error, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
