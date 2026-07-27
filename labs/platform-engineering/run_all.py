#!/usr/bin/env python3
"""Run the platform-engineering lab happy paths and expected-denial scenario."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Scenario:
    name: str
    command: tuple[str, ...]
    expected_exit: int
    expected_text: str


def main() -> int:
    root = Path(__file__).resolve().parent
    python = sys.executable

    scenarios = (
        Scenario(
            "golden-path contract",
            (
                python,
                str(root / "01-golden-path-contract" / "validate_request.py"),
                str(root / "01-golden-path-contract" / "service-request.json"),
                str(root / "01-golden-path-contract" / "policy.json"),
            ),
            0,
            "VALID:",
        ),
        Scenario(
            "staged policy rollout",
            (
                python,
                str(root / "02-policy-rollout" / "evaluate_policy.py"),
                str(root / "02-policy-rollout" / "resources.json"),
                str(root / "02-policy-rollout" / "policy.json"),
                "--now",
                "2026-07-27T12:00:00Z",
            ),
            1,
            "DENY",
        ),
        Scenario(
            "tenant isolation contract",
            (
                python,
                str(root / "03-tenant-isolation-contract" / "validate_tenant.py"),
                str(root / "03-tenant-isolation-contract" / "tenant-package.json"),
                str(root / "03-tenant-isolation-contract" / "workload.json"),
            ),
            0,
            "VALID:",
        ),
        Scenario(
            "artifact trust verification",
            (
                python,
                str(root / "04-artifact-trust-verification" / "verify_artifact.py"),
                str(root / "04-artifact-trust-verification" / "deployment.json"),
                str(root / "04-artifact-trust-verification" / "evidence.json"),
                str(root / "04-artifact-trust-verification" / "trust-policy.json"),
                "--now",
                "2026-07-27T12:00:00Z",
            ),
            0,
            "TRUSTED:",
        ),
    )

    failures = 0
    for scenario in scenarios:
        print(f"\n=== {scenario.name} ===")
        completed = subprocess.run(
            scenario.command,
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, file=sys.stderr, end="")

        output = completed.stdout + completed.stderr
        passed = (
            completed.returncode == scenario.expected_exit
            and scenario.expected_text in output
        )
        if passed:
            print(
                f"PASS: exit={completed.returncode}, "
                f"found={scenario.expected_text!r}"
            )
        else:
            failures += 1
            print(
                f"FAIL: expected exit={scenario.expected_exit} and "
                f"text={scenario.expected_text!r}; got exit={completed.returncode}"
            )

    print(f"\nSUMMARY: {len(scenarios) - failures}/{len(scenarios)} scenarios passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
