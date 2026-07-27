#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

mkdir -p .evidence
stamp="$(date -u +%Y%m%dT%H%M%SZ)"

if [[ -f terraform.tfstate ]]; then
  terraform state pull > ".evidence/state-pull-${stamp}.json"
  terraform show -json > ".evidence/terraform-show-${stamp}.json"
  terraform state list > ".evidence/state-list-${stamp}.txt"
else
  printf 'No terraform.tfstate exists at evidence-capture time.\n' \
    > ".evidence/state-missing-${stamp}.txt"
fi

{
  printf 'UTC: %s\n' "$stamp"
  printf 'PWD: %s\n' "$root_dir"
  printf '\n## Runtime directory\n'
  find runtime -maxdepth 2 -type f -print -exec ls -l {} \; -exec sha256sum {} \; 2>/dev/null || true
  printf '\n## Terraform files\n'
  find . -maxdepth 1 -type f -name '*.tf' -print -exec sha256sum {} \;
  printf '\n## Process identity\n'
  id
  printf '\n## Terraform version\n'
  terraform version
} > ".evidence/filesystem-${stamp}.txt"

printf 'Evidence captured under %s/.evidence with timestamp %s\n' "$root_dir" "$stamp"
