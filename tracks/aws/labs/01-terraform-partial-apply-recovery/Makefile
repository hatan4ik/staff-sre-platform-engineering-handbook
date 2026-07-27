SHELL := /usr/bin/env bash

TF_VARS_HEALTHY := -var='generation=1' -var='fail_after_create=false'
TF_VARS_FAILING := -var='generation=1' -var='fail_after_create=true'

.PHONY: init fail healthy recover evidence verify reset fmt validate

init:
	terraform init

fmt:
	terraform fmt -check -recursive

validate:
	terraform validate

fail:
	@echo 'The apply below is expected to fail with exit code 42.'
	@set +e; terraform apply -auto-approve $(TF_VARS_FAILING); rc=$$?; set -e; \
	if [[ $$rc -eq 0 ]]; then \
	  echo 'ERROR: failure injection did not fail.' >&2; exit 1; \
	fi; \
	echo "Observed expected non-zero Terraform exit: $$rc"

healthy:
	terraform apply -auto-approve $(TF_VARS_HEALTHY)

recover:
	terraform plan $(TF_VARS_HEALTHY) -out=recovery.tfplan
	terraform show recovery.tfplan
	terraform apply recovery.tfplan

 evidence:
	./scripts/evidence.sh

verify:
	@terraform plan -detailed-exitcode $(TF_VARS_HEALTHY) >/tmp/terraform-lab-plan.txt; rc=$$?; \
	cat /tmp/terraform-lab-plan.txt; \
	if [[ $$rc -ne 0 ]]; then \
	  echo "Expected an empty plan; terraform exited $$rc" >&2; exit $$rc; \
	fi

reset:
	./scripts/reset.sh
