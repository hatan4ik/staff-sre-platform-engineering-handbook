from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline import Config, Event, Inbox, Pipeline, percentile, stable_shard


class UtilityTests(unittest.TestCase):
    def test_stable_shard_is_deterministic(self) -> None:
        self.assertEqual(
            stable_shard("tenant-1", 8),
            stable_shard("tenant-1", 8),
        )
        self.assertGreaterEqual(stable_shard("tenant-1", 8), 0)
        self.assertLess(stable_shard("tenant-1", 8), 8)

    def test_percentile(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0]
        self.assertEqual(percentile(values, 0.0), 1.0)
        self.assertEqual(percentile(values, 1.0), 4.0)
        self.assertAlmostEqual(percentile(values, 0.5), 2.5)


class InboxTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_once_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inbox = Inbox(Path(directory) / "inbox.sqlite3")
            event = Event("id-1", "tenant-1", "Test", 1.0, {})
            self.assertTrue(await inbox.apply_once(event, "ok"))
            self.assertFalse(await inbox.apply_once(event, "ok"))
            self.assertEqual(inbox.count(), 1)
            inbox.close()


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_pipeline_processes_and_deduplicates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Config(
                rate=100,
                duration=0.2,
                shards=4,
                workers=4,
                shard_queue_size=50,
                work_queue_size=100,
                hot_key_percent=0.0,
                duplicate_percent=1.0,
                transient_failure_percent=0.0,
                downstream_ms=0.1,
                max_attempts=3,
                poison_key=None,
                seed=3,
            )
            result = await Pipeline(
                config,
                Path(directory) / "inbox.sqlite3",
            ).run()
            self.assertGreater(result["processed"], 0)
            self.assertGreater(result["duplicates"], 0)
            self.assertEqual(result["processed"], result["inbox_rows"])
            self.assertEqual(result["dlq"], 0)

    async def test_poison_event_reaches_dlq(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Config(
                rate=20,
                duration=0.25,
                shards=2,
                workers=2,
                shard_queue_size=50,
                work_queue_size=50,
                hot_key_percent=0.0,
                duplicate_percent=0.0,
                transient_failure_percent=0.0,
                downstream_ms=0.1,
                max_attempts=3,
                poison_key="poison",
                seed=5,
            )
            result = await Pipeline(
                config,
                Path(directory) / "inbox.sqlite3",
            ).run()
            self.assertGreaterEqual(result["dlq"], 1)
            self.assertEqual(result["dlq"], result["dlq_depth"])


if __name__ == "__main__":
    unittest.main()
