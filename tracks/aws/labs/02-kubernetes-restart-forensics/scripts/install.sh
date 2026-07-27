#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

command -v kubectl >/dev/null 2>&1 || {
  echo 'kubectl is required.' >&2
  exit 2
}

current_context="$(kubectl config current-context 2>/dev/null || true)"
if [[ -z "$current_context" ]]; then
  echo 'No Kubernetes context is selected.' >&2
  exit 2
fi

cat <<EOF
Installing intentional restart failures into context:
  ${current_context}
Namespace:
  restart-lab

Press Ctrl-C now if this is not a disposable/test cluster.
EOF
sleep 3

kubectl apply -f manifests/00-namespace.yaml
kubectl apply -f manifests/10-exit-zero.yaml
kubectl apply -f manifests/20-oom-after-ready.yaml
kubectl apply -f manifests/30-background-pid1.yaml
kubectl apply -f manifests/40-sidecar-restart.yaml

kubectl get deployments,pods -n restart-lab -o wide

cat <<'EOF'

The scenarios intentionally restart. Wait about 30–60 seconds, then run:
  make status
  make evidence
  kubectl get pods -n restart-lab -w
EOF
