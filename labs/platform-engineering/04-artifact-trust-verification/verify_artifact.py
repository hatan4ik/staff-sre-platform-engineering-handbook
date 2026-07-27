#!/usr/bin/env python3
"""Verify simplified artifact evidence against deployment trust policy.

The lab assumes the cryptographic primitive has already been verified by a real
Sigstore/Cosign implementation. It focuses on authorization and semantic checks:
identity, exact digest binding, provenance, SBOM, scan age, and release approval.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ARTIFACT_PATTERN = re.compile(r"^(?P<repository>.+)@(?P<digest>sha256:[0-9a-fA-F]{64})$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


class InputError(Exception):
    """Raised when a lab file is malformed."""


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise InputError(
            f"invalid JSON in {path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(value, dict):
        raise InputError(f"{path} must contain a JSON object")
    return value


def object_field(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{path}.{key}: must be an object")
        return {}
    return value


def string_field(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key}: must be a non-empty string")
        return ""
    return value.strip()


def bool_field(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> bool | None:
    value = parent.get(key)
    if not isinstance(value, bool):
        errors.append(f"{path}.{key}: must be true or false")
        return None
    return value


def nonnegative_int(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> int | None:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        errors.append(f"{path}.{key}: must be a non-negative integer")
        return None
    return value


def string_list(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> list[str]:
    value = parent.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        errors.append(f"{path}.{key}: must be a non-empty string array")
        return []
    return value


def parse_timestamp(value: str, path: str, errors: list[str]) -> datetime | None:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        errors.append(f"{path}: must be an RFC3339 timestamp")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{path}: must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def fullmatch(pattern: str, value: str, path: str, errors: list[str]) -> bool:
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        errors.append(f"{path}: invalid regular expression: {exc}")
        return False
    return compiled.fullmatch(value) is not None


def validate(
    deployment: dict[str, Any],
    evidence: dict[str, Any],
    policy: dict[str, Any],
    now: datetime,
) -> list[str]:
    errors: list[str] = []

    environment = string_field(deployment, "environment", "deployment", errors)
    service = string_field(deployment, "service", "deployment", errors)
    owner = string_field(deployment, "owner", "deployment", errors)
    artifact = string_field(deployment, "artifact", "deployment", errors)

    expected_environment = string_field(policy, "environment", "policy", errors)
    if environment and expected_environment and environment != expected_environment:
        errors.append(
            f"deployment.environment: {environment!r} does not match policy environment "
            f"{expected_environment!r}"
        )

    match = ARTIFACT_PATTERN.fullmatch(artifact) if artifact else None
    if match is None:
        errors.append("deployment.artifact: must reference an immutable sha256 digest")
        deployment_digest = ""
        artifact_repository = ""
    else:
        deployment_digest = match.group("digest").lower()
        artifact_repository = match.group("repository")

    allowed_prefixes = string_list(
        policy, "allowedRegistryPrefixes", "policy", errors
    )
    if artifact_repository and not any(
        artifact_repository.startswith(prefix) for prefix in allowed_prefixes
    ):
        errors.append(
            f"deployment.artifact: repository {artifact_repository!r} is not allowed"
        )

    subject = object_field(evidence, "subject", "evidence", errors)
    subject_artifact = string_field(subject, "artifact", "evidence.subject", errors)
    subject_digest = string_field(subject, "digest", "evidence.subject", errors).lower()
    if subject_digest and not DIGEST_PATTERN.fullmatch(subject_digest):
        errors.append("evidence.subject.digest: must be a sha256 digest")
    if artifact and subject_artifact and artifact != subject_artifact:
        errors.append("evidence.subject.artifact: does not match deployment artifact")
    if deployment_digest and subject_digest and deployment_digest != subject_digest:
        errors.append("evidence.subject.digest: does not match deployment digest")

    signature = object_field(evidence, "signature", "evidence", errors)
    if bool_field(signature, "verified", "evidence.signature", errors) is not True:
        errors.append("evidence.signature.verified: cryptographic verification must succeed")

    issuer = string_field(
        signature, "certificateIssuer", "evidence.signature", errors
    )
    expected_issuer = string_field(policy, "certificateIssuer", "policy", errors)
    if issuer and expected_issuer and issuer != expected_issuer:
        errors.append("evidence.signature.certificateIssuer: untrusted issuer")

    identity = string_field(
        signature, "certificateIdentity", "evidence.signature", errors
    )
    identity_regex = string_field(
        policy, "certificateIdentityRegex", "policy", errors
    )
    if identity and identity_regex and not fullmatch(
        identity_regex, identity, "policy.certificateIdentityRegex", errors
    ):
        errors.append("evidence.signature.certificateIdentity: identity is not authorized")

    require_transparency = bool_field(
        policy, "requireTransparencyVerification", "policy", errors
    )
    transparency_verified = bool_field(
        signature, "transparencyVerified", "evidence.signature", errors
    )
    if require_transparency is True and transparency_verified is not True:
        errors.append(
            "evidence.signature.transparencyVerified: transparency evidence is required"
        )

    provenance = object_field(evidence, "provenance", "evidence", errors)
    predicate_type = string_field(
        provenance, "predicateType", "evidence.provenance", errors
    )
    required_predicate = string_field(
        policy, "provenancePredicateType", "policy", errors
    )
    if predicate_type and required_predicate and predicate_type != required_predicate:
        errors.append("evidence.provenance.predicateType: unsupported provenance type")

    source_repository = string_field(
        provenance, "sourceRepository", "evidence.provenance", errors
    )
    required_repository = string_field(policy, "sourceRepository", "policy", errors)
    if source_repository and required_repository and source_repository != required_repository:
        errors.append("evidence.provenance.sourceRepository: source is not approved")

    source_revision = string_field(
        provenance, "sourceRevision", "evidence.provenance", errors
    )
    if source_revision and not re.fullmatch(r"[0-9a-fA-F]{40,64}", source_revision):
        errors.append(
            "evidence.provenance.sourceRevision: expected an immutable commit digest"
        )

    source_ref = string_field(provenance, "sourceRef", "evidence.provenance", errors)
    source_ref_regex = string_field(policy, "sourceRefRegex", "policy", errors)
    if source_ref and source_ref_regex and not fullmatch(
        source_ref_regex, source_ref, "policy.sourceRefRegex", errors
    ):
        errors.append("evidence.provenance.sourceRef: source ref is not approved")

    builder_id = string_field(provenance, "builderId", "evidence.provenance", errors)
    approved_builders = string_list(policy, "approvedBuilderIds", "policy", errors)
    if builder_id and builder_id not in approved_builders:
        errors.append("evidence.provenance.builderId: builder is not approved")

    workflow = string_field(provenance, "workflow", "evidence.provenance", errors)
    approved_workflow = string_field(policy, "approvedWorkflow", "policy", errors)
    if workflow and approved_workflow and workflow != approved_workflow:
        errors.append("evidence.provenance.workflow: workflow is not approved")

    build_type = string_field(
        provenance, "buildType", "evidence.provenance", errors
    )
    approved_build_types = string_list(
        policy, "approvedBuildTypes", "policy", errors
    )
    if build_type and build_type not in approved_build_types:
        errors.append("evidence.provenance.buildType: build type is not approved")

    sbom = object_field(evidence, "sbom", "evidence", errors)
    sbom_format = string_field(sbom, "format", "evidence.sbom", errors)
    sbom_digest = string_field(sbom, "digest", "evidence.sbom", errors).lower()
    allowed_sbom_formats = string_list(
        policy, "requiredSbomFormats", "policy", errors
    )
    if sbom_format and sbom_format not in allowed_sbom_formats:
        errors.append("evidence.sbom.format: SBOM format is not approved")
    if sbom_digest and not DIGEST_PATTERN.fullmatch(sbom_digest):
        errors.append("evidence.sbom.digest: must bind the SBOM by sha256 digest")

    scan = object_field(evidence, "vulnerabilityScan", "evidence", errors)
    nonempty_scanner = string_field(scan, "scanner", "evidence.vulnerabilityScan", errors)
    scanned_at_raw = string_field(
        scan, "scannedAt", "evidence.vulnerabilityScan", errors
    )
    scanned_at = (
        parse_timestamp(scanned_at_raw, "evidence.vulnerabilityScan.scannedAt", errors)
        if scanned_at_raw
        else None
    )
    critical = nonnegative_int(
        scan, "critical", "evidence.vulnerabilityScan", errors
    )
    high = nonnegative_int(scan, "high", "evidence.vulnerabilityScan", errors)
    max_age = nonnegative_int(policy, "maxScanAgeHours", "policy", errors)
    max_critical = nonnegative_int(
        policy, "maximumCriticalVulnerabilities", "policy", errors
    )
    max_high = nonnegative_int(
        policy, "maximumHighVulnerabilities", "policy", errors
    )

    if scanned_at is not None:
        if scanned_at > now:
            errors.append("evidence.vulnerabilityScan.scannedAt: cannot be in the future")
        elif max_age is not None:
            age_hours = (now - scanned_at).total_seconds() / 3600
            if age_hours > max_age:
                errors.append(
                    f"evidence.vulnerabilityScan.scannedAt: scan is {age_hours:.1f} hours old; "
                    f"maximum is {max_age}"
                )
    if critical is not None and max_critical is not None and critical > max_critical:
        errors.append(
            f"evidence.vulnerabilityScan.critical: {critical} exceeds maximum {max_critical}"
        )
    if high is not None and max_high is not None and high > max_high:
        errors.append(
            f"evidence.vulnerabilityScan.high: {high} exceeds maximum {max_high}"
        )

    release = object_field(evidence, "releaseAuthorization", "evidence", errors)
    require_release = bool_field(
        policy, "requireReleaseAuthorization", "policy", errors
    )
    approved = bool_field(release, "approved", "evidence.releaseAuthorization", errors)
    release_environment = string_field(
        release, "environment", "evidence.releaseAuthorization", errors
    )
    release_service = string_field(
        release, "service", "evidence.releaseAuthorization", errors
    )
    release_owner = string_field(
        release, "owner", "evidence.releaseAuthorization", errors
    )

    if require_release is True and approved is not True:
        errors.append("evidence.releaseAuthorization.approved: approval is required")
    if environment and release_environment and release_environment != environment:
        errors.append("evidence.releaseAuthorization.environment: does not match deployment")
    if service and release_service and release_service != service:
        errors.append("evidence.releaseAuthorization.service: does not match deployment")
    if owner and release_owner and release_owner != owner:
        errors.append("evidence.releaseAuthorization.owner: does not match deployment")

    return errors


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("deployment", type=Path)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("policy", type=Path)
    parser.add_argument(
        "--now",
        required=True,
        help="RFC3339 verification time used for deterministic scan-age checks",
    )
    args = parser.parse_args(argv[1:])

    try:
        deployment = load_object(args.deployment)
        evidence = load_object(args.evidence)
        policy = load_object(args.policy)
        parse_errors: list[str] = []
        now = parse_timestamp(args.now, "--now", parse_errors)
        if parse_errors or now is None:
            raise InputError("; ".join(parse_errors))
        errors = validate(deployment, evidence, policy, now)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("UNTRUSTED: production deployment evidence failed policy")
        for index, error in enumerate(errors, start=1):
            print(f"  {index}. {error}")
        return 1

    print("TRUSTED: production deployment evidence satisfies policy")
    print(f"ARTIFACT: {deployment['artifact']}")
    print(f"SOURCE: {evidence['provenance']['sourceRepository']}@{evidence['provenance']['sourceRevision']}")
    print(f"BUILDER: {evidence['provenance']['builderId']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
