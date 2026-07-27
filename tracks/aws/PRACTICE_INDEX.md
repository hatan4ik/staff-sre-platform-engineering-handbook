# AWS Interview Practice Index

The AWS track now has nine connected layers.

## 1. Deep technical chapters

Start with [`README.md`](README.md) and follow the 18-question sequence across:

- `round-1/` — EKS, GitOps, Terraform, security, provisioning, and autoscaling
- `round-2/` — incident response, latency, evidence, recovery, runtime failures, and postmortems
- `round-3/` — mobile backend, secure updates, multi-Region DR, observability, and event platforms

## 2. Board calibration

- [`FAANG_BOARD_REVIEW.md`](FAANG_BOARD_REVIEW.md) — Staff/Principal bar, question-by-question review, down-level signals, and adversarial corrections.
- [`MOCK_INTERVIEW_SCORECARD.md`](MOCK_INTERVIEW_SCORECARD.md) — 100-point rubric, full interview-loop structure, scenario cards, and feedback template.

## 3. Spoken-answer training

- [`SPOKEN_ANSWER_DRILLS.md`](SPOKEN_ANSWER_DRILLS.md) — 60–90 second answers for every question and rapid adversarial drills.

Practice rule:

```text
answer in 90 seconds
 -> draw in 5 minutes
 -> survive 5 follow-ups
 -> name one unsafe alternative
 -> connect to one truthful production story
 -> state the validation evidence
```

## 4. Executable baseline mock

- [`mock-sessions/README.md`](mock-sessions/README.md) — operating guide for timed mock sessions.
- [`mock-sessions/session-01-baseline.json`](mock-sessions/session-01-baseline.json) — cold Day 1 assessment across Q1, Q3, Q7, Q13, Q16, and Q18.
- [`mock-sessions/mock_runner.py`](mock-sessions/mock_runner.py) — dependency-free interactive runner that times answers, delivers adversarial follow-ups, collects the 100-point scorecard, and writes a Markdown report.

Run:

```bash
cd tracks/aws/mock-sessions
make validate
make test
make baseline
```

Use an external recorder for audio or video. The runner does not access a microphone or camera.

## 5. Truthful personal production evidence

- [`PERSONAL_STORY_BANK.md`](PERSONAL_STORY_BANK.md) — maps Nathanel's documented SES/O3b, Alexander Street Press, Pipl, large MySQL migration, AKS assignment, repository migration, observability, incident, and leadership experience to the 18 AWS questions.
- [`EVIDENCE_COMPLETION_WORKSHEET.md`](EVIDENCE_COMPLETION_WORKSHEET.md) — structured evidence intake for the five remaining gaps: platform adoption, one exact severe incident, NOC/observability outcomes, final 45 TB migration results, and five-person-team leadership.

These files separate:

- verified production facts;
- supported experience needing a precise metric;
- assignment/lab evidence;
- hypothetical architecture;
- claims that must not be made without documentation.

## 6. Interview-day compression

- [`INTERVIEW_DAY_CHEATSHEET.md`](INTERVIEW_DAY_CHEATSHEET.md) — the SCOPE and STABILIZE frameworks, 18 invariants, personal evidence anchors, six whiteboards, adversarial one-line responses, and final self-check.

This is the final review document, not the starting curriculum.

## 7. Hands-on labs

- [`labs/01-terraform-partial-apply-recovery/`](labs/01-terraform-partial-apply-recovery/) — local Terraform state and partial-apply recovery.
- [`labs/02-kubernetes-restart-forensics/`](labs/02-kubernetes-restart-forensics/) — exit-code, OOM, PID 1, sidecar, and pod-replacement evidence.
- [`labs/03-event-stream-backpressure/`](labs/03-event-stream-backpressure/) — tested Python simulator for partitioning, hot keys, bounded queues, retry, DLQ, and idempotency.
- [`../../labs/aws/README.md`](../../labs/aws/README.md) — canonical AWS/EKS cohort, Terraform, runtime, and disaster-recovery exercises.

The track-specific labs and mock runner are validated by [`.github/workflows/aws-labs-ci.yml`](../../.github/workflows/aws-labs-ci.yml).

## 8. Execution program

- [`30_DAY_EXECUTION_PLAN.md`](30_DAY_EXECUTION_PLAN.md) — daily plan from baseline recording through Round 1/2/3 mocks, lab execution, story completion, executive communication, and two full interview loops.

The outcome target is two consecutive mock scores of at least 82/100 with no unsafe state, security, or incident-response behavior.

## 9. Result artifacts

Each baseline run generates a local Markdown report containing:

- answer and follow-up timing;
- one immediate correction per question;
- all nine score dimensions;
- total calibration;
- strongest evidence;
- highest-risk gap;
- next drill;
- unsupported-claim truth check.

Generated reports remain local and are ignored by Git. Commit only deliberately sanitized results.

---

## Immediate next sequence

```text
1. Run the cold Day 1 baseline.
2. Review the two weakest answers only.
3. Complete one exact severe-incident worksheet.
4. Complete the 45 TB migration outcome and validation fields.
5. Rerun the two weakest answers in practice mode.
6. Continue Day 2 of the 30-day plan.
```

## Recommended weekly cycle after day 30

```text
Day 1: read one deep chapter and rewrite the invariant in your own words
Day 2: deliver the spoken answer and record yourself
Day 3: complete one mock card and score it honestly
Day 4: run or extend one hands-on lab
Day 5: improve one truthful production story and its evidence
Day 6: adversarial mock with interruptions
Day 7: correct the weakest evidence, not the most familiar topic
```

## Readiness criteria

A topic is interview-ready only when the candidate can:

- clarify the ambiguous requirement;
- state scale, SLO, consistency, and security assumptions;
- identify the source of truth and write authority;
- explain the largest failure domain;
- describe overload, retry, rollback, and recovery;
- answer current-version questions without guessing quotas;
- demonstrate one real incident, migration, or architecture decision;
- distinguish production experience from an assignment or hypothetical design;
- quantify results honestly;
- explain how the design was or would be proven.

Staff/Principal readiness requires technical depth **and** evidence that the candidate influenced systems, teams, standards, and outcomes.