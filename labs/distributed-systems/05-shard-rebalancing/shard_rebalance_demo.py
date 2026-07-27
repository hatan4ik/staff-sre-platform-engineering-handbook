from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Iterable


class MigrationPhase(str, Enum):
    PREPARE = "prepare"
    COPY = "copy"
    CATCH_UP = "catch_up"
    CUTOVER = "cutover"
    CLEANUP = "cleanup"


@dataclass(frozen=True)
class Record:
    key: str
    value: str
    sequence: int


@dataclass
class ShardEntry:
    owner: str
    epoch: int


@dataclass(frozen=True)
class Route:
    owner: str
    epoch: int


@dataclass
class Migration:
    virtual_shard: int
    source: str
    target: str
    source_epoch: int
    baseline_sequence: int = 0
    replayed_through: int = 0
    phase: MigrationPhase = MigrationPhase.PREPARE


@dataclass(frozen=True)
class WriteResult:
    accepted: bool
    owner: str
    epoch: int
    reason: str
    sequence: int | None


@dataclass(frozen=True)
class ScenarioResult:
    mode: str
    key: str
    virtual_shard: int
    source: str
    target: str
    old_epoch: int
    new_epoch: int
    stale_write_accepted: bool
    stale_write_reason: str
    authoritative_value: str | None
    source_value: str | None
    target_value: str | None
    migration_phase: str
    events: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["events"] = list(self.events)
        return data


@dataclass(frozen=True)
class DistributionReport:
    counts: dict[int, int]
    average: float
    hottest_shard: int | None
    hottest_count: int
    hot_shards: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "counts": {str(k): v for k, v in sorted(self.counts.items())},
            "average": self.average,
            "hottest_shard": self.hottest_shard,
            "hottest_count": self.hottest_count,
            "hot_shards": list(self.hot_shards),
        }


def hash_partition(key: str, virtual_shards: int) -> int:
    if virtual_shards <= 0:
        raise ValueError("virtual_shards must be positive")
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    value = int.from_bytes(digest[:8], "big", signed=False)
    return value % virtual_shards


def range_partition(value: int, upper_bounds: Iterable[int]) -> int:
    bounds = tuple(upper_bounds)
    if tuple(sorted(bounds)) != bounds:
        raise ValueError("upper_bounds must be sorted")
    for index, upper_bound in enumerate(bounds):
        if value < upper_bound:
            return index
    return len(bounds)


def find_key_for_shard(
    virtual_shard: int,
    virtual_shards: int,
    prefix: str = "tenant-a",
) -> str:
    for candidate in range(100_000):
        key = f"{prefix}:key-{candidate}"
        if hash_partition(key, virtual_shards) == virtual_shard:
            return key
    raise RuntimeError("unable to find a key for requested shard")


def distribution_report(
    keys: Iterable[str],
    virtual_shards: int,
    hot_ratio: float = 2.0,
) -> DistributionReport:
    if hot_ratio <= 0:
        raise ValueError("hot_ratio must be positive")
    counts = {shard: 0 for shard in range(virtual_shards)}
    for key in keys:
        counts[hash_partition(key, virtual_shards)] += 1

    total = sum(counts.values())
    average = total / virtual_shards if virtual_shards else 0.0
    hottest_shard = max(counts, key=counts.get) if counts else None
    hottest_count = counts[hottest_shard] if hottest_shard is not None else 0
    threshold = average * hot_ratio
    hot_shards = tuple(
        shard
        for shard, count in sorted(counts.items())
        if average > 0 and count >= threshold
    )
    return DistributionReport(
        counts=counts,
        average=average,
        hottest_shard=hottest_shard,
        hottest_count=hottest_count,
        hot_shards=hot_shards,
    )


def tenant_skew(
    requests_by_tenant: dict[str, int],
    dominant_ratio: float = 0.5,
) -> tuple[str, ...]:
    if not 0 < dominant_ratio <= 1:
        raise ValueError("dominant_ratio must be in (0, 1]")
    total = sum(requests_by_tenant.values())
    if total <= 0:
        return ()
    return tuple(
        tenant
        for tenant, count in sorted(requests_by_tenant.items())
        if count / total >= dominant_ratio
    )


class Cluster:
    def __init__(
        self,
        node_names: Iterable[str],
        virtual_shards: int = 16,
    ) -> None:
        names = tuple(node_names)
        if not names:
            raise ValueError("at least one node is required")
        if virtual_shards <= 0:
            raise ValueError("virtual_shards must be positive")

        self.virtual_shards = virtual_shards
        self.nodes: dict[str, dict[str, Record]] = {name: {} for name in names}
        self.shard_map: dict[int, ShardEntry] = {
            shard: ShardEntry(owner=names[shard % len(names)], epoch=1)
            for shard in range(virtual_shards)
        }
        self.sequence = 0
        self.write_log: list[tuple[int, int, str, Record]] = []

    def virtual_shard_for(self, key: str) -> int:
        return hash_partition(key, self.virtual_shards)

    def set_owner(
        self,
        virtual_shard: int,
        owner: str,
        epoch: int = 1,
    ) -> None:
        self._require_node(owner)
        self._require_shard(virtual_shard)
        if epoch <= 0:
            raise ValueError("epoch must be positive")
        self.shard_map[virtual_shard] = ShardEntry(owner=owner, epoch=epoch)

    def snapshot_routes(self) -> dict[int, Route]:
        return {
            shard: Route(owner=entry.owner, epoch=entry.epoch)
            for shard, entry in self.shard_map.items()
        }

    def write(
        self,
        routes: dict[int, Route],
        key: str,
        value: str,
        *,
        enforce_fencing: bool,
    ) -> WriteResult:
        virtual_shard = self.virtual_shard_for(key)
        if virtual_shard not in routes:
            raise KeyError(f"router has no route for shard {virtual_shard}")

        route = routes[virtual_shard]
        self._require_node(route.owner)
        current = self.shard_map[virtual_shard]

        if enforce_fencing and (
            route.epoch != current.epoch or route.owner != current.owner
        ):
            return WriteResult(
                accepted=False,
                owner=route.owner,
                epoch=route.epoch,
                reason=(
                    f"rejected stale route owner={route.owner} epoch={route.epoch}; "
                    f"current owner={current.owner} epoch={current.epoch}"
                ),
                sequence=None,
            )

        self.sequence += 1
        record = Record(key=key, value=value, sequence=self.sequence)
        self.nodes[route.owner][key] = record
        self.write_log.append((self.sequence, virtual_shard, route.owner, record))
        return WriteResult(
            accepted=True,
            owner=route.owner,
            epoch=route.epoch,
            reason="accepted",
            sequence=self.sequence,
        )

    def begin_migration(
        self,
        virtual_shard: int,
        target: str,
    ) -> Migration:
        self._require_shard(virtual_shard)
        self._require_node(target)
        entry = self.shard_map[virtual_shard]
        if entry.owner == target:
            raise ValueError("target already owns shard")
        return Migration(
            virtual_shard=virtual_shard,
            source=entry.owner,
            target=target,
            source_epoch=entry.epoch,
        )

    def copy_snapshot(self, migration: Migration) -> None:
        self._require_phase(migration, MigrationPhase.PREPARE)
        migration.baseline_sequence = self.sequence
        migration.replayed_through = migration.baseline_sequence
        for key, record in self.nodes[migration.source].items():
            if self.virtual_shard_for(key) == migration.virtual_shard:
                self.nodes[migration.target][key] = record
        migration.phase = MigrationPhase.COPY

    def catch_up(self, migration: Migration) -> int:
        if migration.phase not in (
            MigrationPhase.COPY,
            MigrationPhase.CATCH_UP,
        ):
            raise ValueError(
                f"catch-up not allowed in phase {migration.phase.value}"
            )

        replayed = 0
        for sequence, virtual_shard, owner, record in self.write_log:
            if (
                sequence > migration.replayed_through
                and virtual_shard == migration.virtual_shard
                and owner == migration.source
            ):
                self.nodes[migration.target][record.key] = record
                replayed += 1
                migration.replayed_through = sequence

        migration.replayed_through = max(
            migration.replayed_through,
            self.sequence,
        )
        migration.phase = MigrationPhase.CATCH_UP
        return replayed

    def cutover(
        self,
        migration: Migration,
        *,
        require_catch_up: bool = True,
    ) -> int:
        if require_catch_up and migration.phase != MigrationPhase.CATCH_UP:
            raise ValueError("safe cutover requires catch-up")
        if not require_catch_up and migration.phase not in (
            MigrationPhase.COPY,
            MigrationPhase.CATCH_UP,
        ):
            raise ValueError(
                f"cutover not allowed in phase {migration.phase.value}"
            )

        current = self.shard_map[migration.virtual_shard]
        if (
            current.owner != migration.source
            or current.epoch != migration.source_epoch
        ):
            raise RuntimeError("shard ownership changed during migration")

        new_epoch = current.epoch + 1
        self.shard_map[migration.virtual_shard] = ShardEntry(
            owner=migration.target,
            epoch=new_epoch,
        )
        migration.phase = MigrationPhase.CUTOVER
        return new_epoch

    def cleanup(self, migration: Migration) -> int:
        self._require_phase(migration, MigrationPhase.CUTOVER)
        deleted = 0
        for key in tuple(self.nodes[migration.source]):
            if self.virtual_shard_for(key) == migration.virtual_shard:
                del self.nodes[migration.source][key]
                deleted += 1
        migration.phase = MigrationPhase.CLEANUP
        return deleted

    def read_authoritative(self, key: str) -> Record | None:
        shard = self.virtual_shard_for(key)
        owner = self.shard_map[shard].owner
        return self.nodes[owner].get(key)

    def read_from(self, owner: str, key: str) -> Record | None:
        self._require_node(owner)
        return self.nodes[owner].get(key)

    def _require_node(self, owner: str) -> None:
        if owner not in self.nodes:
            raise KeyError(f"unknown node {owner}")

    def _require_shard(self, virtual_shard: int) -> None:
        if not 0 <= virtual_shard < self.virtual_shards:
            raise KeyError(f"invalid virtual shard {virtual_shard}")

    @staticmethod
    def _require_phase(
        migration: Migration,
        expected: MigrationPhase,
    ) -> None:
        if migration.phase != expected:
            raise ValueError(
                f"expected phase {expected.value}, got {migration.phase.value}"
            )


def simulate_rebalance(*, safe: bool) -> ScenarioResult:
    cluster = Cluster(("node-a", "node-b"), virtual_shards=8)
    virtual_shard = 3
    cluster.set_owner(virtual_shard, "node-a", epoch=7)
    key = find_key_for_shard(virtual_shard, cluster.virtual_shards)
    events: list[str] = []

    initial_router = cluster.snapshot_routes()
    first = cluster.write(
        initial_router,
        key,
        "value-v1",
        enforce_fencing=safe,
    )
    events.append(f"seed write: {first.reason}")

    stale_router = cluster.snapshot_routes()
    migration = cluster.begin_migration(virtual_shard, "node-b")
    events.append(
        f"prepare: shard={virtual_shard} source={migration.source} "
        f"target={migration.target} epoch={migration.source_epoch}"
    )

    cluster.copy_snapshot(migration)
    events.append(f"copy: baseline sequence={migration.baseline_sequence}")

    during_migration = cluster.write(
        stale_router,
        key,
        "value-v2",
        enforce_fencing=safe,
    )
    events.append(
        f"write during copy: accepted={during_migration.accepted} "
        f"sequence={during_migration.sequence}"
    )

    if safe:
        replayed = cluster.catch_up(migration)
        events.append(f"catch-up: replayed={replayed}")
        new_epoch = cluster.cutover(migration, require_catch_up=True)
    else:
        new_epoch = cluster.cutover(migration, require_catch_up=False)

    events.append(f"cutover: owner=node-b epoch={new_epoch}")

    stale = cluster.write(
        stale_router,
        key,
        "value-v3-from-stale-router",
        enforce_fencing=safe,
    )
    events.append(f"post-cutover stale write: {stale.reason}")

    if safe:
        deleted = cluster.cleanup(migration)
        events.append(f"cleanup: deleted_from_source={deleted}")

    authoritative = cluster.read_authoritative(key)
    source = cluster.read_from("node-a", key)
    target = cluster.read_from("node-b", key)

    return ScenarioResult(
        mode="safe" if safe else "unsafe",
        key=key,
        virtual_shard=virtual_shard,
        source="node-a",
        target="node-b",
        old_epoch=7,
        new_epoch=new_epoch,
        stale_write_accepted=stale.accepted,
        stale_write_reason=stale.reason,
        authoritative_value=authoritative.value if authoritative else None,
        source_value=source.value if source else None,
        target_value=target.value if target else None,
        migration_phase=migration.phase.value,
        events=tuple(events),
    )


def sample_distribution() -> dict[str, object]:
    virtual_shards = 16
    keys = [
        f"tenant-{tenant}:object-{index}"
        for tenant in range(50)
        for index in range(20)
    ]
    hot_key = find_key_for_shard(
        5,
        virtual_shards,
        prefix="celebrity",
    )
    keys.extend([hot_key] * 500)
    report = distribution_report(keys, virtual_shards, hot_ratio=2.0)
    tenants = tenant_skew(
        {
            "tenant-normal-a": 100,
            "tenant-normal-b": 120,
            "tenant-hot": 900,
        },
        dominant_ratio=0.5,
    )
    return {
        "virtual_shards": virtual_shards,
        "hot_key": hot_key,
        "distribution": report.to_dict(),
        "dominant_tenants": list(tenants),
        "range_partition_examples": {
            str(value): range_partition(value, (100, 1_000, 10_000))
            for value in (5, 500, 5_000, 50_000)
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Simulate shard-map rebalancing, ownership epochs, and skew."
        )
    )
    parser.add_argument(
        "scenario",
        choices=("unsafe", "safe", "compare", "distribution", "all"),
        help="scenario to execute",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    payload: object
    if args.scenario == "unsafe":
        payload = simulate_rebalance(safe=False).to_dict()
    elif args.scenario == "safe":
        payload = simulate_rebalance(safe=True).to_dict()
    elif args.scenario == "compare":
        payload = {
            "unsafe": simulate_rebalance(safe=False).to_dict(),
            "safe": simulate_rebalance(safe=True).to_dict(),
        }
    elif args.scenario == "distribution":
        payload = sample_distribution()
    else:
        payload = {
            "rebalance": {
                "unsafe": simulate_rebalance(safe=False).to_dict(),
                "safe": simulate_rebalance(safe=True).to_dict(),
            },
            "distribution": sample_distribution(),
        }

    print(json.dumps(payload, indent=2, sort_keys=args.json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
