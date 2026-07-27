#!/usr/bin/env python3
"""Evaluate Kubernetes-like JSON resources against staged platform policy.

This lab intentionally models only a few rules and uses Python's standard
library. It is not a replacement for Kubernetes admission policy engines.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIGEST_IMAGE = re.compile(r"^.+@sha256:[0-9a-fA-F]{64}$")
VALID_MODES = {"audit", "warn", "enforce"}


class InputError(Exception):
    """Raised when an input file or schema is unusable."""


@dataclass(frozen=True)
class Violation:
    rule: str
    message: str
    excepted_by: str | None = None


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def parse_time(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise InputError(f"invalid RFC3339 timestamp {value!r}") from exc
    if parsed.tzinfo is None:
        raise InputError(f"timestamp {value!r} must include a timezone")
    return parsed.astimezone(timezone.utc)


def require_dict(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise InputError(f"{path} must be an object")
    return value


def resource_identity(resource: dict[str, Any]) -> tuple[str, str, str]:
    metadata = require_dict(resource.get("metadata"), "resource.metadata")
    namespace = metadata.get("namespace")
    name = metadata.get("name")
    labels = metadata.get("labels")
    if not isinstance(namespace, str) or not namespace:
        raise InputError("resource.metadata.namespace must be a non-empty string")
    if not isinstance(name, str) or not name:
        raise InputError("resource.metadata.name must be a non-empty string")
    if not isinstance(labels, dict):
        raise InputError(f"{namespace}/{name}: metadata.labels must be an object")
    environment = labels.get("environment")
    if not isinstance(environment, str) or not environment:
        raise InputError(f"{namespace}/{name}: labels.environment is required")
    return namespace, name, environment


def active_exception(
    policy: dict[str, Any],
    resource_name: str,
    rule: str,
    now: datetime,
) -> str | None:
    exceptions = policy.get("exceptions", [])
    if not isinstance(exceptions, list):
        raise InputError("policy.exceptions must be an array")

    for raw in exceptions:
        exception = require_dict(raw, "policy.exceptions[]")
        if exception.get("resource") != resource_name or exception.get("rule") != rule:
            continue

        exception_id = exception.get("id")
        owner = exception.get("owner")
        expires_at = exception.get("expiresAt")
        if not all(isinstance(value, str) and value for value in (exception_id, owner, expires_at)):
            raise InputError(
                f"exception for {resource_name}/{rule} requires id, owner, and expiresAt"
            )
        if parse_time(expires_at) > now:
            return exception_id
    return None


def evaluate(
    resource: dict[str, Any], policy: dict[str, Any], now: datetime
) -> tuple[str, str, list[Violation]]:
    namespace, name, environment = resource_identity(resource)
    resource_name = f"{namespace}/{name}"

    modes = require_dict(policy.get("modesByEnvironment"), "policy.modesByEnvironment")
    mode = modes.get(environment)
    if mode not in VALID_MODES:
        raise InputError(
            f"{resource_name}: environment {environment!r} has invalid or missing mode"
        )

    metadata = require_dict(resource.get("metadata"), f"{resource_name}.metadata")
    labels = require_dict(metadata.get("labels"), f"{resource_name}.metadata.labels")
    spec = require_dict(resource.get("spec"), f"{resource_name}.spec")
    containers = spec.get("containers")
    if not isinstance(containers, list) or not containers:
        raise InputError(f"{resource_name}: spec.containers must be a non-empty array")

    violations: list[Violation] = []

    owner_label = policy.get("requiredOwnerLabel")
    if not isinstance(owner_label, str) or not owner_label:
        raise InputError("policy.requiredOwnerLabel must be a non-empty string")
    if not isinstance(labels.get(owner_label), str) or not labels.get(owner_label):
        violations.append(Violation("require-owner", f"missing label {owner_label}"))

    digest_environments = policy.get("requireDigestIn", [])
    if not isinstance(digest_environments, list):
        raise InputError("policy.requireDigestIn must be an array")

    privileged_environments = policy.get("denyPrivilegedIn", [])
    if not isinstance(privileged_environments, list):
        raise InputError("policy.denyPrivilegedIn must be an array")

    for index, raw_container in enumerate(containers):
        container = require_dict(raw_container, f"{resource_name}.spec.containers[{index}]")
        container_name = container.get("name", f"index-{index}")
        image = container.get("image")
        privileged = container.get("privileged", False)

        if not isinstance(image, str) or not image:
            violations.append(
                Violation("require-image", f"container {container_name!r} has no image")
            )
        elif environment in digest_environments and not DIGEST_IMAGE.fullmatch(image):
            violations.append(
                Violation(
                    "require-digest",
                    f"container {container_name!r} image must use an immutable sha256 digest",
                )
            )

        if not isinstance(privileged, bool):
            raise InputError(
                f"{resource_name}: container {container_name!r} privileged must be boolean"
            )
        if environment in privileged_environments and privileged:
            exception_id = active_exception(
                policy, resource_name, "deny-privileged", now
            )
            violations.append(
                Violation(
                    "deny-privileged",
                    f"container {container_name!r} requests privileged execution",
                    exception_id,
                )
            )

    return resource_name, mode, violations


def decision(mode: str, violations: list[Violation]) -> str:
    active = [violation for violation in violations if violation.excepted_by is None]
    if not active:
        return "ALLOW"
    if mode == "audit":
        return "ALLOW_AUDIT"
    if mode == "warn":
        return "ALLOW_WARN"
    return "DENY"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("resources", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument(
        "--now",
        help="RFC3339 evaluation time; defaults to current UTC time",
    )
    args = parser.parse_args(argv[1:])

    try:
        resources = load_json(args.resources)
        policy = require_dict(load_json(args.policy), "policy")
        if not isinstance(resources, list):
            raise InputError("resources file must contain a JSON array")
        now = parse_time(args.now) if args.now else datetime.now(timezone.utc)

        denied = False
        for index, raw_resource in enumerate(resources):
            resource = require_dict(raw_resource, f"resources[{index}]")
            resource_name, mode, violations = evaluate(resource, policy, now)
            outcome = decision(mode, violations)
            denied = denied or outcome == "DENY"
            print(f"{outcome:11} {resource_name} mode={mode}")
            for violation in violations:
                suffix = (
                    f" [EXCEPTED by {violation.excepted_by}]"
                    if violation.excepted_by
                    else ""
                )
                print(f"  - {violation.rule}: {violation.message}{suffix}")

        return 1 if denied else 0
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
