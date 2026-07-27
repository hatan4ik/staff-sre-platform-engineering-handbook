#!/usr/bin/env python3
"""Discrete retry-amplification simulator.

The program models a synchronous call chain in which every layer may retry the
layer below it. It makes the difference between logical requests and physical
attempts visible and shows why retry ownership and jitter matter.

Only Python's standard library is required.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class Config:
    logical_requests: int = 1000
    service_layers: int = 3
    retries_per_layer: int = 2
    dependency_failure_rate: float = 0.65
    dependency_latency_ms: float = 40.0
    base_backoff_ms: float = 50.0
    max_backoff_ms: float = 1000.0
    jitter: bool = False
    mode: str = "layered"
    seed: int = 7
    histogram_bucket_ms: int = 50


@dataclass
class RequestResult:
    success: bool
    completion_ms: float
    attempts_by_layer: list[int]
    dependency_attempt_times_ms: list[float]


@dataclass
class SimulationResult:
    config: Config
    successful_requests: int
    failed_requests: int
    total_calls_by_layer: list[int]
    total_dependency_attempts: int
    dependency_attempts_per_logical_request: float
    p50_completion_ms: float
    p95_completion_ms: float
    p99_completion_ms: float
    retry_wave_histogram: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["config"] = asdict(self.config)
        return data


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def retry_limit(layer: int, config: Config) -> int:
    if config.mode == "none":
        return 0
    if config.mode == "edge":
        return config.retries_per_layer if layer == 0 else 0
    if config.mode == "layered":
        return config.retries_per_layer
    raise ValueError(f"Unsupported mode: {config.mode}")


def backoff_ms(retry_number: int, config: Config, rng: random.Random) -> float:
    ceiling = min(
        config.max_backoff_ms,
        config.base_backoff_ms * (2 ** max(0, retry_number - 1)),
    )
    if config.jitter:
        return rng.uniform(0.0, ceiling)
    return ceiling


def simulate_request(config: Config, rng: random.Random) -> RequestResult:
    # service_layers counts retry-capable caller layers. The dependency is the
    # final leaf and is represented by index service_layers.
    calls = [0 for _ in range(config.service_layers + 1)]
    dependency_attempt_times: list[float] = []

    def call(layer: int, start_ms: float) -> tuple[bool, float]:
        calls[layer] += 1

        if layer == config.service_layers:
            dependency_attempt_times.append(start_ms)
            completed = start_ms + config.dependency_latency_ms
            success = rng.random() >= config.dependency_failure_rate
            return success, completed

        current_time = start_ms
        max_retries = retry_limit(layer, config)

        for attempt_index in range(max_retries + 1):
            success, completed = call(layer + 1, current_time)
            if success:
                return True, completed

            current_time = completed
            if attempt_index < max_retries:
                current_time += backoff_ms(attempt_index + 1, config, rng)

        return False, current_time

    success, completion = call(0, 0.0)
    return RequestResult(
        success=success,
        completion_ms=completion,
        attempts_by_layer=calls,
        dependency_attempt_times_ms=dependency_attempt_times,
    )


def build_histogram(
    attempt_times: Iterable[float], bucket_ms: int, max_buckets: int = 30
) -> dict[str, int]:
    counts: Counter[int] = Counter()
    for timestamp in attempt_times:
        counts[int(timestamp // bucket_ms)] += 1

    histogram: dict[str, int] = {}
    for bucket in sorted(counts)[:max_buckets]:
        lower = bucket * bucket_ms
        upper = lower + bucket_ms
        histogram[f"{lower:04d}-{upper:04d}ms"] = counts[bucket]

    omitted = len(counts) - len(histogram)
    if omitted > 0:
        histogram[f"... {omitted} later buckets omitted"] = 0
    return histogram


def run(config: Config) -> SimulationResult:
    if config.logical_requests <= 0:
        raise ValueError("logical_requests must be greater than zero")
    if config.service_layers <= 0:
        raise ValueError("service_layers must be greater than zero")
    if config.retries_per_layer < 0:
        raise ValueError("retries_per_layer must not be negative")
    if not 0.0 <= config.dependency_failure_rate <= 1.0:
        raise ValueError("dependency_failure_rate must be between 0 and 1")

    rng = random.Random(config.seed)
    results = [simulate_request(config, rng) for _ in range(config.logical_requests)]

    total_calls = [0 for _ in range(config.service_layers + 1)]
    all_attempt_times: list[float] = []
    completion_times: list[float] = []

    for result in results:
        completion_times.append(result.completion_ms)
        all_attempt_times.extend(result.dependency_attempt_times_ms)
        for index, count in enumerate(result.attempts_by_layer):
            total_calls[index] += count

    successful = sum(1 for item in results if item.success)
    dependency_attempts = total_calls[-1]

    return SimulationResult(
        config=config,
        successful_requests=successful,
        failed_requests=config.logical_requests - successful,
        total_calls_by_layer=total_calls,
        total_dependency_attempts=dependency_attempts,
        dependency_attempts_per_logical_request=(
            dependency_attempts / config.logical_requests
        ),
        p50_completion_ms=percentile(completion_times, 0.50),
        p95_completion_ms=percentile(completion_times, 0.95),
        p99_completion_ms=percentile(completion_times, 0.99),
        retry_wave_histogram=build_histogram(
            all_attempt_times, config.histogram_bucket_ms
        ),
    )


def format_result(result: SimulationResult) -> str:
    config = result.config
    lines = [
        "Retry amplification simulation",
        "=" * 32,
        f"mode:                         {config.mode}",
        f"jitter:                       {config.jitter}",
        f"logical requests:             {config.logical_requests}",
        f"retry-capable service layers: {config.service_layers}",
        f"retries per owning layer:     {config.retries_per_layer}",
        f"dependency failure rate:      {config.dependency_failure_rate:.1%}",
        "",
        f"successful logical requests:  {result.successful_requests}",
        f"failed logical requests:      {result.failed_requests}",
        f"dependency attempts:          {result.total_dependency_attempts}",
        "dependency attempts/request: "
        f"{result.dependency_attempts_per_logical_request:.2f}",
        f"calls by layer:                {result.total_calls_by_layer}",
        f"completion p50:                {result.p50_completion_ms:.1f} ms",
        f"completion p95:                {result.p95_completion_ms:.1f} ms",
        f"completion p99:                {result.p99_completion_ms:.1f} ms",
        "",
        "Dependency-attempt timeline",
        "---------------------------",
    ]

    peak = max(result.retry_wave_histogram.values(), default=1)
    for bucket, count in result.retry_wave_histogram.items():
        bar_length = 0 if peak == 0 else round((count / peak) * 50)
        lines.append(f"{bucket:>27} | {'#' * bar_length} {count}")

    lines.extend(
        [
            "",
            "Interpretation",
            "--------------",
            "Compare logical requests with dependency attempts. A large ratio is",
            "retry amplification. Tall narrow timeline bars are synchronized retry",
            "waves. Jitter spreads those waves; single-layer retry ownership prevents",
            "multiplication across the call chain.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--layers", type=int, default=3)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--failure-rate", type=float, default=0.65)
    parser.add_argument("--dependency-latency-ms", type=float, default=40.0)
    parser.add_argument("--base-backoff-ms", type=float, default=50.0)
    parser.add_argument("--max-backoff-ms", type=float, default=1000.0)
    parser.add_argument("--bucket-ms", type=int, default=50)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--mode", choices=("none", "edge", "layered"), default="layered"
    )
    parser.add_argument("--jitter", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = Config(
        logical_requests=args.requests,
        service_layers=args.layers,
        retries_per_layer=args.retries,
        dependency_failure_rate=args.failure_rate,
        dependency_latency_ms=args.dependency_latency_ms,
        base_backoff_ms=args.base_backoff_ms,
        max_backoff_ms=args.max_backoff_ms,
        jitter=args.jitter,
        mode=args.mode,
        seed=args.seed,
        histogram_bucket_ms=args.bucket_ms,
    )

    try:
        result = run(config)
    except ValueError as exc:
        raise SystemExit(f"configuration error: {exc}") from exc

    if args.as_json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_result(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
