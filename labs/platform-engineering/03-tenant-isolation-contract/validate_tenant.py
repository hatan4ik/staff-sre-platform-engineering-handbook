#!/usr/bin/env python3
"""Validate a simplified tenant namespace package and workload contract.

This lab checks declared configuration only. Production isolation requires active
conformance tests against the Kubernetes, cloud, network, storage, and telemetry
control planes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


class InputError(Exception):
    """Raised for malformed lab input."""


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


def nonempty_string(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}.{key}: must be a non-empty string")
        return ""
    return value.strip()


def boolean(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> bool | None:
    value = parent.get(key)
    if not isinstance(value, bool):
        errors.append(f"{path}.{key}: must be true or false")
        return None
    return value


def positive_number(parent: dict[str, Any], key: str, path: str, errors: list[str]) -> float | None:
    value = parent.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        errors.append(f"{path}.{key}: must be a positive number")
        return None
    return float(value)


def validate(package: dict[str, Any], workload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    tenant = mapping(package, "tenant", "package", errors)
    labels = mapping(package, "namespaceLabels", "package", errors)
    rbac = mapping(package, "rbac", "package", errors)
    network = mapping(package, "network", "package", errors)
    quota = mapping(package, "quota", "package", errors)
    identity = mapping(package, "identity", "package", errors)
    storage = mapping(package, "storage", "package", errors)
    observability = mapping(package, "observability", "package", errors)

    tenant_name = nonempty_string(tenant, "name", "package.tenant", errors)
    trust_level = nonempty_string(tenant, "trustLevel", "package.tenant", errors)
    namespace = nonempty_string(tenant, "namespace", "package.tenant", errors)
    environment = nonempty_string(tenant, "environment", "package.tenant", errors)

    if trust_level not in {"cooperative-internal", "untrusted-external", "regulated"}:
        errors.append(
            "package.tenant.trustLevel: expected cooperative-internal, "
            "untrusted-external, or regulated"
        )
    if trust_level in {"untrusted-external", "regulated"}:
        errors.append(
            "tenant boundary: namespace-only package is insufficient for this trust level; "
            "select a dedicated cluster/account or an explicitly reviewed stronger design"
        )

    if labels.get("platform.example.com/owner") != tenant_name:
        errors.append("namespaceLabels: owner label must match package.tenant.name")
    if environment == "production" and labels.get("pod-security.kubernetes.io/enforce") != "restricted":
        errors.append("namespaceLabels: production tenants must enforce restricted Pod Security")
    version = labels.get("pod-security.kubernetes.io/enforce-version")
    if not isinstance(version, str) or not version.startswith("v1."):
        errors.append("namespaceLabels: Pod Security enforcement version must be pinned")

    if boolean(rbac, "allowClusterAdmin", "package.rbac", errors) is not False:
        errors.append("package.rbac.allowClusterAdmin: tenant must not receive cluster-admin")
    if boolean(rbac, "allowRoleEscalation", "package.rbac", errors) is not False:
        errors.append("package.rbac.allowRoleEscalation: must be false")
    if boolean(rbac, "allowImpersonation", "package.rbac", errors) is not False:
        errors.append("package.rbac.allowImpersonation: must be false")
    nonempty_string(rbac, "humanGroup", "package.rbac", errors)

    if boolean(network, "defaultDenyIngress", "package.network", errors) is not True:
        errors.append("package.network.defaultDenyIngress: must be true")
    if boolean(network, "defaultDenyEgress", "package.network", errors) is not True:
        errors.append("package.network.defaultDenyEgress: must be true")
    allowed_egress = network.get("allowedEgress")
    if not isinstance(allowed_egress, list) or not all(isinstance(item, str) for item in allowed_egress):
        errors.append("package.network.allowedEgress: must be an array of strings")
        allowed_egress_set: set[str] = set()
    else:
        allowed_egress_set = set(allowed_egress)

    if not isinstance(quota.get("cpuRequests"), str) or not quota.get("cpuRequests"):
        errors.append("package.quota.cpuRequests: must be declared")
    positive_number(quota, "memoryRequestsGiB", "package.quota", errors)
    positive_number(quota, "pods", "package.quota", errors)
    positive_number(quota, "servicesLoadBalancers", "package.quota", errors)

    package_sa = nonempty_string(identity, "serviceAccount", "package.identity", errors)
    nonempty_string(identity, "cloudRole", "package.identity", errors)
    trusted_namespace = nonempty_string(identity, "trustedNamespace", "package.identity", errors)
    trusted_sa = nonempty_string(identity, "trustedServiceAccount", "package.identity", errors)
    if trusted_namespace and namespace and trusted_namespace != namespace:
        errors.append("package.identity.trustedNamespace: must equal tenant namespace")
    if trusted_sa and package_sa and trusted_sa != package_sa:
        errors.append("package.identity.trustedServiceAccount: must equal serviceAccount")
    if boolean(identity, "allowNodeRoleFallback", "package.identity", errors) is not False:
        errors.append("package.identity.allowNodeRoleFallback: must be false")

    if boolean(storage, "allowHostPath", "package.storage", errors) is not False:
        errors.append("package.storage.allowHostPath: must be false")
    if boolean(storage, "encryptionRequired", "package.storage", errors) is not True:
        errors.append("package.storage.encryptionRequired: must be true")
    if environment == "production" and boolean(
        storage, "deletionProtection", "package.storage", errors
    ) is not True:
        errors.append("package.storage.deletionProtection: production must enable protection")

    if boolean(
        observability,
        "tenantScopedBackendAuthorization",
        "package.observability",
        errors,
    ) is not True:
        errors.append(
            "package.observability.tenantScopedBackendAuthorization: backend enforcement is required"
        )
    if boolean(
        observability, "crossTenantQueryAllowed", "package.observability", errors
    ) is not False:
        errors.append("package.observability.crossTenantQueryAllowed: must be false")

    metadata = mapping(workload, "metadata", "workload", errors)
    spec = mapping(workload, "spec", "workload", errors)
    workload_labels = mapping(metadata, "labels", "workload.metadata", errors)

    workload_namespace = nonempty_string(metadata, "namespace", "workload.metadata", errors)
    nonempty_string(metadata, "name", "workload.metadata", errors)
    if workload_namespace and namespace and workload_namespace != namespace:
        errors.append("workload.metadata.namespace: must equal tenant namespace")
    if workload_labels.get("platform.example.com/owner") != tenant_name:
        errors.append("workload.metadata.labels: owner must match tenant")

    workload_sa = nonempty_string(spec, "serviceAccountName", "workload.spec", errors)
    if workload_sa and package_sa and workload_sa != package_sa:
        errors.append("workload.spec.serviceAccountName: not trusted by tenant identity contract")

    for field in ("hostNetwork", "hostPID", "hostIPC"):
        if boolean(spec, field, "workload.spec", errors) is not False:
            errors.append(f"workload.spec.{field}: must be false")

    volumes = spec.get("volumes", [])
    if not isinstance(volumes, list):
        errors.append("workload.spec.volumes: must be an array")
    else:
        for index, raw_volume in enumerate(volumes):
            if not isinstance(raw_volume, dict):
                errors.append(f"workload.spec.volumes[{index}]: must be an object")
                continue
            if raw_volume.get("type") == "hostPath":
                errors.append(f"workload.spec.volumes[{index}]: hostPath is prohibited")

    containers = spec.get("containers")
    if not isinstance(containers, list) or not containers:
        errors.append("workload.spec.containers: must be a non-empty array")
        containers = []

    for index, raw_container in enumerate(containers):
        if not isinstance(raw_container, dict):
            errors.append(f"workload.spec.containers[{index}]: must be an object")
            continue
        path = f"workload.spec.containers[{index}]"
        nonempty_string(raw_container, "name", path, errors)
        image = nonempty_string(raw_container, "image", path, errors)
        if image and "@sha256:" not in image:
            errors.append(f"{path}.image: production image must be digest-pinned")

        security = mapping(raw_container, "securityContext", path, errors)
        if boolean(security, "privileged", f"{path}.securityContext", errors) is not False:
            errors.append(f"{path}.securityContext.privileged: must be false")
        if boolean(security, "runAsNonRoot", f"{path}.securityContext", errors) is not True:
            errors.append(f"{path}.securityContext.runAsNonRoot: must be true")
        if boolean(
            security,
            "allowPrivilegeEscalation",
            f"{path}.securityContext",
            errors,
        ) is not False:
            errors.append(f"{path}.securityContext.allowPrivilegeEscalation: must be false")

        resources = mapping(raw_container, "resources", path, errors)
        requests = mapping(resources, "requests", f"{path}.resources", errors)
        limits = mapping(resources, "limits", f"{path}.resources", errors)
        if not isinstance(requests.get("cpu"), str) or not requests.get("cpu"):
            errors.append(f"{path}.resources.requests.cpu: required")
        positive_number(requests, "memoryMiB", f"{path}.resources.requests", errors)
        if not isinstance(limits.get("cpu"), str) or not limits.get("cpu"):
            errors.append(f"{path}.resources.limits.cpu: required")
        positive_number(limits, "memoryMiB", f"{path}.resources.limits", errors)

        requested_egress = raw_container.get("requestedEgress", [])
        if not isinstance(requested_egress, list) or not all(
            isinstance(item, str) for item in requested_egress
        ):
            errors.append(f"{path}.requestedEgress: must be an array of strings")
        else:
            undeclared = sorted(set(requested_egress) - allowed_egress_set)
            if undeclared:
                errors.append(
                    f"{path}.requestedEgress: destinations not allowed by tenant package: {undeclared}"
                )

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            f"Usage: {Path(argv[0]).name} TENANT_PACKAGE.json WORKLOAD.json",
            file=sys.stderr,
        )
        return 2

    try:
        package = load_object(Path(argv[1]))
        workload = load_object(Path(argv[2]))
        errors = validate(package, workload)
    except InputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if errors:
        print("INVALID: tenant isolation contract failed")
        for index, error in enumerate(errors, start=1):
            print(f"  {index}. {error}")
        return 1

    tenant = package["tenant"]
    print(
        f"VALID: {tenant['name']} workload satisfies the declared "
        f"{tenant['trustLevel']} namespace contract"
    )
    print("NOTE: active cross-tenant conformance testing is still required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
