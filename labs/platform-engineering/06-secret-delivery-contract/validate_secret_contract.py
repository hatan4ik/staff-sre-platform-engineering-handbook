#!/usr/bin/env python3
"""Validate a simplified external-secret delivery and rotation contract.

This lab checks declared intent. It does not contact a secret provider, perform
cryptographic authentication, rotate a real credential, or prove application
reload behavior.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class InputError(Exception):
    """Raised when the contract file cannot be parsed."""


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


def mapping(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        errors.append(f"{path}.{key}: must be an object")
        return {}
    return value


def text(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key}: must be a non-empty string")
        return ""
    return value.strip()


def flag(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> bool | None:
    value = parent.get(key)
    if not isinstance(value, bool):
        errors.append(f"{path}.{key}: must be true or false")
        return None
    return value


def positive_int(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> int | None:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        errors.append(f"{path}.{key}: must be a positive integer")
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
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        errors.append(f"{path}.{key}: must be an array of non-empty strings")
        return []
    return value


def validate(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    service = mapping(contract, "service", "contract", errors)
    authority = mapping(contract, "authority", "contract", errors)
    auth = mapping(contract, "providerAuthentication", "contract", errors)
    delivery = mapping(contract, "delivery", "contract", errors)
    application = mapping(contract, "application", "contract", errors)
    outage = mapping(contract, "outage", "contract", errors)
    audit = mapping(contract, "audit", "contract", errors)

    service_name = text(service, "name", "contract.service", errors)
    owner = text(service, "owner", "contract.service", errors)
    environment = text(service, "environment", "contract.service", errors)
    namespace = text(service, "namespace", "contract.service", errors)
    service_account = text(
        service, "serviceAccount", "contract.service", errors
    )

    if owner and not owner.startswith("team-"):
        errors.append("contract.service.owner: must use a team-owned identity")
    if environment not in {"development", "staging", "production"}:
        errors.append(
            "contract.service.environment: expected development, staging, or production"
        )

    authority_system = text(
        authority, "system", "contract.authority", errors
    )
    authoritative = flag(
        authority, "authoritative", "contract.authority", errors
    )
    text(authority, "region", "contract.authority", errors)
    remote_path = text(authority, "remotePath", "contract.authority", errors)
    allowed_prefix = text(
        authority, "allowedPathPrefix", "contract.authority", errors
    )
    credential_type = text(
        authority, "credentialType", "contract.authority", errors
    )
    rotation_hours = positive_int(
        authority, "rotationPeriodHours", "contract.authority", errors
    )
    overlap_hours = positive_int(
        authority, "overlapHours", "contract.authority", errors
    )

    if authoritative is not True:
        errors.append("contract.authority.authoritative: external authority must be true")
    if authority_system in {"kubernetes-secret", "environment-variable", "git"}:
        errors.append(
            "contract.authority.system: delivery caches and source control cannot be authority"
        )
    if remote_path and allowed_prefix and not remote_path.startswith(allowed_prefix):
        errors.append(
            "contract.authority.remotePath: outside the tenant's allowed path prefix"
        )
    if credential_type not in {
        "dynamic",
        "rotated-static",
        "certificate",
        "token",
    }:
        errors.append(
            "contract.authority.credentialType: unsupported credential lifecycle"
        )
    if (
        rotation_hours is not None
        and overlap_hours is not None
        and overlap_hours >= rotation_hours
    ):
        errors.append(
            "contract.authority.overlapHours: must be less than rotationPeriodHours"
        )

    auth_method = text(
        auth, "method", "contract.providerAuthentication", errors
    )
    static_used = flag(
        auth,
        "staticCredentialUsed",
        "contract.providerAuthentication",
        errors,
    )
    trusted_namespace = text(
        auth,
        "trustedNamespace",
        "contract.providerAuthentication",
        errors,
    )
    trusted_sa = text(
        auth,
        "trustedServiceAccount",
        "contract.providerAuthentication",
        errors,
    )
    audience = text(
        auth, "audience", "contract.providerAuthentication", errors
    )
    token_ttl = positive_int(
        auth,
        "maximumTokenTtlMinutes",
        "contract.providerAuthentication",
        errors,
    )

    if auth_method not in {
        "workload-identity",
        "federated-oidc",
        "vault-kubernetes-auth",
    }:
        errors.append(
            "contract.providerAuthentication.method: use a supported short-lived workload identity method"
        )
    if static_used is not False:
        errors.append(
            "contract.providerAuthentication.staticCredentialUsed: must be false"
        )
    if trusted_namespace and namespace and trusted_namespace != namespace:
        errors.append(
            "contract.providerAuthentication.trustedNamespace: must match service namespace"
        )
    if trusted_sa and service_account and trusted_sa != service_account:
        errors.append(
            "contract.providerAuthentication.trustedServiceAccount: must match service account"
        )
    if audience in {"*", "default", ""}:
        errors.append(
            "contract.providerAuthentication.audience: must be provider-specific"
        )
    if token_ttl is not None and token_ttl > 120:
        errors.append(
            "contract.providerAuthentication.maximumTokenTtlMinutes: exceeds platform maximum of 120"
        )

    mechanism = text(delivery, "mechanism", "contract.delivery", errors)
    store_scope = text(delivery, "storeScope", "contract.delivery", errors)
    store_namespace = text(
        delivery, "storeNamespace", "contract.delivery", errors
    )
    allowed_namespaces = string_list(
        delivery, "allowedNamespaces", "contract.delivery", errors
    )
    target_kind = text(delivery, "targetKind", "contract.delivery", errors)
    target_name = text(delivery, "targetName", "contract.delivery", errors)
    target_is_authority = flag(
        delivery, "targetIsAuthority", "contract.delivery", errors
    )
    refresh_policy = text(
        delivery, "refreshPolicy", "contract.delivery", errors
    )
    refresh_minutes = positive_int(
        delivery, "refreshIntervalMinutes", "contract.delivery", errors
    )
    deletion_policy = text(
        delivery, "deletionPolicy", "contract.delivery", errors
    )
    creation_policy = text(
        delivery, "creationPolicy", "contract.delivery", errors
    )

    supported_mechanisms = {
        "direct-api",
        "agent-file",
        "csi-file",
        "operator-sync",
    }
    if mechanism not in supported_mechanisms:
        errors.append("contract.delivery.mechanism: unsupported delivery mechanism")
    if store_scope not in {"Namespace", "Cluster"}:
        errors.append("contract.delivery.storeScope: expected Namespace or Cluster")
    if store_scope == "Namespace":
        if store_namespace and namespace and store_namespace != namespace:
            errors.append(
                "contract.delivery.storeNamespace: namespaced store must match service namespace"
            )
        if namespace and namespace not in allowed_namespaces:
            errors.append(
                "contract.delivery.allowedNamespaces: service namespace must be explicitly allowed"
            )
        extra = sorted(set(allowed_namespaces) - {namespace})
        if extra:
            errors.append(
                f"contract.delivery.allowedNamespaces: namespaced store contains unrelated namespaces {extra}"
            )
    else:
        if environment == "production" and len(allowed_namespaces) != 1:
            errors.append(
                "contract.delivery.allowedNamespaces: production cluster store must be narrowly selected"
            )

    if mechanism == "operator-sync":
        if target_kind != "KubernetesSecret":
            errors.append(
                "contract.delivery.targetKind: operator-sync must declare KubernetesSecret cache"
            )
        if target_is_authority is not False:
            errors.append(
                "contract.delivery.targetIsAuthority: synchronized Kubernetes Secret is only a cache"
            )
        if refresh_policy not in {"Periodic", "OnChange", "CreatedOnce"}:
            errors.append(
                "contract.delivery.refreshPolicy: unsupported operator refresh policy"
            )
    elif mechanism in {"agent-file", "csi-file"}:
        if target_kind != "MountedFile":
            errors.append(
                "contract.delivery.targetKind: file delivery must use MountedFile"
            )
    elif mechanism == "direct-api" and target_kind != "ProcessMemory":
        errors.append(
            "contract.delivery.targetKind: direct API delivery should terminate in process memory"
        )

    if not target_name:
        errors.append("contract.delivery.targetName: required")
    if refresh_minutes is not None and overlap_hours is not None:
        if refresh_minutes >= overlap_hours * 60:
            errors.append(
                "contract.delivery.refreshIntervalMinutes: must be shorter than credential overlap"
            )
    if deletion_policy not in {"Retain", "Delete", "Merge"}:
        errors.append("contract.delivery.deletionPolicy: unsupported value")
    if creation_policy not in {"Owner", "Orphan", "Merge", "None"}:
        errors.append("contract.delivery.creationPolicy: unsupported value")

    consumption = text(
        application, "consumption", "contract.application", errors
    )
    reload_method = text(
        application, "reloadMethod", "contract.application", errors
    )
    confirms_version = flag(
        application,
        "confirmsDeliveredVersion",
        "contract.application",
        errors,
    )
    startup_timeout = positive_int(
        application,
        "startupTimeoutSeconds",
        "contract.application",
        errors,
    )
    liveness_provider = flag(
        application,
        "livenessDependsOnProvider",
        "contract.application",
        errors,
    )
    readiness_credential = flag(
        application,
        "readinessRequiresUsableCredential",
        "contract.application",
        errors,
    )

    if consumption not in {
        "mounted-file",
        "environment-variable",
        "local-agent-api",
        "direct-api",
    }:
        errors.append("contract.application.consumption: unsupported pattern")
    if consumption == "environment-variable" and reload_method not in {
        "rolling-restart",
        "process-restart",
    }:
        errors.append(
            "contract.application.reloadMethod: environment variables require process restart"
        )
    if consumption == "mounted-file" and reload_method in {
        "none",
        "environment-refresh",
    }:
        errors.append(
            "contract.application.reloadMethod: mounted files need explicit reopen or restart"
        )
    if confirms_version is not True:
        errors.append(
            "contract.application.confirmsDeliveredVersion: application adoption evidence is required"
        )
    if startup_timeout is not None and startup_timeout > 600:
        errors.append(
            "contract.application.startupTimeoutSeconds: exceeds bounded platform startup window"
        )
    if liveness_provider is not False:
        errors.append(
            "contract.application.livenessDependsOnProvider: provider outage must not cause restart storms"
        )
    if readiness_credential is not True:
        errors.append(
            "contract.application.readinessRequiresUsableCredential: must be true"
        )

    existing_cache = flag(
        outage,
        "existingWorkloadsMayUseValidCache",
        "contract.outage",
        errors,
    )
    new_stale = flag(
        outage, "newPodsMayUseStaleCache", "contract.outage", errors
    )
    maximum_stale = nonnegative_int(
        outage, "maximumStaleMinutes", "contract.outage", errors
    )
    bounded_retry = flag(
        outage, "boundedRetry", "contract.outage", errors
    )
    expiry_alert = positive_int(
        outage, "expiryMarginAlertMinutes", "contract.outage", errors
    )

    if existing_cache is not True:
        errors.append(
            "contract.outage.existingWorkloadsMayUseValidCache: continuity with still-valid credentials should be explicit"
        )
    if new_stale is True and (maximum_stale is None or maximum_stale == 0):
        errors.append(
            "contract.outage.maximumStaleMinutes: stale startup requires a non-zero explicit bound"
        )
    if new_stale is False and maximum_stale not in {None, 0}:
        errors.append(
            "contract.outage.maximumStaleMinutes: must be zero when stale startup is prohibited"
        )
    if bounded_retry is not True:
        errors.append("contract.outage.boundedRetry: must be true")
    if (
        expiry_alert is not None
        and token_ttl is not None
        and expiry_alert < token_ttl
    ):
        errors.append(
            "contract.outage.expiryMarginAlertMinutes: should exceed one provider-auth token lifetime"
        )

    for field in (
        "secretReadsAudited",
        "policyChangesAudited",
        "rotationEventsAudited",
        "valueRedactionRequired",
    ):
        if flag(audit, field, "contract.audit", errors) is not True:
            errors.append(f"contract.audit.{field}: must be true")

    if mechanism == "operator-sync" and consumption == "mounted-file":
        # A Kubernetes Secret may be mounted as a file, which can update on the
        # node, but the application still needs reload behavior. This is allowed.
        pass

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            f"Usage: {Path(argv[0]).name} SECRET_CONTRACT.json",
            file=sys.stderr,
        )
        return 2

    try:
        contract = load_object(Path(argv[1]))
        errors = validate(contract)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("INVALID: secret delivery contract failed")
        for index, error in enumerate(errors, start=1):
            print(f"  {index}. {error}")
        return 1

    service = contract["service"]
    authority = contract["authority"]
    delivery = contract["delivery"]
    print("VALID: secret delivery contract is bounded and rotation-aware")
    print(
        f"SERVICE: {service['namespace']}/{service['name']} "
        f"identity={service['serviceAccount']}"
    )
    print(
        f"AUTHORITY: {authority['system']} path={authority['remotePath']}"
    )
    print(
        f"DELIVERY: {delivery['mechanism']} -> "
        f"{delivery['targetKind']}/{delivery['targetName']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
