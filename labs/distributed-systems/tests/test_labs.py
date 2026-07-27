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
cache_race = load_module(
    "cache_race_demo",
    "labs/distributed-systems/04-cache-races/cache_race_demo.py",
)
shard_rebalance = load_module(
    "shard_rebalance_demo",
    "labs/distributed-systems/05-shard-rebalancing/shard_rebalance_demo.py",
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


class CacheRaceTests(unittest.TestCase):
    def test_delete_only_invalidation_allows_stale_resurrection(self) -> None:
        events = cache_race.stale_fill_race(safe=False)
        final_cache = events[-1].cache
        self.assertEqual(final_cache.value, "profile-v1")
        self.assertEqual(final_cache.value_version, 1)
        self.assertTrue(events[-1].outcome.startswith("accepted"))

    def test_version_fence_rejects_stale_fill(self) -> None:
        events = cache_race.stale_fill_race(safe=True)
        final_cache = events[-1].cache
        self.assertIsNone(final_cache.value)
        self.assertEqual(final_cache.version_fence, 2)
        self.assertTrue(events[-1].outcome.startswith("rejected"))

    def test_single_flight_collapses_origin_load(self) -> None:
        unsafe = cache_race.stampede(1000, single_flight=False)
        safe = cache_race.stampede(1000, single_flight=True)
        self.assertEqual(unsafe.origin_loads, 1000)
        self.assertEqual(safe.origin_loads, 1)
        self.assertEqual(safe.cache_hits_after_fill, 999)


class ShardRebalancingTests(unittest.TestCase):
    def test_hash_partition_is_stable(self) -> None:
        first = shard_rebalance.hash_partition("tenant-a:object-1", 64)
        second = shard_rebalance.hash_partition("tenant-a:object-1", 64)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, 64)

    def test_range_partition_uses_sorted_boundaries(self) -> None:
        bounds = (100, 1_000, 10_000)
        self.assertEqual(shard_rebalance.range_partition(5, bounds), 0)
        self.assertEqual(shard_rebalance.range_partition(500, bounds), 1)
        self.assertEqual(shard_rebalance.range_partition(5_000, bounds), 2)
        self.assertEqual(shard_rebalance.range_partition(50_000, bounds), 3)

    def test_unsafe_move_loses_catch_up_and_accepts_stale_router(self) -> None:
        result = shard_rebalance.simulate_rebalance(safe=False)
        self.assertTrue(result.stale_write_accepted)
        self.assertEqual(result.authoritative_value, "value-v1")
        self.assertEqual(result.source_value, "value-v3-from-stale-router")
        self.assertEqual(result.target_value, "value-v1")
        self.assertEqual(result.migration_phase, "cutover")

    def test_safe_move_replays_delta_and_rejects_stale_router(self) -> None:
        result = shard_rebalance.simulate_rebalance(safe=True)
        self.assertFalse(result.stale_write_accepted)
        self.assertEqual(result.authoritative_value, "value-v2")
        self.assertIsNone(result.source_value)
        self.assertEqual(result.target_value, "value-v2")
        self.assertEqual(result.new_epoch, result.old_epoch + 1)
        self.assertEqual(result.migration_phase, "cleanup")

    def test_hot_key_and_dominant_tenant_are_detected(self) -> None:
        report = shard_rebalance.sample_distribution()
        distribution = report["distribution"]
        self.assertIn(5, distribution["hot_shards"])
        self.assertIn("tenant-hot", report["dominant_tenants"])

    def test_safe_cutover_requires_catch_up(self) -> None:
        cluster = shard_rebalance.Cluster(("a", "b"), virtual_shards=4)
        shard = 2
        cluster.set_owner(shard, "a", epoch=3)
        migration = cluster.begin_migration(shard, "b")
        cluster.copy_snapshot(migration)
        with self.assertRaises(ValueError):
            cluster.cutover(migration, require_catch_up=True)


if __name__ == "__main__":
    unittest.main()
