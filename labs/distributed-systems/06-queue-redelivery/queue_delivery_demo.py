from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field


@dataclass
class Message:
    message_id: str
    payload: str
    group_key: str
    sequence: int
    receive_count: int = 0
    visible_at: int = 0
    receipt_token: str | None = None


@dataclass(frozen=True)
class Delivery:
    message_id: str
    payload: str
    group_key: str
    sequence: int
    receive_count: int
    receipt_token: str
    lease_until: int


@dataclass(frozen=True)
class ProcessResult:
    message_id: str
    duplicate: bool
    side_effect_count: int
    acknowledged: bool
    crashed_before_ack: bool


@dataclass(frozen=True)
class ScenarioResult:
    name: str
    side_effect_count: int
    inbox_count: int
    remaining_messages: int
    dlq_messages: tuple[str, ...]
    events: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["dlq_messages"] = list(self.dlq_messages)
        data["events"] = list(self.events)
        return data


class Broker:
    def __init__(
        self,
        *,
        max_receive_count: int = 3,
        strict_group_ordering: bool = False,
    ) -> None:
        if max_receive_count <= 0:
            raise ValueError("max_receive_count must be positive")
        self.max_receive_count = max_receive_count
        self.strict_group_ordering = strict_group_ordering
        self.messages: list[Message] = []
        self.dlq: list[Message] = []
        self._sequence = 0
        self._receipt_sequence = 0

    def enqueue(
        self,
        message_id: str,
        payload: str,
        *,
        group_key: str = "default",
    ) -> None:
        if any(message.message_id == message_id for message in self.messages):
            raise ValueError(f"duplicate message id {message_id}")
        self._sequence += 1
        self.messages.append(
            Message(
                message_id=message_id,
                payload=payload,
                group_key=group_key,
                sequence=self._sequence,
            )
        )

    def receive(
        self,
        *,
        now: int,
        visibility_timeout: int,
    ) -> Delivery | None:
        if visibility_timeout <= 0:
            raise ValueError("visibility_timeout must be positive")

        for message in tuple(self.messages):
            if message.visible_at > now:
                continue
            if (
                self.strict_group_ordering
                and self._blocked_by_earlier_group_message(message)
            ):
                continue

            message.receive_count += 1
            if message.receive_count > self.max_receive_count:
                self.messages.remove(message)
                message.receipt_token = None
                self.dlq.append(message)
                continue

            self._receipt_sequence += 1
            token = f"receipt-{self._receipt_sequence}"
            message.receipt_token = token
            message.visible_at = now + visibility_timeout
            return Delivery(
                message_id=message.message_id,
                payload=message.payload,
                group_key=message.group_key,
                sequence=message.sequence,
                receive_count=message.receive_count,
                receipt_token=token,
                lease_until=message.visible_at,
            )
        return None

    def ack(self, receipt_token: str) -> bool:
        for message in tuple(self.messages):
            if message.receipt_token == receipt_token:
                self.messages.remove(message)
                return True
        return False

    def nack(
        self,
        receipt_token: str,
        *,
        now: int,
        retry_delay: int = 0,
    ) -> bool:
        if retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        for message in self.messages:
            if message.receipt_token == receipt_token:
                message.receipt_token = None
                message.visible_at = now + retry_delay
                return True
        return False

    def _blocked_by_earlier_group_message(self, candidate: Message) -> bool:
        return any(
            other.group_key == candidate.group_key
            and other.sequence < candidate.sequence
            for other in self.messages
        )


@dataclass
class Consumer:
    name: str
    inbox: set[str] = field(default_factory=set)
    side_effects: dict[str, int] = field(default_factory=dict)

    def process(
        self,
        broker: Broker,
        delivery: Delivery,
        *,
        idempotent: bool,
        crash_before_ack: bool,
    ) -> ProcessResult:
        duplicate = delivery.message_id in self.inbox

        if idempotent:
            if not duplicate:
                self.inbox.add(delivery.message_id)
                self.side_effects[delivery.message_id] = (
                    self.side_effects.get(delivery.message_id, 0) + 1
                )
        else:
            self.side_effects[delivery.message_id] = (
                self.side_effects.get(delivery.message_id, 0) + 1
            )

        acknowledged = False
        if not crash_before_ack:
            acknowledged = broker.ack(delivery.receipt_token)

        return ProcessResult(
            message_id=delivery.message_id,
            duplicate=duplicate,
            side_effect_count=self.side_effects.get(delivery.message_id, 0),
            acknowledged=acknowledged,
            crashed_before_ack=crash_before_ack,
        )


def duplicate_delivery_scenario(*, idempotent: bool) -> ScenarioResult:
    broker = Broker(max_receive_count=5)
    broker.enqueue("order-1", "reserve inventory")
    consumer = Consumer("inventory")
    events: list[str] = []

    first = broker.receive(now=0, visibility_timeout=5)
    assert first is not None
    first_result = consumer.process(
        broker,
        first,
        idempotent=idempotent,
        crash_before_ack=True,
    )
    events.append(
        f"first attempt applied={first_result.side_effect_count} "
        "crash_before_ack=true"
    )

    second = broker.receive(now=6, visibility_timeout=5)
    assert second is not None
    second_result = consumer.process(
        broker,
        second,
        idempotent=idempotent,
        crash_before_ack=False,
    )
    events.append(
        f"redelivery duplicate={second_result.duplicate} "
        f"side_effect_count={second_result.side_effect_count} "
        f"acknowledged={second_result.acknowledged}"
    )

    return ScenarioResult(
        name=(
            "idempotent-redelivery"
            if idempotent
            else "unsafe-redelivery"
        ),
        side_effect_count=consumer.side_effects.get("order-1", 0),
        inbox_count=len(consumer.inbox),
        remaining_messages=len(broker.messages),
        dlq_messages=tuple(message.message_id for message in broker.dlq),
        events=tuple(events),
    )


def poison_message_scenario() -> ScenarioResult:
    broker = Broker(max_receive_count=3)
    broker.enqueue("poison-1", "invalid schema")
    events: list[str] = []

    for now in (0, 6, 12, 18):
        delivery = broker.receive(now=now, visibility_timeout=5)
        if delivery is None:
            events.append(
                f"time={now}: no delivery; "
                f"dlq={[message.message_id for message in broker.dlq]}"
            )
            continue
        events.append(
            f"time={now}: receive_count={delivery.receive_count}; "
            "processing failed"
        )

    return ScenarioResult(
        name="poison-message",
        side_effect_count=0,
        inbox_count=0,
        remaining_messages=len(broker.messages),
        dlq_messages=tuple(message.message_id for message in broker.dlq),
        events=tuple(events),
    )


def visibility_timeout_scenario() -> ScenarioResult:
    broker = Broker(max_receive_count=5)
    broker.enqueue("report-1", "render expensive report")
    consumer = Consumer("report-worker")
    events: list[str] = []

    worker_a = broker.receive(now=0, visibility_timeout=5)
    assert worker_a is not None
    events.append(
        f"worker-a received token={worker_a.receipt_token} "
        f"lease_until={worker_a.lease_until}"
    )

    worker_b = broker.receive(now=6, visibility_timeout=5)
    assert worker_b is not None
    events.append(
        f"worker-b received token={worker_b.receipt_token} "
        f"lease_until={worker_b.lease_until}"
    )

    result_a = consumer.process(
        broker,
        worker_a,
        idempotent=False,
        crash_before_ack=False,
    )
    events.append(
        f"worker-a completed late; old receipt "
        f"acknowledged={result_a.acknowledged}"
    )

    result_b = consumer.process(
        broker,
        worker_b,
        idempotent=False,
        crash_before_ack=False,
    )
    events.append(
        f"worker-b completed; current receipt "
        f"acknowledged={result_b.acknowledged}"
    )

    return ScenarioResult(
        name="visibility-timeout-too-short",
        side_effect_count=consumer.side_effects.get("report-1", 0),
        inbox_count=len(consumer.inbox),
        remaining_messages=len(broker.messages),
        dlq_messages=tuple(message.message_id for message in broker.dlq),
        events=tuple(events),
    )


def ordered_group_scenario() -> dict[str, object]:
    broker = Broker(
        max_receive_count=3,
        strict_group_ordering=True,
    )
    broker.enqueue(
        "account-1-event-1",
        "debit",
        group_key="account-1",
    )
    broker.enqueue(
        "account-1-event-2",
        "credit",
        group_key="account-1",
    )
    broker.enqueue(
        "account-2-event-1",
        "debit",
        group_key="account-2",
    )

    first = broker.receive(now=0, visibility_timeout=10)
    second = broker.receive(now=0, visibility_timeout=10)
    assert first is not None
    assert second is not None

    return {
        "first": asdict(first),
        "second": asdict(second),
        "blocked_message": "account-1-event-2",
        "explanation": (
            "the second account-1 message remains blocked behind the "
            "unacknowledged first message, while another group can progress"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate queue redelivery, idempotency, visibility, and DLQs."
        )
    )
    parser.add_argument(
        "scenario",
        choices=(
            "unsafe",
            "idempotent",
            "poison",
            "visibility",
            "ordering",
            "all",
        ),
    )
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    payload: object
    if args.scenario == "unsafe":
        payload = duplicate_delivery_scenario(idempotent=False).to_dict()
    elif args.scenario == "idempotent":
        payload = duplicate_delivery_scenario(idempotent=True).to_dict()
    elif args.scenario == "poison":
        payload = poison_message_scenario().to_dict()
    elif args.scenario == "visibility":
        payload = visibility_timeout_scenario().to_dict()
    elif args.scenario == "ordering":
        payload = ordered_group_scenario()
    else:
        payload = {
            "unsafe": duplicate_delivery_scenario(
                idempotent=False
            ).to_dict(),
            "idempotent": duplicate_delivery_scenario(
                idempotent=True
            ).to_dict(),
            "poison": poison_message_scenario().to_dict(),
            "visibility": visibility_timeout_scenario().to_dict(),
            "ordering": ordered_group_scenario(),
        }

    print(json.dumps(payload, indent=2, sort_keys=args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
