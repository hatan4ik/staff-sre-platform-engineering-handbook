#!/usr/bin/env python3
"""Send matched cohort requests and summarize results by serving version."""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
import urllib.error
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--sleep", type=float, default=0.01)
    return parser.parse_args()


def request_once(base_url: str, cohort: str, timeout: float) -> tuple[int, str, str]:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/order",
        headers={"X-Cohort": cohort, "User-Agent": "cohort-probe/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            version = response.headers.get("X-App-Version", "unknown")
            return response.status, version, body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        version = error.headers.get("X-App-Version", "unknown")
        return error.code, version, body
    except Exception as error:  # noqa: BLE001 - probe should record transport failures
        return 0, "transport", json.dumps({"error": str(error)})


def main() -> int:
    args = parse_args()
    if args.requests < 1:
        print("--requests must be positive", file=sys.stderr)
        return 2

    counts: collections.Counter[tuple[str, str, str]] = collections.Counter()
    examples: dict[tuple[str, str], str] = {}

    for index in range(args.requests):
        cohort = "beta" if index % 2 else "general"
        status, version, body = request_once(args.url, cohort, args.timeout)
        outcome = "success" if 200 <= status < 400 else "failure"
        counts[(cohort, version, outcome)] += 1
        if outcome == "failure":
            examples.setdefault((cohort, version), body)
        if args.sleep:
            time.sleep(args.sleep)

    print("cohort result matrix")
    print("=" * 72)
    for cohort, version, outcome in sorted(counts):
        print(
            f"cohort={cohort:<8} version={version:<10} "
            f"outcome={outcome:<7} count={counts[(cohort, version, outcome)]}"
        )

    failures = sum(
        count
        for (cohort, version, outcome), count in counts.items()
        if outcome == "failure"
    )
    print("=" * 72)
    print(f"requests={args.requests} failures={failures}")

    for (cohort, version), body in sorted(examples.items()):
        print(f"example failure cohort={cohort} version={version}: {body}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
