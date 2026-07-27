from __future__ import annotations

import importlib.util
import sqlite3
import sys
import tempfile
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


retry = load_module(
    "retry_simulator",
    "labs/distributed-systems/01-retry-amplification/retry_simulator.py",
)
outbox = load_module(
    "outbox_lab",
    "labs/distributed-systems/02-transactional-outbox/outbox_lab.py",
)
fencing = load_module(
    "fencing_demo",
    "labs/distributed-systems/03-fencing-tokens/fencing_demo.py",
)


class RetryAmplificationTests(unittest.TestCase):
    def test_no_retry_creates_one_dependency_attempt_per_request(self) -> None:
        config = retry.Config(
            logical_requests=25,
            service_layers=3,
            retries_per_layer=2,
            dependency_failure_rate=1.0,
            mode="none",
            seed=1,
        )
        result = retry.run(config)
        self.assertEqual(result.total_dependency_attempts, 25)
        self.assertEqual(result.failed_requests, 25)

    def test_layered_retries_multiply_attempts(self) -> None:
        layered = retry.run(
            retry.Config(
                logical_requests=1,
                service_layers=2,
                retries_per_layer=2,
                dependency_failure_rate=1.0,
                mode="layered",
                seed=1,
            )
        )
        edge = retry.run(
            retry.Config(
                logical_requests=1,
                service_layers=2,
                retries_per_layer=2,
                dependency_failure_rate=1.0,
                mode="edge",
                seed=1,
            )
        )
        self.assertEqual(layered.total_dependency_attempts, 9)
        self.assertEqual(edge.total_dependency_attempts, 3)

    def test_json_shape_contains_retry_evidence(self) -> None:
        result = retry.run(
            retry.Config(
                logical_requests=10,
                service_layers=2,
                retries_per_layer=1,
                dependency_failure_rate=0.5,
                mode="edge",
                jitter=True,
                seed=3,
            )
        )
        data = result.to_dict()
        self.assertIn("total_dependency_attempts", data)
        self.assertIn("retry_wave_histogram", data)
        self.assertEqual(data["config"]["mode"], "edge")


class TransactionalOutboxTests(unittest.TestCase):
    def test_duplicate_publication_produces_one_business_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            paths = outbox.Paths(
                app_db=Path(directory) / "app.db",
                broker_db=Path(directory) / "broker.db",
            )
            outbox.initialize(paths)
            event_id = outbox.create_order(
                paths,
                order_id="order-test-1",
                customer_id="customer-test-1",
                amount_cents=12345,
            )

            crash_code = outbox.relay(
                paths,
                limit=10,
                crash_after_publish=True,
                duplicate_each=1,
            )
            self.assertEqual(crash_code, 75)

            published = outbox.relay(
                paths,
                limit=10,
                crash_after_publish=False,
                duplicate_each=1,
            )
            self.assertEqual(published, 1)

            processed, duplicates = outbox.consume(
                paths,
                consumer_name="test-consumer",
                limit=100,
            )
            self.assertEqual(processed, 1)
            self.assertEqual(duplicates, 1)

            with sqlite3.connect(paths.app_db) as app:
                inbox_count = app.execute(
                    "SELECT COUNT(*) FROM consumer_inbox WHERE event_id = ?",
                    (event_id,),
                ).fetchone()[0]
                fulfillment_count = app.execute(
                    "SELECT COUNT(*) FROM fulfillment WHERE order_id = ?",
                    ("order-test-1",),
                ).fetchone()[0]
                published_at = app.execute(
                    "SELECT published_at FROM outbox WHERE event_id = ?",
                    (event_id,),
                ).fetchone()[0]

            with sqlite3.connect(paths.broker_db) as broker:
                delivery_count = broker.execute(
                    "SELECT COUNT(*) FROM deliveries WHERE event_id = ?",
                    (event_id,),
                ).fetchone()[0]

            self.assertEqual(delivery_count, 2)
            self.assertEqual(inbox_count, 1)
            self.assertEqual(fulfillment_count, 1)
            self.assertIsNotNone(published_at)


class FencingTokenTests(unittest.TestCase):
    def test_unsafe_resource_accepts_stale_writer(self) -> None:
        events = fencing.simulate(fenced=False)
        self.assertEqual(events[-1].resource_value, "A:stale-resumed-write")
        self.assertTrue(events[-1].outcome.startswith("accepted"))

    def test_fenced_resource_rejects_stale_writer(self) -> None:
        events = fencing.simulate(fenced=True)
        self.assertEqual(events[-1].resource_value, "B:authoritative-write")
        self.assertTrue(events[-1].outcome.startswith("rejected"))


if __name__ == "__main__":
    unittest.main()
