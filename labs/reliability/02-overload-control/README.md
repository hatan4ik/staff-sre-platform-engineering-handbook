# Overload Control and Retry Amplification Lab

This deterministic standard-library lab compares two operating models:

- mixed traffic with broad retries;
- bounded admission with reserved critical capacity and a retry budget.

Run:

```bash
python3 labs/reliability/02-overload-control/overload_simulator.py
```

Try a harsher dependency failure:

```bash
python3 labs/reliability/02-overload-control/overload_simulator.py \
  --critical 800 \
  --optional 1200 \
  --capacity 1000 \
  --failure-percent 55 \
  --max-retries 4 \
  --critical-reservation-percent 85
```

## Interview exercise

Explain:

1. why optional work is rejected before critical work;
2. why retry attempts are separate from useful completions;
3. why adding caller capacity might worsen a constrained dependency;
4. which SLOs and abort conditions would be used in production;
5. how backlog drain would be controlled after recovery.

The simulator is educational evidence, not a production benchmark.
