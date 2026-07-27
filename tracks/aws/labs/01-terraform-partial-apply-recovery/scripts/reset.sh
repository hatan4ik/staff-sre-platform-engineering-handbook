#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

case "$root_dir" in
  */tracks/aws/labs/01-terraform-partial-apply-recovery|*/01-terraform-partial-apply-recovery)
    ;;
  *)
    echo "Refusing cleanup from unexpected directory: $root_dir" >&2
    exit 2
    ;;
esac

rm -rf \
  .terraform \
  .terraform.lock.hcl \
  .evidence \
  runtime \
  terraform.tfstate \
  terraform.tfstate.backup \
  recovery.tfplan

printf 'Reset complete: %s\n' "$root_dir"
