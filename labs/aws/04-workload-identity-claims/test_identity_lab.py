from __future__ import annotations

import pathlib
import sys
import unittest

LAB_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(LAB_DIR))

from identity_lab import (  # noqa: E402
    IdentityError,
    TrustPolicy,
    build_claims,
    select_credential_source,
    sign_assertion,
    validate_assertion,
)


class IdentityLabTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = 1_800_000_000
        self.secret = b"lab-only-signing-secret"
        self.policy = TrustPolicy(
            issuer="https://issuer.prod.example",
            audience="cloud-sts",
            subject="system:serviceaccount:payments:ledger-api",
            environment="prod",
        )

    def test_exact_claims_are_allowed(self) -> None:
        token = sign_assertion(build_claims(now=self.now), self.secret)
        claims = validate_assertion(token, self.secret, self.policy, now=self.now)
        self.assertEqual(claims["sub"], self.policy.subject)

    def test_wrong_audience_is_denied(self) -> None:
        token = sign_assertion(
            build_claims(now=self.now, audience="kubernetes-api"),
            self.secret,
        )
        with self.assertRaisesRegex(IdentityError, "audience mismatch"):
            validate_assertion(token, self.secret, self.policy, now=self.now)

    def test_wrong_subject_is_denied(self) -> None:
        token = sign_assertion(
            build_claims(
                now=self.now,
                subject="system:serviceaccount:payments:default",
            ),
            self.secret,
        )
        with self.assertRaisesRegex(IdentityError, "subject mismatch"):
            validate_assertion(token, self.secret, self.policy, now=self.now)

    def test_wrong_environment_is_denied(self) -> None:
        token = sign_assertion(
            build_claims(now=self.now, environment="dev"),
            self.secret,
        )
        with self.assertRaisesRegex(IdentityError, "environment mismatch"):
            validate_assertion(token, self.secret, self.policy, now=self.now)

    def test_expired_token_is_denied(self) -> None:
        token = sign_assertion(
            build_claims(now=self.now - 3_600, lifetime_seconds=300),
            self.secret,
        )
        with self.assertRaisesRegex(IdentityError, "token expired"):
            validate_assertion(token, self.secret, self.policy, now=self.now)

    def test_tampered_token_is_denied(self) -> None:
        token = sign_assertion(build_claims(now=self.now), self.secret)
        header, payload, signature = token.split(".")
        tampered_payload = payload[:-1] + ("A" if payload[-1] != "A" else "B")
        with self.assertRaisesRegex(IdentityError, "signature validation failed"):
            validate_assertion(
                f"{header}.{tampered_payload}.{signature}",
                self.secret,
                self.policy,
                now=self.now,
            )

    def test_static_key_can_shadow_workload_identity(self) -> None:
        source = select_credential_source(
            static_environment_key=True,
            local_credentials_file=False,
            workload_assertion_valid=True,
            node_role_reachable=False,
        )
        self.assertEqual(source, "static-environment-key")

    def test_node_role_fallback_is_visible(self) -> None:
        source = select_credential_source(
            static_environment_key=False,
            local_credentials_file=False,
            workload_assertion_valid=False,
            node_role_reachable=True,
        )
        self.assertEqual(source, "node-role-fallback")


if __name__ == "__main__":
    unittest.main()
