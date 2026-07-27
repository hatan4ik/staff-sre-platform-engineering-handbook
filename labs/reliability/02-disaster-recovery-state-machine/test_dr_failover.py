from __future__ import annotations

import pathlib
import sys
import unittest
from dataclasses import replace

LAB_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR))

from dr_failover import (  # noqa: E402
    DRContext,
    DRError,
    DRPolicy,
    DRState,
    Region,
    destination_eligibility,
    healthy_region,
    reconcile_once,
    run_until_stable,
    write_allowed,
)


class DisasterRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = DRPolicy(
            required_capacity_percent_of_peak=100.0,
            maximum_replication_lag_seconds=30.0,
            initial_canary_percent=5.0,
            maximum_traffic_step_percent=25.0,
        )
        self.primary = replace(
            healthy_region("region-a", writer_epoch=41, accepting_writes=True),
            application_healthy=False,
            business_synthetic_healthy=False,
        )
        self.secondary = healthy_region(
            "region-b",
            writer_epoch=41,
            accepting_writes=False,
        )

    def context(self, **overrides: object) -> DRContext:
        values: dict[str, object] = {
            "state": DRState.NORMAL,
            "primary": self.primary,
            "secondary": self.secondary,
            "old_writer_fenced": True,
            "traffic_percent_secondary": 0.0,
            "fast_burn": False,
            "data_inconsistency_detected": False,
            "global_change_freeze": False,
            "incident_commander_assigned": True,
            "failback_replication_healthy": False,
            "original_region_rebuilt": False,
        }
        values.update(overrides)
        return DRContext(**values)  # type: ignore[arg-type]

    def test_destination_eligibility(self) -> None:
        eligible, failures = destination_eligibility(self.secondary, self.policy)
        self.assertTrue(eligible)
        self.assertEqual(failures, [])

    def test_replication_lag_blocks_destination(self) -> None:
        lagging = replace(self.secondary, replication_lag_seconds=120.0)
        eligible, failures = destination_eligibility(lagging, self.policy)
        self.assertFalse(eligible)
        self.assertIn("replication-lag-exceeds-rpo", failures)

    def test_missing_observability_blocks_destination(self) -> None:
        blind = replace(self.secondary, observability_healthy=False)
        eligible, failures = destination_eligibility(blind, self.policy)
        self.assertFalse(eligible)
        self.assertIn("observability-unhealthy", failures)

    def test_safe_failover_reaches_recovered_secondary(self) -> None:
        history = run_until_stable(self.context(), self.policy)
        final = history[-1].context
        self.assertEqual(final.state, DRState.RECOVERED_SECONDARY)
        self.assertEqual(final.traffic_percent_secondary, 100.0)
        self.assertFalse(final.primary.accepting_writes)
        self.assertTrue(final.secondary.accepting_writes)
        self.assertEqual(final.secondary.writer_epoch, 42)

    def test_old_writer_fencing_is_required(self) -> None:
        history = run_until_stable(
            self.context(old_writer_fenced=False),
            self.policy,
        )
        final_transition = history[-1]
        self.assertEqual(final_transition.context.state, DRState.FENCING)
        self.assertEqual(final_transition.action, "hold")
        self.assertIn("fencing is not proven", final_transition.reason)

    def test_ineligible_destination_holds_read_only(self) -> None:
        lagging = replace(self.secondary, replication_lag_seconds=120.0)
        history = run_until_stable(
            self.context(secondary=lagging),
            self.policy,
        )
        self.assertEqual(history[-1].context.state, DRState.HOLD_READ_ONLY)

    def test_fast_burn_aborts_canary(self) -> None:
        context = self.context(
            state=DRState.CANARY,
            primary=replace(self.primary, accepting_writes=False),
            secondary=replace(
                self.secondary,
                accepting_writes=True,
                writer_epoch=42,
            ),
            traffic_percent_secondary=5.0,
            fast_burn=True,
        )
        result = reconcile_once(context, self.policy)
        self.assertEqual(result.next_state, DRState.HOLD_READ_ONLY)
        self.assertEqual(result.action, "abort-traffic-shift")

    def test_data_inconsistency_overrides_other_actions(self) -> None:
        result = reconcile_once(
            self.context(data_inconsistency_detected=True),
            self.policy,
        )
        self.assertEqual(result.next_state, DRState.HOLD_READ_ONLY)
        self.assertIn("data inconsistency", result.reason)

    def test_stale_writer_token_is_rejected_after_promotion(self) -> None:
        history = run_until_stable(self.context(), self.policy)
        final = history[-1].context
        self.assertFalse(write_allowed(final.secondary, 41))
        self.assertTrue(
            write_allowed(final.secondary, final.secondary.writer_epoch)
        )
        self.assertFalse(write_allowed(final.primary, 41))

    def test_no_incident_commander_holds_assessment(self) -> None:
        context = self.context(
            state=DRState.ASSESS,
            incident_commander_assigned=False,
        )
        result = reconcile_once(context, self.policy)
        self.assertEqual(result.next_state, DRState.ASSESS)
        self.assertEqual(result.action, "hold")

    def test_failback_requires_rebuild_and_replication(self) -> None:
        recovered = self.context(
            state=DRState.RECOVERED_SECONDARY,
            primary=replace(self.primary, accepting_writes=False),
            secondary=replace(
                self.secondary,
                accepting_writes=True,
                writer_epoch=42,
            ),
            traffic_percent_secondary=100.0,
        )
        result = reconcile_once(recovered, self.policy)
        self.assertEqual(result.next_state, DRState.RECOVERED_SECONDARY)

    def test_failback_can_restore_original_region(self) -> None:
        recovered = self.context(
            state=DRState.RECOVERED_SECONDARY,
            primary=healthy_region(
                "region-a",
                writer_epoch=41,
                accepting_writes=False,
            ),
            secondary=healthy_region(
                "region-b",
                writer_epoch=42,
                accepting_writes=True,
            ),
            traffic_percent_secondary=100.0,
            original_region_rebuilt=True,
            failback_replication_healthy=True,
        )
        history = run_until_stable(recovered, self.policy)
        final = history[-1].context
        self.assertEqual(final.state, DRState.NORMAL_RESTORED)
        self.assertEqual(final.traffic_percent_secondary, 0.0)
        self.assertTrue(final.primary.accepting_writes)
        self.assertFalse(final.secondary.accepting_writes)
        self.assertEqual(final.primary.writer_epoch, 43)

    def test_invalid_region_is_rejected(self) -> None:
        invalid = Region(
            name="",
            application_healthy=True,
            capacity_percent_of_peak=100.0,
            dependencies_healthy=True,
            identity_healthy=True,
            observability_healthy=True,
            replication_lag_seconds=0.0,
            schema_compatible=True,
            writer_epoch=1,
            accepting_writes=False,
            business_synthetic_healthy=True,
        )
        with self.assertRaisesRegex(DRError, "region name is required"):
            destination_eligibility(invalid, self.policy)


if __name__ == "__main__":
    unittest.main()
