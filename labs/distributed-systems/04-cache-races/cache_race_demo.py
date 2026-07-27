#!/usr/bin/env python3
"""Demonstrate stale cache fills and cache stampedes.

The stale-fill scenario shows why delete-only invalidation is vulnerable when a
slow reader repopulates an older value after a newer write. The safe variant
keeps a version fence and rejects older fills.

The stampede scenario compares independent cache misses with single-flight
request coalescing.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class VersionedValue:
    value: str
    version: int


@dataclass
class CacheState:
    value: str | None = None
    value_version: int | None = None
    version_fence: int = 0

    def unsafe_delete(self) -> None:
        self.value = None
        self.value_version = None

    def safe_invalidate(self, new_version: int) -> None:
        self.value = None
        self.value_version = None
        self.version_fence = max(self.version_fence, new_version)

    def unsafe_fill(self, item: VersionedValue) -> tuple[bool, str]:
        self.value = item.value
        self.value_version = item.version
        return True, f"accepted fill version {item.version}"

    def safe_fill(self, item: VersionedValue) -> tuple[bool, str]:
        if item.version < self.version_fence:
            return (
                False,
                f"rejected version {item.version}; fence is {self.version_fence}",
            )
        if self.value_version is not None and item.version < self.value_version:
            return (
                False,
                f"rejected version {item.version}; cached version is "
                f"{self.value_version}",
            )
        self.value = item.value
        self.value_version = item.version
        self.version_fence = max(self.version_fence, item.version)
        return True, f"accepted fill version {item.version}"


@dataclass
class RaceEvent:
    step: int
    actor: str
    action: str
    outcome: str
    database: VersionedValue
    cache: CacheState


def snapshot_cache(cache: CacheState) -> CacheState:
    return CacheState(
        value=cache.value,
        value_version=cache.value_version,
        version_fence=cache.version_fence,
    )


def stale_fill_race(safe: bool) -> list[RaceEvent]:
    database = VersionedValue(value="profile-v1", version=1)
    cache = CacheState(value=None, value_version=None, version_fence=0)
    events: list[RaceEvent] = []

    # Reader A misses and reads v1 from the database, but pauses before filling.
    reader_a_snapshot = database
    events.append(
        RaceEvent(
            step=1,
            actor="reader-A",
            action="cache miss; read database",
            outcome="captured profile-v1/version-1, then paused",
            database=database,
            cache=snapshot_cache(cache),
        )
    )

    # Writer commits v2.
    database = VersionedValue(value="profile-v2", version=2)
    events.append(
        RaceEvent(
            step=2,
            actor="writer",
            action="commit database update",
            outcome="database now contains profile-v2/version-2",
            database=database,
            cache=snapshot_cache(cache),
        )
    )

    # Writer invalidates cache after commit.
    if safe:
        cache.safe_invalidate(new_version=database.version)
        invalidation_outcome = "cache cleared and version fence advanced to 2"
    else:
        cache.unsafe_delete()
        invalidation_outcome = "cache key deleted with no version fence"

    events.append(
        RaceEvent(
            step=3,
            actor="writer",
            action="invalidate cache",
            outcome=invalidation_outcome,
            database=database,
            cache=snapshot_cache(cache),
        )
    )

    # Reader A resumes and attempts to fill its old snapshot.
    if safe:
        accepted, reason = cache.safe_fill(reader_a_snapshot)
    else:
        accepted, reason = cache.unsafe_fill(reader_a_snapshot)

    events.append(
        RaceEvent(
            step=4,
            actor="reader-A",
            action="resume and fill cached snapshot",
            outcome=("accepted: " if accepted else "rejected: ") + reason,
            database=database,
            cache=snapshot_cache(cache),
        )
    )

    return events


@dataclass(frozen=True)
class StampedeResult:
    requests: int
    origin_loads: int
    cache_hits_after_fill: int
    mode: str
    explanation: str


def stampede(requests: int, single_flight: bool) -> StampedeResult:
    if requests <= 0:
        raise ValueError("requests must be greater than zero")

    if single_flight:
        return StampedeResult(
            requests=requests,
            origin_loads=1,
            cache_hits_after_fill=requests - 1,
            mode="single-flight",
            explanation=(
                "one request owns the fill; followers wait and reuse the result"
            ),
        )

    return StampedeResult(
        requests=requests,
        origin_loads=requests,
        cache_hits_after_fill=0,
        mode="independent-miss",
        explanation=(
            "all requests observe the miss before any fill completes and all hit origin"
        ),
    )


def event_to_dict(event: RaceEvent) -> dict[str, object]:
    return {
        "step": event.step,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "database": asdict(event.database),
        "cache": asdict(event.cache),
    }


def print_race(events: list[RaceEvent], safe: bool) -> None:
    title = (
        "SAFE STALE-FILL CONTROL: version fence rejects an old fill"
        if safe
        else "UNSAFE STALE-FILL RACE: delete-only invalidation"
    )
    print(title)
    print("=" * len(title))
    for event in events:
        print(
            f"{event.step}. {event.actor}: {event.action}\n"
            f"   {event.outcome}\n"
            f"   DB={event.database.value}@v{event.database.version}; "
            f"cache={event.cache.value!r}@{event.cache.value_version}; "
            f"fence={event.cache.version_fence}"
        )
    print()
    final = events[-1]
    if safe:
        print(
            "Invariant preserved: the cache did not resurrect version 1 after "
            "version 2 committed."
        )
    else:
        print(
            "Invariant violated: a delayed reader repopulated version 1 after "
            "version 2 committed and invalidated the key."
        )


def print_stampede(result: StampedeResult) -> None:
    print(f"mode:                  {result.mode}")
    print(f"concurrent requests:   {result.requests}")
    print(f"origin loads:          {result.origin_loads}")
    print(f"followers reusing fill:{result.cache_hits_after_fill:>5}")
    print(f"explanation:           {result.explanation}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "scenario",
        choices=("race", "stampede", "all"),
        nargs="?",
        default="all",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.scenario in ("race", "all"):
        unsafe_events = stale_fill_race(safe=False)
        safe_events = stale_fill_race(safe=True)
        if args.as_json and args.scenario == "race":
            print(
                json.dumps(
                    {
                        "unsafe": [event_to_dict(event) for event in unsafe_events],
                        "safe": [event_to_dict(event) for event in safe_events],
                    },
                    indent=2,
                )
            )
        elif not args.as_json:
            print_race(unsafe_events, safe=False)
            print("\n" + "#" * 90 + "\n")
            print_race(safe_events, safe=True)

    if args.scenario in ("stampede", "all"):
        unsafe_stampede = stampede(args.requests, single_flight=False)
        safe_stampede = stampede(args.requests, single_flight=True)
        if args.as_json and args.scenario == "stampede":
            print(
                json.dumps(
                    {
                        "unsafe": asdict(unsafe_stampede),
                        "safe": asdict(safe_stampede),
                    },
                    indent=2,
                )
            )
        elif not args.as_json:
            if args.scenario == "all":
                print("\n" + "#" * 90 + "\n")
            print("UNSAFE CACHE STAMPEDE")
            print("======================")
            print_stampede(unsafe_stampede)
            print("\nSINGLE-FLIGHT CONTROL")
            print("=====================")
            print_stampede(safe_stampede)

    if args.as_json and args.scenario == "all":
        print(
            json.dumps(
                {
                    "race": {
                        "unsafe": [
                            event_to_dict(event)
                            for event in stale_fill_race(safe=False)
                        ],
                        "safe": [
                            event_to_dict(event)
                            for event in stale_fill_race(safe=True)
                        ],
                    },
                    "stampede": {
                        "unsafe": asdict(
                            stampede(args.requests, single_flight=False)
                        ),
                        "safe": asdict(
                            stampede(args.requests, single_flight=True)
                        ),
                    },
                },
                indent=2,
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
