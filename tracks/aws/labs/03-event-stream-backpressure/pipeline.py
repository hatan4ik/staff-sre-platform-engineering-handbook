#!/usr/bin/env python3
"""Local event-stream lab for partitioning, backpressure, retries, and idempotency.

This models semantics rather than AWS API compatibility:
- bounded per-shard queues approximate Kinesis shard pressure
- router output queues approximate SQS work isolation
- SQLite inbox implements idempotent business effect
- bounded retry plus DLQ demonstrates poison-event handling
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sqlite3
import statistics
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    partition_key: str
    event_type: str
    produced_at: float
    payload: dict[str, Any]
    attempt: int = 0

    def with_attempt(self, attempt: int) -> "Event":
        return Event(
            event_id=self.event_id,
            partition_key=self.partition_key,
            event_type=self.event_type,
            produced_at=self.produced_at,
            payload=self.payload,
            attempt=attempt,
        )


@dataclass(slots=True)
class Metrics:
    produced: int = 0
    admitted: int = 0
    producer_backpressure: int = 0
    routed: int = 0
    processed: int = 0
    duplicates: int = 0
    retries: int = 0
    dlq: int = 0
    transient_failures: int = 0
    permanent_failures: int = 0
    shard_counts: list[int] = field(default_factory=list)
    latencies_ms: list[float] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        latency = self.latencies_ms
        return {
            "produced": self.produced,
            "admitted": self.admitted,
            "producer_backpressure": self.producer_backpressure,
            "routed": self.routed,
            "processed": self.processed,
            "duplicates": self.duplicates,
            "retries": self.retries,
            "dlq": self.dlq,
            "transient_failures": self.transient_failures,
            "permanent_failures": self.permanent_failures,
            "p50_latency_ms": round(statistics.median(latency), 2) if latency else None,
            "p95_latency_ms": round(percentile(latency, 0.95), 2) if latency else None,
            "p99_latency_ms": round(percentile(latency, 0.99), 2) if latency else None,
            "max_latency_ms": round(max(latency), 2) if latency else None,
            "shard_counts": self.shard_counts,
        }


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def stable_shard(partition_key: str, shard_count: int) -> int:
    digest = hashlib.sha256(partition_key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % shard_count


class Inbox:
    """SQLite-backed idempotency ledger and durable side-effect record."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection = sqlite3.connect(path)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS inbox (
                event_id TEXT PRIMARY KEY,
                partition_key TEXT NOT NULL,
                processed_at REAL NOT NULL,
                result TEXT NOT NULL
            )
            """
        )
        self.connection.commit()
        self._lock = asyncio.Lock()

    async def apply_once(self, event: Event, result: str) -> bool:
        async with self._lock:
            try:
                self.connection.execute(
                    "INSERT INTO inbox(event_id, partition_key, processed_at, result) VALUES (?, ?, ?, ?)",
                    (event.event_id, event.partition_key, time.time(), result),
                )
                self.connection.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) FROM inbox").fetchone()
        return int(row[0]) if row else 0

    def close(self) -> None:
        self.connection.close()


@dataclass(slots=True)
class Config:
    rate: int
    duration: float
    shards: int
    workers: int
    shard_queue_size: int
    work_queue_size: int
    hot_key_percent: float
    duplicate_percent: float
    transient_failure_percent: float
    downstream_ms: float
    max_attempts: int
    poison_key: str | None
    seed: int


class Pipeline:
    def __init__(self, config: Config, state_path: Path) -> None:
        self.config = config
        self.metrics = Metrics(shard_counts=[0] * config.shards)
        self.shard_queues = [
            asyncio.Queue[Event](maxsize=config.shard_queue_size)
            for _ in range(config.shards)
        ]
        self.work_queue: asyncio.Queue[Event] = asyncio.Queue(
            maxsize=config.work_queue_size
        )
        self.dlq: asyncio.Queue[Event] = asyncio.Queue()
        self.inbox = Inbox(state_path)
        self.stop = asyncio.Event()
        self.random = random.Random(config.seed)

    async def run(self) -> dict[str, Any]:
        tasks: list[asyncio.Task[Any]] = []
        tasks.extend(
            asyncio.create_task(self._router(index, queue), name=f"router-{index}")
            for index, queue in enumerate(self.shard_queues)
        )
        tasks.extend(
            asyncio.create_task(self._worker(index), name=f"worker-{index}")
            for index in range(self.config.workers)
        )
        producer = asyncio.create_task(self._produce(), name="producer")
        reporter = asyncio.create_task(self._report(), name="reporter")

        await producer
        await asyncio.gather(*(queue.join() for queue in self.shard_queues))
        await self.work_queue.join()
        self.stop.set()

        for task in tasks:
            task.cancel()
        reporter.cancel()
        await asyncio.gather(*tasks, reporter, return_exceptions=True)

        result = self.metrics.snapshot()
        result["inbox_rows"] = self.inbox.count()
        result["dlq_depth"] = self.dlq.qsize()
        self.inbox.close()
        return result

    async def _produce(self) -> None:
        interval = 1 / self.config.rate
        deadline = time.monotonic() + self.config.duration
        next_send = time.monotonic()
        sequence = 0
        last_event: Event | None = None

        while time.monotonic() < deadline:
            sequence += 1
            event = self._new_event(sequence)
            self.metrics.produced += 1
            await self._admit(event)
            last_event = event

            if last_event and self.random.random() < self.config.duplicate_percent:
                self.metrics.produced += 1
                await self._admit(last_event)

            next_send += interval
            sleep_for = next_send - time.monotonic()
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                await asyncio.sleep(0)

    def _new_event(self, sequence: int) -> Event:
        if self.random.random() < self.config.hot_key_percent:
            key = "tenant-hot"
        else:
            key = f"tenant-{self.random.randint(1, 10_000)}"

        if self.config.poison_key and sequence % max(self.config.rate // 2, 1) == 0:
            key = self.config.poison_key

        return Event(
            event_id=str(uuid.uuid4()),
            partition_key=key,
            event_type="TelemetryAccepted",
            produced_at=time.time(),
            payload={
                "sequence": sequence,
                "value": self.random.randint(1, 1_000_000),
            },
        )

    async def _admit(self, event: Event) -> None:
        shard = stable_shard(event.partition_key, self.config.shards)
        queue = self.shard_queues[shard]
        if queue.full():
            self.metrics.producer_backpressure += 1
        await queue.put(event)
        self.metrics.admitted += 1
        self.metrics.shard_counts[shard] += 1

    async def _router(self, shard: int, queue: asyncio.Queue[Event]) -> None:
        del shard
        while True:
            event = await queue.get()
            try:
                await self.work_queue.put(event)
                self.metrics.routed += 1
            finally:
                queue.task_done()

    async def _worker(self, worker_id: int) -> None:
        worker_random = random.Random(self.config.seed + worker_id + 1)
        while True:
            event = await self.work_queue.get()
            try:
                await self._process(event, worker_random)
            finally:
                self.work_queue.task_done()

    async def _process(self, event: Event, worker_random: random.Random) -> None:
        await asyncio.sleep(self.config.downstream_ms / 1000)

        if self.config.poison_key and event.partition_key == self.config.poison_key:
            self.metrics.permanent_failures += 1
            await self._retry_or_dlq(event, permanent=True)
            return

        if worker_random.random() < self.config.transient_failure_percent:
            self.metrics.transient_failures += 1
            await self._retry_or_dlq(event, permanent=False)
            return

        inserted = await self.inbox.apply_once(
            event,
            json.dumps(
                {"worker": worker_random.randint(1, 1_000_000)},
                sort_keys=True,
            ),
        )
        if not inserted:
            self.metrics.duplicates += 1
            return

        self.metrics.processed += 1
        self.metrics.latencies_ms.append((time.time() - event.produced_at) * 1000)

    async def _retry_or_dlq(self, event: Event, *, permanent: bool) -> None:
        next_attempt = event.attempt + 1
        if permanent or next_attempt >= self.config.max_attempts:
            await self.dlq.put(event.with_attempt(next_attempt))
            self.metrics.dlq += 1
            return

        self.metrics.retries += 1
        delay = min(0.5, 0.01 * (2**event.attempt))
        delay += self.random.uniform(0, delay)
        await asyncio.sleep(delay)
        await self.work_queue.put(event.with_attempt(next_attempt))

    async def _report(self) -> None:
        while not self.stop.is_set():
            await asyncio.sleep(1)
            snapshot = {
                "produced": self.metrics.produced,
                "processed": self.metrics.processed,
                "retries": self.metrics.retries,
                "dlq": self.metrics.dlq,
                "shard_depths": [q.qsize() for q in self.shard_queues],
                "work_depth": self.work_queue.qsize(),
            }
            print(json.dumps(snapshot, sort_keys=True), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rate", type=int, default=500, help="logical events per second")
    parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="producer duration in seconds",
    )
    parser.add_argument("--shards", type=int, default=8)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--shard-queue-size", type=int, default=500)
    parser.add_argument("--work-queue-size", type=int, default=2_000)
    parser.add_argument("--hot-key-percent", type=float, default=0.0)
    parser.add_argument("--duplicate-percent", type=float, default=0.01)
    parser.add_argument("--transient-failure-percent", type=float, default=0.01)
    parser.add_argument("--downstream-ms", type=float, default=2.0)
    parser.add_argument("--max-attempts", type=int, default=4)
    parser.add_argument("--poison-key", default=None)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("runtime/inbox.sqlite3"),
    )
    return parser.parse_args()


def validate_fraction(name: str, value: float) -> None:
    if not 0 <= value <= 1:
        raise ValueError(f"{name} must be between 0 and 1")


async def async_main() -> int:
    args = parse_args()
    if args.rate <= 0 or args.shards <= 0 or args.workers <= 0:
        raise ValueError("rate, shards, and workers must be positive")
    validate_fraction("hot-key-percent", args.hot_key_percent)
    validate_fraction("duplicate-percent", args.duplicate_percent)
    validate_fraction(
        "transient-failure-percent",
        args.transient_failure_percent,
    )
    args.state.parent.mkdir(parents=True, exist_ok=True)

    config = Config(
        rate=args.rate,
        duration=args.duration,
        shards=args.shards,
        workers=args.workers,
        shard_queue_size=args.shard_queue_size,
        work_queue_size=args.work_queue_size,
        hot_key_percent=args.hot_key_percent,
        duplicate_percent=args.duplicate_percent,
        transient_failure_percent=args.transient_failure_percent,
        downstream_ms=args.downstream_ms,
        max_attempts=args.max_attempts,
        poison_key=args.poison_key,
        seed=args.seed,
    )
    result = await Pipeline(config, args.state).run()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def main() -> int:
    try:
        return asyncio.run(async_main())
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
