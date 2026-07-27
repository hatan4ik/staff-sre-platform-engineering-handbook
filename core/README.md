# Canonical Core Curriculum

The `core/` tree contains reusable engineering chapters shared by all interview tracks.

## Domains

```text
core/
├── linux/
├── networking/
├── kubernetes/
├── cloud/
├── platform-engineering/
├── security/
├── service-mesh/
├── ebpf-security/
├── observability/
├── reliability/
├── incident-response/
├── infrastructure-as-code/
├── delivery-gitops/
├── distributed-systems/
└── leadership/
```

## Active curriculum indexes

- [Platform engineering](platform-engineering/README.md)
- [Security](security/README.md)
- [Linux](linux/README.md)
- [Kubernetes](kubernetes/README.md)
- [Distributed systems](distributed-systems/README.md)
- [Infrastructure as code](infrastructure-as-code/README.md)
- [GitOps and progressive delivery](delivery-gitops/README.md)
- [Incident response](incident-response/README.md)
- [Observability](observability/README.md)
- [Reliability](reliability/README.md)
- [Service mesh](service-mesh/README.md)
- [eBPF and runtime security](ebpf-security/cilium-hubble-falco-tetragon.md)

Networking, cloud, and leadership continue to expand as dedicated indexes. Company tracks must link to canonical foundations rather than duplicate them.

## Chapter standard

Every canonical chapter should include:

1. Why the topic exists.
2. What an interviewer is testing.
3. Foundations from first principles.
4. Control-plane and data-plane mechanics.
5. End-to-end execution flow.
6. Scale model.
7. Failure modes.
8. Evidence and debugging path.
9. Immediate mitigation versus permanent fix.
10. Security interpretation.
11. Observability and acceptance criteria.
12. Rollout and rollback.
13. Trade-offs and dangerous answers.
14. Ninety-second and deep-dive interview answers.
15. Whiteboard model.
16. Hands-on lab or explicit validation plan.
17. Adversarial follow-ups.
18. Official primary references or a source-verification checklist for version-sensitive behavior.

## Source-of-truth rule

Company tracks link to these chapters. They do not copy and fork the foundational explanation. A deep track chapter may remain temporarily as migration source material, but canonical parity must be followed by adapter thinning and duplicate removal.
