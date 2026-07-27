#!/usr/bin/env bash
set -euo pipefail

namespace="restart-lab"

if kubectl get namespace "$namespace" >/dev/null 2>&1; then
  kubectl delete namespace "$namespace" --wait=true
else
  echo "Namespace $namespace is already absent."
fi
