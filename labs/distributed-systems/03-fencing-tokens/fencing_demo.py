#!/usr/bin/env python3
"""Demonstrate why leases need resource-enforced fencing tokens.

A former owner may pause long enough for its lease to expire, then resume and
continue writing. A coordinator cannot recall credentials already handed out.
The protected resource must reject operations carrying an older token.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Lease:
    owner: str
    token: int
    issued_at: float
    expires_at: float


@dataclass
class Event:
    time: float
    actor: str
    action: str
    token: int | None
    outcome: str
    resource_value: str | None


class LeaseCoordinator:
    def __init__(self, lease_duration: float) -> None:
        if lease_duration <= 0:
            raise ValueError("lease_duration must be greater than zero")
        self.lease_duration = lease_duration
        self._next_token = 1
        self._active: Lease | None = None

    def acquire(self, owner: str, now: float) -> Lease:
        if self._active is not None and now < self._active.expires_at:
            raise RuntimeError(
                f"lease is still held by {self._active.owner} "
                f"until t={self._active.expires_at}"
            )

        lease = Lease(
            owner=owner,
            token=self._next_token,
            issued_at=now,
            expires_at=now + self.lease_duration,
        )
        self._next_token += 1
        self._active = lease
        return lease


class UnsafeResource:
    """Accepts writes from any client that once received a lease."""

    def __init__(self) -> None:
        self.value: str | None = None

    def write(self, value: str, token: int) -> tuple[bool, str]:
        self.value = value
        return True, f"accepted token {token} without checking freshness"


class FencedResource:
    """Rejects tokens lower than the highest token already observed."""

    def __init__(self) -> None:
        self.value: str | None = None
        self.highest_token = 0

    def write(self, value: str, token: int) -> tuple[bool, str]:
        if token < self.highest_token:
            return (
                False,
                f"rejected stale token {token}; highest accepted token is "
                f"{self.highest_token}",
            )

        self.highest_token = token
        self.value = value
        return True, f"accepted token {token}"


def simulate(fenced: bool, lease_duration: float = 5.0) -> list[Event]:
    coordinator = LeaseCoordinator(lease_duration=lease_duration)
    resource = FencedResource() if fenced else UnsafeResource()
    events: list[Event] = []

    # t=0: worker A becomes owner.
    lease_a = coordinator.acquire("worker-A", now=0.0)
    events.append(
        Event(
            time=0.0,
            actor="worker-A",
            action="acquire lease",
            token=lease_a.token,
            outcome=f"lease valid until t={lease_a.expires_at}",
            resource_value=resource.value,
        )
    )

    accepted, reason = resource.write("A:initial-write", lease_a.token)
    events.append(
        Event(
            time=1.0,
            actor="worker-A",
            action="write A:initial-write",
            token=lease_a.token,
            outcome=("accepted: " if accepted else "rejected: ") + reason,
            resource_value=resource.value,
        )
    )

    # A pauses. The coordinator cannot distinguish a long pause from failure.
    events.append(
        Event(
            time=2.0,
            actor="worker-A",
            action="process pauses",
            token=lease_a.token,
            outcome="no renewal; client still retains old token",
            resource_value=resource.value,
        )
    )

    # t=6: A's lease expired, so B legitimately becomes the new owner.
    lease_b = coordinator.acquire("worker-B", now=6.0)
    events.append(
        Event(
            time=6.0,
            actor="worker-B",
            action="acquire lease",
            token=lease_b.token,
            outcome=f"lease valid until t={lease_b.expires_at}",
            resource_value=resource.value,
        )
    )

    accepted, reason = resource.write("B:authoritative-write", lease_b.token)
    events.append(
        Event(
            time=6.5,
            actor="worker-B",
            action="write B:authoritative-write",
            token=lease_b.token,
            outcome=("accepted: " if accepted else "rejected: ") + reason,
            resource_value=resource.value,
        )
    )

    # t=7: A resumes. It does not know its lease expired and still has token 1.
    events.append(
        Event(
            time=7.0,
            actor="worker-A",
            action="process resumes",
            token=lease_a.token,
            outcome="client incorrectly assumes it still owns the resource",
            resource_value=resource.value,
        )
    )

    accepted, reason = resource.write("A:stale-resumed-write", lease_a.token)
    events.append(
        Event(
            time=7.1,
            actor="worker-A",
            action="write A:stale-resumed-write",
            token=lease_a.token,
            outcome=("accepted: " if accepted else "rejected: ") + reason,
            resource_value=resource.value,
        )
    )

    return events


def print_table(events: list[Event]) -> None:
    print(
        f"{'time':>6}  {'actor':<10}  {'token':>5}  "
        f"{'action':<29}  outcome"
    )
    print("-" * 118)
    for event in events:
        token = "-" if event.token is None else str(event.token)
        print(
            f"{event.time:>6.1f}  {event.actor:<10}  {token:>5}  "
            f"{event.action:<29}  {event.outcome}"
        )
        print(f"{'':>27}resource value -> {event.resource_value!r}")


def run_mode(mode: str, as_json: bool) -> int:
    fenced = mode == "safe"
    events = simulate(fenced=fenced)

    if as_json:
        print(json.dumps([asdict(event) for event in events], indent=2))
    else:
        title = (
            "SAFE: resource enforces monotonically increasing fencing tokens"
            if fenced
            else "UNSAFE: lease exists, but resource does not enforce fencing"
        )
        print(title)
        print("=" * len(title))
        print_table(events)
        print()
        final = events[-1]
        if fenced:
            print(
                "Invariant preserved: worker-A's stale resumed write was rejected, "
                "so worker-B's authoritative value remains."
            )
        else:
            print(
                "Invariant violated: worker-A resumed with an expired lease and "
                "overwrote worker-B because the resource accepted a stale token."
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("unsafe", "safe", "compare"),
        nargs="?",
        default="compare",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "compare":
        if args.as_json:
            print(
                json.dumps(
                    {
                        "unsafe": [
                            asdict(event) for event in simulate(fenced=False)
                        ],
                        "safe": [asdict(event) for event in simulate(fenced=True)],
                    },
                    indent=2,
                )
            )
            return 0

        run_mode("unsafe", as_json=False)
        print("\n" + "#" * 118 + "\n")
        run_mode("safe", as_json=False)
        return 0

    return run_mode(args.mode, as_json=args.as_json)


if __name__ == "__main__":
    raise SystemExit(main())
