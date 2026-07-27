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
└── leadership/
```

## Active curriculum indexes

- [Linux](linux/README.md)
- [Distributed systems](distributed-systems/README.md)
- [Platform engineering](platform-engineering/README.md)
- [Security](security/README.md)

Additional domains are expanded incrementally. Company tracks should link to canonical foundations rather than duplicate them.

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
16. Hands-on lab.
17. Adversarial follow-ups.
18. Official primary references.

## Source-of-truth rule

Company tracks link to these chapters. They do not copy and fork the foundational explanation.
