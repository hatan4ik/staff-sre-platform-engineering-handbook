# AWS Staff/Principal Mock Interview Sessions

This directory turns the written curriculum into timed, repeatable interview runs.

## Day 1 baseline

The first session deliberately samples six different reasoning modes:

1. EKS capacity and failure domains
2. Terraform state integrity
3. request-path incident response
4. postmortem leadership
5. multi-Region authority transfer
6. high-volume event processing

Run it cold before rereading the model answers.

```bash
cd tracks/aws/mock-sessions
python3 mock_runner.py --validate-only
python3 mock_runner.py
```

The default run:

- presents each initial prompt;
- times the spoken answer;
- presents adversarial follow-ups one at a time;
- asks for one immediate correction per question;
- reveals expected coverage after the complete exam;
- collects the repository's 100-point scorecard;
- writes a Markdown report under `reports/`.

Use an external phone, screen recorder, or meeting application for audio/video recording. The runner does not access a microphone or camera.

## Practice mode

Reveal coverage and unsafe signals immediately after each question:

```bash
python3 mock_runner.py --practice
```

Practice mode is useful after the cold baseline, not before it.

## Custom report location

```bash
python3 mock_runner.py \
  --output ~/interview-results/aws-baseline-01.md
```

## Validate and test

```bash
python3 mock_runner.py --validate-only
python3 -m unittest -v
```

The runner and session definition use only Python's standard library.

## Scoring interpretation

| Total | Calibration |
|---:|---|
| 90–100 | Strong Principal / exceptional Staff |
| 82–89 | Strong Staff; Principal possible with leadership evidence |
| 74–81 | Staff or strong Senior depending on consistency |
| 65–73 | Senior; material Staff gaps |
| 50–64 | Mixed Senior signal |
| Below 50 | No hire for a senior infrastructure role |

A numerical result never overrides an unsafe answer involving state corruption, weak security boundaries, fabricated experience, blame-based incident leadership, or uncontrolled failover.

## Day 1 operating sequence

```text
1. Start external recording.
2. Run the session in exam mode.
3. Do not pause to look up AWS documentation.
4. Score honestly.
5. Review filler words, structure, and unsupported certainty.
6. Select the two lowest-signal questions.
7. Read only those deep chapters.
8. Rerun those two answers in practice mode.
9. Complete one missing personal-evidence field.
```

## Evidence integrity

During every mock:

- Label hypothetical architecture as hypothetical.
- Label AKS, Terraform, Kubernetes, and stream exercises as assignments or labs.
- Use SES/O3b, Alexander Street Press, Pipl, and the large MySQL migration only where the stated fact is documented or personally verified.
- Do not invent availability, traffic, cost, incident, or delivery metrics.
- Do not guess a current AWS quota.

## Adding a new session

Create another JSON file using the existing schema:

```json
{
  "id": "unique-session-id",
  "title": "Session title",
  "description": "Purpose",
  "rules": ["Rule"],
  "questions": [
    {
      "id": "q1",
      "title": "Question title",
      "prompt": "Prompt",
      "target_seconds": 90,
      "followups": ["Follow-up"],
      "must_cover": ["Required concept"],
      "unsafe_signals": ["Unsafe claim"]
    }
  ]
}
```

Validate it before committing:

```bash
python3 mock_runner.py --session new-session.json --validate-only
```

## Readiness rule

One high score is not readiness. The current target is:

- at least **82/100** in two consecutive full sessions;
- no unsafe state, security, data, or incident decision;
- five truthful production stories with defensible evidence;
- direct answers under interruption;
- no unsupported AWS or personal metric claims.
