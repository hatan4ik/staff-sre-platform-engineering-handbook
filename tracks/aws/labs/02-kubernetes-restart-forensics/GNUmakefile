SHELL := /usr/bin/env bash

.PHONY: install watch evidence status cleanup

install:
	bash scripts/install.sh

watch:
	kubectl get pods -n restart-lab -w

evidence:
	bash scripts/collect.sh

status:
	kubectl get pods -n restart-lab \
	  -o custom-columns='NAME:.metadata.name,UID:.metadata.uid,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,NODE:.spec.nodeName'

cleanup:
	bash scripts/cleanup.sh
