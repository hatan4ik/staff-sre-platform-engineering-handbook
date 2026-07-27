# Lab: Validate a Golden-Path Service Request

This lab models the first boundary of an Internal Developer Platform: converting developer intent into a validated, supportable request before any provisioning system receives credentials or changes infrastructure.

## Learning objectives

- distinguish product intent from raw cloud configuration;
- enforce bounded choices and ownership metadata;
- return actionable policy errors;
- separate validation from provisioning;
- reason about idempotency, audit, and lifecycle conditions.

## Files

- `service-request.json` — example developer intent.
- `policy.json` — platform-owned supported values and guardrails.
- `validate_request.py` — standard-library validator.

## Run

```bash
python3 validate_request.py service-request.json policy.json
```

Expected result:

```text
VALID: orders-api can enter the provisioning workflow
```

## Failure exercises

Edit `service-request.json` and retry:

1. Remove the owner.
2. Set an unsupported production region.
3. Set `publicExposure` to `true` for confidential data.
4. Request an RPO beyond the selected service tier.
5. Reuse the request ID with a different service name and discuss where idempotency history must live.

## Staff-level discussion

The validator is intentionally not a provisioning engine. In a real platform:

```text
request
  -> authentication and authorization
  -> schema and policy validation
  -> durable workflow record with idempotency key
  -> reviewed or versioned desired state
  -> provisioning control plane
  -> runtime acceptance checks
  -> status and audit evidence
```

Discuss:

- which policy belongs in the API schema, workflow, admission layer, and cloud boundary;
- how policy changes affect requests already in flight;
- how to version the request API;
- which errors are retryable;
- how to avoid leaking credentials or sensitive provider errors;
- how to prove that a resource is ready rather than merely created.
