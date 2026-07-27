PYTHON ?= python3
SESSION ?= session-01-baseline.json

.PHONY: validate test baseline practice clean

validate:
	$(PYTHON) mock_runner.py --session $(SESSION) --validate-only

test:
	$(PYTHON) -m unittest -v

baseline:
	$(PYTHON) mock_runner.py --session $(SESSION)

practice:
	$(PYTHON) mock_runner.py --session $(SESSION) --practice

clean:
	rm -rf __pycache__ reports
