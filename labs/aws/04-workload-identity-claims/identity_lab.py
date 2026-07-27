from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any


class IdentityError(ValueError):
    """Raised when a workload assertion fails validation."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


@dataclass(frozen=True)
class TrustPolicy:
    issuer: str
    audience: str
    subject: str
    environment: str


def sign_assertion(claims: dict[str, Any], secret: bytes) -> str:
    """Create a compact HMAC-signed JWT-like assertion for this safe lab."""
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    encoded_payload = _b64url_encode(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(secret, signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_unverified(token: str) -> dict[str, Any]:
    """Decode claims for inspection only. This does not authenticate the token."""
    parts = token.split(".")
    if len(parts) != 3:
        raise IdentityError("token must contain three compact parts")
    try:
        payload = json.loads(_b64url_decode(parts[1]))
    except (ValueError, json.JSONDecodeError) as exc:
        raise IdentityError("payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise IdentityError("payload must be a JSON object")
    return payload


def validate_assertion(
    token: str,
    secret: bytes,
    policy: TrustPolicy,
    *,
    now: int | None = None,
    clock_skew_seconds: int = 30,
) -> dict[str, Any]:
    """Validate signature, lifetime, and exact trust-policy claims."""
    parts = token.split(".")
    if len(parts) != 3:
        raise IdentityError("token must contain three compact parts")

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected = hmac.new(secret, signing_input, hashlib.sha256).digest()
    try:
        supplied = _b64url_decode(parts[2])
    except ValueError as exc:
        raise IdentityError("signature encoding is invalid") from exc

    if not hmac.compare_digest(expected, supplied):
        raise IdentityError("signature validation failed")

    claims = decode_unverified(token)
    current = int(time.time()) if now is None else now

    required = {"iss", "aud", "sub", "env", "iat", "exp"}
    missing = sorted(required.difference(claims))
    if missing:
        raise IdentityError(f"missing required claims: {', '.join(missing)}")

    if claims["iss"] != policy.issuer:
        raise IdentityError("issuer mismatch")
    if claims["aud"] != policy.audience:
        raise IdentityError("audience mismatch")
    if claims["sub"] != policy.subject:
        raise IdentityError("subject mismatch")
    if claims["env"] != policy.environment:
        raise IdentityError("environment mismatch")

    issued_at = int(claims["iat"])
    expires_at = int(claims["exp"])
    if issued_at > current + clock_skew_seconds:
        raise IdentityError("token issued in the future")
    if expires_at <= current - clock_skew_seconds:
        raise IdentityError("token expired")
    if expires_at <= issued_at:
        raise IdentityError("expiration must be after issuance")

    return claims


def select_credential_source(
    *,
    static_environment_key: bool,
    local_credentials_file: bool,
    workload_assertion_valid: bool,
    node_role_reachable: bool,
) -> str:
    """Model a dangerous provider chain where earlier sources win."""
    if static_environment_key:
        return "static-environment-key"
    if local_credentials_file:
        return "local-credentials-file"
    if workload_assertion_valid:
        return "workload-identity"
    if node_role_reachable:
        return "node-role-fallback"
    return "no-credentials"


def build_claims(
    *,
    now: int,
    issuer: str = "https://issuer.prod.example",
    audience: str = "cloud-sts",
    subject: str = "system:serviceaccount:payments:ledger-api",
    environment: str = "prod",
    lifetime_seconds: int = 900,
) -> dict[str, Any]:
    return {
        "iss": issuer,
        "aud": audience,
        "sub": subject,
        "env": environment,
        "iat": now,
        "exp": now + lifetime_seconds,
        "pod_uid": "demo-pod-uid",
    }


def run_demo() -> int:
    now = 1_800_000_000
    secret = b"lab-only-signing-secret"
    policy = TrustPolicy(
        issuer="https://issuer.prod.example",
        audience="cloud-sts",
        subject="system:serviceaccount:payments:ledger-api",
        environment="prod",
    )

    scenarios: list[tuple[str, dict[str, Any]]] = [
        ("valid", build_claims(now=now)),
        ("wrong-audience", build_claims(now=now, audience="kubernetes-api")),
        (
            "wrong-service-account",
            build_claims(now=now, subject="system:serviceaccount:payments:default"),
        ),
        ("wrong-environment", build_claims(now=now, environment="dev")),
        ("expired", build_claims(now=now - 3_600, lifetime_seconds=300)),
    ]

    results: list[dict[str, str]] = []
    for name, claims in scenarios:
        token = sign_assertion(claims, secret)
        try:
            validate_assertion(token, secret, policy, now=now)
        except IdentityError as exc:
            results.append({"scenario": name, "result": "DENY", "reason": str(exc)})
        else:
            results.append({"scenario": name, "result": "ALLOW", "reason": "exact trust match"})

    provider_cases = [
        {
            "scenario": "clean-workload-identity",
            "source": select_credential_source(
                static_environment_key=False,
                local_credentials_file=False,
                workload_assertion_valid=True,
                node_role_reachable=False,
            ),
        },
        {
            "scenario": "static-key-shadows-federation",
            "source": select_credential_source(
                static_environment_key=True,
                local_credentials_file=False,
                workload_assertion_valid=True,
                node_role_reachable=False,
            ),
        },
        {
            "scenario": "node-role-fallback",
            "source": select_credential_source(
                static_environment_key=False,
                local_credentials_file=False,
                workload_assertion_valid=False,
                node_role_reachable=True,
            ),
        },
    ]

    print(json.dumps({"trust_policy_results": results, "provider_chain_results": provider_cases}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe workload-identity trust-policy lab")
    parser.add_argument("--demo", action="store_true", help="run the built-in positive and negative scenarios")
    args = parser.parse_args()
    if args.demo:
        return run_demo()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
