PYTHON ?= python3

.PHONY: test baseline hot-key slow-downstream duplicates transient-failures poison stress reset

test:
	$(PYTHON) -m unittest -v

baseline: reset
	$(PYTHON) pipeline.py \
	  --rate 500 \
	  --duration 10 \
	  --shards 8 \
	  --workers 16 \
	  --downstream-ms 2

hot-key: reset
	$(PYTHON) pipeline.py \
	  --rate 800 \
	  --duration 10 \
	  --shards 8 \
	  --workers 16 \
	  --hot-key-percent 0.60 \
	  --downstream-ms 2

slow-downstream: reset
	$(PYTHON) pipeline.py \
	  --rate 1_000 \
	  --duration 10 \
	  --shards 8 \
	  --workers 8 \
	  --shard-queue-size 100 \
	  --work-queue-size 200 \
	  --downstream-ms 25

duplicates: reset
	$(PYTHON) pipeline.py \
	  --rate 300 \
	  --duration 5 \
	  --shards 4 \
	  --workers 8 \
	  --duplicate-percent 1.0 \
	  --transient-failure-percent 0

transient-failures: reset
	$(PYTHON) pipeline.py \
	  --rate 400 \
	  --duration 10 \
	  --shards 8 \
	  --workers 16 \
	  --transient-failure-percent 0.20 \
	  --max-attempts 4

poison: reset
	$(PYTHON) pipeline.py \
	  --rate 200 \
	  --duration 8 \
	  --shards 4 \
	  --workers 8 \
	  --poison-key poison \
	  --transient-failure-percent 0

stress: reset
	$(PYTHON) pipeline.py \
	  --rate 1_500 \
	  --duration 15 \
	  --shards 12 \
	  --workers 24 \
	  --shard-queue-size 200 \
	  --work-queue-size 500 \
	  --hot-key-percent 0.35 \
	  --duplicate-percent 0.10 \
	  --transient-failure-percent 0.08 \
	  --downstream-ms 8 \
	  --poison-key poison

reset:
	rm -rf runtime
