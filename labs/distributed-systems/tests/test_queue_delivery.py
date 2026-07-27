from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[3]


def load_module(name: str, relative_path: str) -> ModuleType:
    path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


queue_delivery = load_module(
    "queue_delivery_demo",
    "labs/distributed-systems/06-queue-redelivery/queue_delivery_demo.py",
)


class QueueDeliveryTests(unittest.TestCase):
    def test_unsafe_redelivery_duplicates_business_effect(self) -> None:
        result = queue_delivery.duplicate_delivery_scenario(idempotent=False)
        self.assertEqual(result.side_effect_count, 2)
        self.assertEqual(result.inbox_count, 0)
        self.assertEqual(result.remaining_messages, 0)

    def test_idempotent_inbox_collapses_duplicate_delivery(self) -> None:
        result = queue_delivery.duplicate_delivery_scenario(idempotent=True)
        self.assertEqual(result.side_effect_count, 1)
        self.assertEqual(result.inbox_count, 1)
        self.assertEqual(result.remaining_messages, 0)

    def test_poison_message_moves_to_dlq_after_receive_budget(self) -> None:
        result = queue_delivery.poison_message_scenario()
        self.assertEqual(result.dlq_messages, ("poison-1",))
        self.assertEqual(result.remaining_messages, 0)

    def test_short_visibility_timeout_allows_concurrent_duplicate(self) -> None:
        result = queue_delivery.visibility_timeout_scenario()
        self.assertEqual(result.side_effect_count, 2)
        self.assertEqual(result.remaining_messages, 0)
        self.assertTrue(
            any("old receipt acknowledged=False" in event for event in result.events)
        )

    def test_ordered_group_blocks_later_message_but_not_other_group(self) -> None:
        result = queue_delivery.ordered_group_scenario()
        self.assertEqual(result["first"]["message_id"], "account-1-event-1")
        self.assertEqual(result["second"]["message_id"], "account-2-event-1")
        self.assertEqual(result["blocked_message"], "account-1-event-2")

    def test_nack_delay_controls_redelivery_time(self) -> None:
        broker = queue_delivery.Broker(max_receive_count=3)
        broker.enqueue("message-1", "payload")
        delivery = broker.receive(now=0, visibility_timeout=30)
        self.assertIsNotNone(delivery)
        assert delivery is not None
        self.assertTrue(
            broker.nack(delivery.receipt_token, now=2, retry_delay=10)
        )
        self.assertIsNone(broker.receive(now=11, visibility_timeout=5))
        self.assertIsNotNone(broker.receive(now=12, visibility_timeout=5))


if __name__ == "__main__":
    unittest.main()
