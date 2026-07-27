# Lab: Stage a Policy from Audit to Enforcement

This lab models a safe admission-policy rollout without requiring a Kubernetes cluster or third-party packages.

## Learning objectives

- separate policy logic from enforcement mode;
- evaluate representative resources before cluster-wide deny;
- distinguish violations from policy-engine errors;
- understand audit, warn, and enforce behavior;
- identify why exceptions and rollout cohorts need ownership and expiry.

## Files

- `policy.json` — policy rules, environment modes, and a scoped exception.
- `resources.json` — representative Kubernetes-like workload requests.
- `evaluate_policy.py` — standard-library policy evaluator.

## Run

```bash
python3 evaluate_policy.py resources.json policy.json
```

The program prints one decision per resource and exits non-zero only when an `enforce` policy denies at least one request.

## Exercises

1. Change production mode from `enforce` to `warn` and compare the exit code.
2. Remove the exception expiry or extend its scope and explain the risk.
3. Add a workload using a mutable image tag.
4. Add a privileged system workload in an approved namespace and decide whether policy or a separate cluster class is safer.
5. Add a malformed resource and decide whether the policy engine should fail open or fail closed.

## Staff-level discussion

A real rollout should follow:

```text
fixtures and unit tests
  -> CI evaluation
  -> audit existing resources
  -> warn users
  -> fix platform templates
  -> enforce on a canary cohort
  -> expand by environment and risk
  -> expire exceptions
```

The lab intentionally shows that policy outcome and enforcement mode are separate decisions. A violation in audit mode is evidence; the same violation in enforce mode is an availability-affecting control-plane decision.
