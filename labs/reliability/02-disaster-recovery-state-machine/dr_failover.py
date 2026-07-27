from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from enum import Enum


class DRError(ValueError):
    """Raised when a disaster-recovery state or policy is invalid."""


class DRState(str, Enum):
    NORMAL = "normal"
    ASSESS = "assess"
    FROZEN = "frozen"
    ELIGIBILITY_CHECK = "eligibility-check"
    FENCING = "fencing"
    PROMOTING = "promoting"
    CANARY = "canary"
    EXPANDING = "expanding"
    RECOVERED_SECONDARY = "recovered-secondary"
    HOLD_READ_ONLY = "hold-read-only"
    FAILBACK_PREP = "failback-prep"
    FAILBACK_CANARY = "failback-canary"
    NORMAL_RESTORED = "normal-restored"


@dataclass(frozen=True)
class Region:
    name: str
    application_healthy: bool
    capacity_percent_of_peak: float
    dependencies_healthy: bool
    identity_healthy: bool
    observability_healthy: bool
    replication_lag_seconds: float
    schema_compatible: bool
    writer_epoch: int
    accepting_writes: bool
    business_synthetic_healthy: bool


@dataclass(frozen=True)
class DRPolicy:
    required_capacity_percent_of_peak: float = 100.0
    maximum_replication_lag_seconds: float = 30.0
    require_observability: bool = True
    require_business_synthetic: bool = True
    initial_canary_percent: float = 1.0
    maximum_traffic_step_percent: float = 25.0


@dataclass(frozen=True)
class DRContext:
    state: DRState
    primary: Region
    secondary: Region
    old_writer_fenced: bool = False
    traffic_percent_secondary: float = 0.0
    fast_burn: bool = False
    data_inconsistency_detected: bool = False
    global_change_freeze: bool = False
    incident_commander_assigned: bool = False
    failback_replication_healthy: bool = False
    original_region_rebuilt: bool = False


@dataclass(frozen=True)
class TransitionResult:
    previous_state: DRState
    next_state: DRState
    action: str
    reason: str
    context: DRContext


def _validate_region(region: Region) -> None:
    if not region.name:
        raise DRError("region name is required")
    if region.capacity_percent_of_peak < 0:
        raise DRError("capacity percent cannot be negative")
    if region.replication_lag_seconds < 0:
        raise DRError("replication lag cannot be negative")
    if region.writer_epoch < 0:
        raise DRError("writer epoch cannot be negative")


def _validate_policy(policy: DRPolicy) -> None:
    if policy.required_capacity_percent_of_peak <= 0:
        raise DRError("required capacity must be positive")
    if policy.maximum_replication_lag_seconds < 0:
        raise DRError("maximum replication lag cannot be negative")
    if not 0 < policy.initial_canary_percent <= 100:
        raise DRError("initial canary percent must be in (0, 100]")
    if not 0 < policy.maximum_traffic_step_percent <= 100:
        raise DRError("maximum traffic step percent must be in (0, 100]")


def destination_eligibility(region: Region, policy: DRPolicy) -> tuple[bool, list[str]]:
    _validate_region(region)
    _validate_policy(policy)

    failures: list[str] = []
    if not region.application_healthy:
        failures.append("application-unhealthy")
    if region.capacity_percent_of_peak < policy.required_capacity_percent_of_peak:
        failures.append("insufficient-capacity")
    if not region.dependencies_healthy:
        failures.append("dependency-unhealthy")
    if not region.identity_healthy:
        failures.append("identity-unhealthy")
    if policy.require_observability and not region.observability_healthy:
        failures.append("observability-unhealthy")
    if region.replication_lag_seconds > policy.maximum_replication_lag_seconds:
        failures.append("replication-lag-exceeds-rpo")
    if not region.schema_compatible:
        failures.append("schema-incompatible")
    if policy.require_business_synthetic and not region.business_synthetic_healthy:
        failures.append("business-synthetic-failed")

    return not failures, failures


def write_allowed(region: Region, token_epoch: int) -> bool:
    """Model resource-enforced stale-writer rejection."""
    _validate_region(region)
    if token_epoch < 0:
        raise DRError("token epoch cannot be negative")
    return region.accepting_writes and token_epoch == region.writer_epoch


def reconcile_once(context: DRContext, policy: DRPolicy) -> TransitionResult:
    """Apply one idempotent DR state-machine transition."""
    _validate_region(context.primary)
    _validate_region(context.secondary)
    _validate_policy(policy)

    previous = context.state

    if context.data_inconsistency_detected:
        next_context = replace(context, state=DRState.HOLD_READ_ONLY)
        return TransitionResult(
            previous,
            DRState.HOLD_READ_ONLY,
            "hold-read-only",
            "data inconsistency requires human reconciliation",
            next_context,
        )

    if context.fast_burn and context.state in {
        DRState.CANARY,
        DRState.EXPANDING,
        DRState.FAILBACK_CANARY,
    }:
        next_context = replace(context, state=DRState.HOLD_READ_ONLY)
        return TransitionResult(
            previous,
            DRState.HOLD_READ_ONLY,
            "abort-traffic-shift",
            "fast SLO burn detected during transition",
            next_context,
        )

    if context.state == DRState.NORMAL:
        if context.primary.application_healthy:
            return TransitionResult(
                previous,
                DRState.NORMAL,
                "observe",
                "primary remains healthy",
                context,
            )
        next_context = replace(context, state=DRState.ASSESS)
        return TransitionResult(
            previous,
            DRState.ASSESS,
            "declare-assessment",
            "primary application is unhealthy",
            next_context,
        )

    if context.state == DRState.ASSESS:
        if not context.incident_commander_assigned:
            return TransitionResult(
                previous,
                DRState.ASSESS,
                "hold",
                "incident commander is not assigned",
                context,
            )
        next_context = replace(
            context,
            state=DRState.FROZEN,
            global_change_freeze=True,
        )
        return TransitionResult(
            previous,
            DRState.FROZEN,
            "freeze-changes",
            "incident command established",
            next_context,
        )

    if context.state == DRState.FROZEN:
        next_context = replace(context, state=DRState.ELIGIBILITY_CHECK)
        return TransitionResult(
            previous,
            DRState.ELIGIBILITY_CHECK,
            "check-destination",
            "change freeze active",
            next_context,
        )

    if context.state == DRState.ELIGIBILITY_CHECK:
        eligible, failures = destination_eligibility(context.secondary, policy)
        if not eligible:
            next_context = replace(context, state=DRState.HOLD_READ_ONLY)
            return TransitionResult(
                previous,
                DRState.HOLD_READ_ONLY,
                "hold-read-only",
                "destination ineligible: " + ", ".join(failures),
                next_context,
            )
        next_context = replace(context, state=DRState.FENCING)
        return TransitionResult(
            previous,
            DRState.FENCING,
            "fence-old-writer",
            "destination is eligible",
            next_context,
        )

    if context.state == DRState.FENCING:
        if not context.old_writer_fenced:
            return TransitionResult(
                previous,
                DRState.FENCING,
                "hold",
                "old writer fencing is not proven",
                context,
            )
        next_context = replace(context, state=DRState.PROMOTING)
        return TransitionResult(
            previous,
            DRState.PROMOTING,
            "promote-secondary-writer",
            "old writer fenced",
            next_context,
        )

    if context.state == DRState.PROMOTING:
        promoted_epoch = max(context.primary.writer_epoch, context.secondary.writer_epoch) + 1
        primary = replace(context.primary, accepting_writes=False)
        secondary = replace(
            context.secondary,
            accepting_writes=True,
            writer_epoch=promoted_epoch,
        )
        next_context = replace(
            context,
            primary=primary,
            secondary=secondary,
            state=DRState.CANARY,
            traffic_percent_secondary=policy.initial_canary_percent,
        )
        return TransitionResult(
            previous,
            DRState.CANARY,
            "start-canary",
            f"secondary promoted with writer epoch {promoted_epoch}",
            next_context,
        )

    if context.state == DRState.CANARY:
        eligible, failures = destination_eligibility(context.secondary, policy)
        if not eligible:
            next_context = replace(context, state=DRState.HOLD_READ_ONLY)
            return TransitionResult(
                previous,
                DRState.HOLD_READ_ONLY,
                "abort-canary",
                "destination lost eligibility: " + ", ".join(failures),
                next_context,
            )
        next_percent = min(
            100.0,
            context.traffic_percent_secondary
            + policy.maximum_traffic_step_percent,
        )
        next_state = (
            DRState.RECOVERED_SECONDARY
            if next_percent >= 100.0
            else DRState.EXPANDING
        )
        next_context = replace(
            context,
            state=next_state,
            traffic_percent_secondary=next_percent,
        )
        return TransitionResult(
            previous,
            next_state,
            "expand-traffic",
            "canary guardrails healthy",
            next_context,
        )

    if context.state == DRState.EXPANDING:
        eligible, failures = destination_eligibility(context.secondary, policy)
        if not eligible:
            next_context = replace(context, state=DRState.HOLD_READ_ONLY)
            return TransitionResult(
                previous,
                DRState.HOLD_READ_ONLY,
                "hold-read-only",
                "destination lost eligibility: " + ", ".join(failures),
                next_context,
            )
        next_percent = min(
            100.0,
            context.traffic_percent_secondary
            + policy.maximum_traffic_step_percent,
        )
        next_state = (
            DRState.RECOVERED_SECONDARY
            if next_percent >= 100.0
            else DRState.EXPANDING
        )
        next_context = replace(
            context,
            state=next_state,
            traffic_percent_secondary=next_percent,
        )
        return TransitionResult(
            previous,
            next_state,
            "expand-traffic",
            "regional SLI and data guardrails healthy",
            next_context,
        )

    if context.state == DRState.RECOVERED_SECONDARY:
        if context.original_region_rebuilt and context.failback_replication_healthy:
            next_context = replace(context, state=DRState.FAILBACK_PREP)
            return TransitionResult(
                previous,
                DRState.FAILBACK_PREP,
                "prepare-failback",
                "original region rebuilt and resynchronized",
                next_context,
            )
        return TransitionResult(
            previous,
            DRState.RECOVERED_SECONDARY,
            "operate-and-reprotect",
            "secondary remains authoritative",
            context,
        )

    if context.state == DRState.FAILBACK_PREP:
        eligible, failures = destination_eligibility(context.primary, policy)
        if not eligible or not context.failback_replication_healthy:
            return TransitionResult(
                previous,
                DRState.FAILBACK_PREP,
                "hold",
                "original region not failback eligible: " + ", ".join(failures),
                context,
            )
        new_epoch = max(context.primary.writer_epoch, context.secondary.writer_epoch) + 1
        primary = replace(
            context.primary,
            accepting_writes=True,
            writer_epoch=new_epoch,
        )
        secondary = replace(context.secondary, accepting_writes=False)
        next_context = replace(
            context,
            primary=primary,
            secondary=secondary,
            state=DRState.FAILBACK_CANARY,
            traffic_percent_secondary=max(
                0.0,
                100.0 - policy.initial_canary_percent,
            ),
        )
        return TransitionResult(
            previous,
            DRState.FAILBACK_CANARY,
            "start-failback-canary",
            f"original region promoted with writer epoch {new_epoch}",
            next_context,
        )

    if context.state == DRState.FAILBACK_CANARY:
        next_secondary_percent = max(
            0.0,
            context.traffic_percent_secondary
            - policy.maximum_traffic_step_percent,
        )
        next_state = (
            DRState.NORMAL_RESTORED
            if next_secondary_percent <= 0.0
            else DRState.FAILBACK_CANARY
        )
        next_context = replace(
            context,
            state=next_state,
            traffic_percent_secondary=next_secondary_percent,
        )
        return TransitionResult(
            previous,
            next_state,
            "expand-failback",
            "failback guardrails healthy",
            next_context,
        )

    if context.state in {DRState.NORMAL_RESTORED, DRState.HOLD_READ_ONLY}:
        return TransitionResult(
            previous,
            context.state,
            "hold",
            "state requires explicit operator decision or remains stable",
            context,
        )

    raise DRError(f"unhandled DR state: {context.state}")


def run_until_stable(
    context: DRContext,
    policy: DRPolicy,
    *,
    maximum_steps: int = 50,
) -> list[TransitionResult]:
    if maximum_steps <= 0:
        raise DRError("maximum_steps must be positive")

    history: list[TransitionResult] = []
    current = context
    for _ in range(maximum_steps):
        result = reconcile_once(current, policy)
        history.append(result)
        if result.context == current:
            break
        current = result.context
    else:
        raise DRError("state machine did not stabilize within maximum_steps")
    return history


def healthy_region(
    name: str,
    *,
    writer_epoch: int,
    accepting_writes: bool,
) -> Region:
    return Region(
        name=name,
        application_healthy=True,
        capacity_percent_of_peak=120.0,
        dependencies_healthy=True,
        identity_healthy=True,
        observability_healthy=True,
        replication_lag_seconds=5.0,
        schema_compatible=True,
        writer_epoch=writer_epoch,
        accepting_writes=accepting_writes,
        business_synthetic_healthy=True,
    )


def run_demo() -> int:
    policy = DRPolicy(
        required_capacity_percent_of_peak=100.0,
        maximum_replication_lag_seconds=30.0,
        initial_canary_percent=5.0,
        maximum_traffic_step_percent=25.0,
    )

    primary = replace(
        healthy_region("region-a", writer_epoch=41, accepting_writes=True),
        application_healthy=False,
        business_synthetic_healthy=False,
    )
    secondary = healthy_region("region-b", writer_epoch=41, accepting_writes=False)

    safe_context = DRContext(
        state=DRState.NORMAL,
        primary=primary,
        secondary=secondary,
        old_writer_fenced=True,
        incident_commander_assigned=True,
    )

    unsafe_lag_context = replace(
        safe_context,
        secondary=replace(secondary, replication_lag_seconds=120.0),
    )

    unfenced_context = replace(safe_context, old_writer_fenced=False)

    safe_history = run_until_stable(safe_context, policy)
    lag_history = run_until_stable(unsafe_lag_context, policy)
    unfenced_history = run_until_stable(unfenced_context, policy)

    safe_final = safe_history[-1].context
    stale_token_allowed = write_allowed(safe_final.secondary, 41)
    current_token_allowed = write_allowed(
        safe_final.secondary,
        safe_final.secondary.writer_epoch,
    )

    output = {
        "safe_failover": [
            {
                "previous_state": item.previous_state,
                "next_state": item.next_state,
                "action": item.action,
                "reason": item.reason,
                "traffic_percent_secondary": item.context.traffic_percent_secondary,
            }
            for item in safe_history
        ],
        "unsafe_replication_lag": [asdict(item) for item in lag_history],
        "unfenced_old_writer": [asdict(item) for item in unfenced_history],
        "writer_token_validation": {
            "stale_epoch_41_allowed": stale_token_allowed,
            "current_epoch_allowed": current_token_allowed,
            "current_epoch": safe_final.secondary.writer_epoch,
        },
    }
    print(json.dumps(output, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safe disaster-recovery failover state-machine simulator"
    )
    parser.add_argument("--demo", action="store_true", help="run built-in scenarios")
    args = parser.parse_args()
    if args.demo:
        return run_demo()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
