# Executable AWS and EKS Incident Labs

This directory converts the AWS interview chapters into reproducible failure experiments.

The first labs are intentionally safe and inexpensive:

- the Kubernetes exercises run on any local or disposable cluster;
- the Terraform exercise uses the built-in `terraform_data` resource and local files;
- no AWS account is required for the initial set;
- each lab separates the production lesson from the mechanics of the toy environment.

## Lab map

1. [Cohort-specific failures after a successful deployment](01-cohort-deployment-failure/README.md)
   - Run stable and canary application versions behind one Kubernetes Service.
   - Inject a defect that affects only one request cohort on the new version.
   - Prove why aggregate success rate hides the failure.
   - Mitigate by removing only the bad version while preserving evidence.

2. [Terraform partial-apply reconciliation](02-terraform-partial-apply/README.md)
   - Allow one resource to succeed before a later resource fails.
   - Compare configuration, Terraform state, and external side effects.
   - Recover without deleting state or blindly repeating destructive actions.
   - Demonstrate why provisioner side effects are outside normal provider reconciliation.

3. [Kubernetes restarts while health probes appear healthy](03-kubernetes-restart-evidence/README.md)
   - Trigger an OOM kill while the HTTP health endpoint remains successful.
   - Trigger a non-primary container crash while the application container remains healthy.
   - Recover the termination reason, exit code, previous logs, events, and resource evidence.
   - Practice distinguishing process, container, Pod, and node failure domains.

## Prerequisites

- Docker plus `kind`, `minikube`, Docker Desktop Kubernetes, or another disposable cluster
- `kubectl`
- Python 3.11 or newer
- Terraform 1.5 or newer for the Terraform lab

The manifests use public container images. Pin images to approved digests before using any pattern in a controlled production environment.

## Automated verification

The [AWS and EKS Incident Labs workflow](../../.github/workflows/aws-incident-labs.yml) performs the non-cluster checks on each relevant push or pull request:

- compiles standalone Python programs;
- parses every Kubernetes YAML document;
- compiles Python programs embedded in ConfigMaps;
- runs `terraform fmt`, `init`, and `validate`;
- proves that the Terraform experiment fails after an earlier resource succeeds;
- performs the documented recovery;
- requires the recovered workspace to produce a no-change plan.

The workflow does not claim to replace a real Kubernetes experiment. Run the manifests on a disposable cluster to observe Service routing, readiness, OOM termination, restart counts, previous logs, and events.

## Working method

For every lab:

1. State the invariant and the user-visible failure.
2. Establish the healthy baseline.
3. Inject one bounded failure.
4. Preserve evidence before restarting or redeploying.
5. Build a cohort or failure-domain matrix.
6. Choose the smallest reversible mitigation.
7. Prove recovery with user-facing evidence.
8. Explain which production controls would prevent recurrence.

## Interview conversion

After running a lab, answer in this order:

1. **Impact** — who is failing and what transaction is broken?
2. **Scope** — which version, cohort, AZ, node, container, or resource address is affected?
3. **Evidence** — what observation falsifies competing hypotheses?
4. **Mitigation** — what is the smallest reversible change?
5. **Recovery proof** — which user-facing SLI returned to normal?
6. **Prevention** — what test, guardrail, rollout policy, or observability dimension eliminates the failure class?

These labs support the chapters in [`tracks/aws/round-2`](../../tracks/aws/round-2/) and the scoring model in [`tracks/aws/MOCK_INTERVIEW_SCORECARD.md`](../../tracks/aws/MOCK_INTERVIEW_SCORECARD.md).
