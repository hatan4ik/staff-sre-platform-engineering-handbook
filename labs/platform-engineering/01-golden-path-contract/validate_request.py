#!/usr/bin/env python3
"""Validate a platform service request against a small golden-path policy.

This is a teaching lab, not a production policy engine. It intentionally uses only
Python's standard library so candidates can run it without installing packages.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,62}$")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{5,127}$")


class ValidationError(Exception):
    """Raised when an input file cannot be loaded or has the wrong top-level type."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc

    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(value, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return value


def require_mapping(parent: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key}: must be an object")
        return {}
    return value


def require_string(
    parent: dict[str, Any], key: str, path: str, errors: list[str]
) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key}: must be a non-empty string")
        return ""
    return value.strip()


def require_boolean(
    parent: dict[str, Any], key: str, path: str, errors: list[str]
) -> bool | None:
    value = parent.get(key)
    if not isinstance(value, bool):
        errors.append(f"{path}.{key}: must be true or false")
        return None
    return value


def require_non_negative_int(
    parent: dict[str, Any], key: str, path: str, errors: list[str]
) -> int | None:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"{path}.{key}: must be a non-negative integer")
        return None
    return value


def list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return []
    return value


def validate(request: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    api_version = require_string(request, "apiVersion", "request", errors)
    kind = require_string(request, "kind", "request", errors)
    metadata = require_mapping(request, "metadata", errors)
    spec = require_mapping(request, "spec", errors)

    supported_versions = list_of_strings(policy.get("supportedApiVersions"))
    supported_kinds = list_of_strings(policy.get("supportedKinds"))

    if api_version and api_version not in supported_versions:
        errors.append(
            f"request.apiVersion: unsupported value {api_version!r}; "
            f"supported values: {supported_versions}"
        )
    if kind and kind not in supported_kinds:
        errors.append(
            f"request.kind: unsupported value {kind!r}; supported values: {supported_kinds}"
        )

    name = require_string(metadata, "name", "metadata", errors)
    request_id = require_string(metadata, "requestId", "metadata", errors)

    if name and not NAME_PATTERN.fullmatch(name):
        errors.append(
            "metadata.name: use 3-63 lowercase letters, digits, or hyphens, "
            "starting with a letter"
        )
    if request_id and not REQUEST_ID_PATTERN.fullmatch(request_id):
        errors.append("metadata.requestId: must be a stable 6-128 character idempotency key")

    owner = require_string(spec, "owner", "spec", errors)
    environment = require_string(spec, "environment", "spec", errors)
    region = require_string(spec, "region", "spec", errors)
    service_tier = require_string(spec, "serviceTier", "spec", errors)
    data_classification = require_string(spec, "dataClassification", "spec", errors)
    public_exposure = require_boolean(spec, "publicExposure", "spec", errors)

    owner_prefix = policy.get("ownerPrefix")
    if owner and isinstance(owner_prefix, str) and not owner.startswith(owner_prefix):
        errors.append(f"spec.owner: must start with {owner_prefix!r}")

    environments = list_of_strings(policy.get("environments"))
    if environment and environment not in environments:
        errors.append(
            f"spec.environment: unsupported value {environment!r}; "
            f"supported values: {environments}"
        )

    regions_by_environment = policy.get("regionsByEnvironment")
    if not isinstance(regions_by_environment, dict):
        errors.append("policy.regionsByEnvironment: policy is malformed")
        allowed_regions: list[str] = []
    else:
        allowed_regions = list_of_strings(regions_by_environment.get(environment))

    if region and environment and region not in allowed_regions:
        errors.append(
            f"spec.region: {region!r} is not supported for {environment!r}; "
            f"supported values: {allowed_regions}"
        )

    classifications = list_of_strings(policy.get("dataClassifications"))
    if data_classification and data_classification not in classifications:
        errors.append(
            f"spec.dataClassification: unsupported value {data_classification!r}; "
            f"supported values: {classifications}"
        )

    exposure_allowed_for = list_of_strings(policy.get("publicExposureAllowedFor"))
    if public_exposure is True and data_classification not in exposure_allowed_for:
        errors.append(
            "spec.publicExposure: public exposure is not permitted for "
            f"data classification {data_classification!r}"
        )

    tiers = policy.get("serviceTiers")
    if not isinstance(tiers, dict):
        errors.append("policy.serviceTiers: policy is malformed")
        tier_policy: dict[str, Any] = {}
    else:
        raw_tier_policy = tiers.get(service_tier)
        tier_policy = raw_tier_policy if isinstance(raw_tier_policy, dict) else {}

    if service_tier and not tier_policy:
        errors.append(
            f"spec.serviceTier: unsupported value {service_tier!r}; "
            f"supported values: {sorted(tiers) if isinstance(tiers, dict) else []}"
        )

    recovery = require_mapping(spec, "recovery", errors)
    rpo = require_non_negative_int(recovery, "rpoMinutes", "spec.recovery", errors)
    rto = require_non_negative_int(recovery, "rtoMinutes", "spec.recovery", errors)

    max_rpo = tier_policy.get("maximumRpoMinutes")
    max_rto = tier_policy.get("maximumRtoMinutes")

    if rpo is not None and isinstance(max_rpo, int) and rpo > max_rpo:
        errors.append(
            f"spec.recovery.rpoMinutes: {rpo} exceeds the {service_tier!r} "
            f"tier maximum of {max_rpo}"
        )
    if rto is not None and isinstance(max_rto, int) and rto > max_rto:
        errors.append(
            f"spec.recovery.rtoMinutes: {rto} exceeds the {service_tier!r} "
            f"tier maximum of {max_rto}"
        )

    if environment == "production" and service_tier == "critical":
        if rpo is not None and rpo == 0:
            errors.append(
                "spec.recovery.rpoMinutes: zero-data-loss requires a separately "
                "reviewed synchronous durability design"
            )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            f"Usage: {Path(argv[0]).name} SERVICE_REQUEST.json POLICY.json",
            file=sys.stderr,
        )
        return 2

    request_path = Path(argv[1])
    policy_path = Path(argv[2])

    try:
        request = load_json(request_path)
        policy = load_json(policy_path)
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate(request, policy)
    if errors:
        print("INVALID: request cannot enter the provisioning workflow")
        for index, error in enumerate(errors, start=1):
            print(f"  {index}. {error}")
        return 1

    metadata = request["metadata"]
    print(f"VALID: {metadata['name']} can enter the provisioning workflow")
    print(f"REQUEST_ID: {metadata['requestId']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
