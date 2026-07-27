#!/usr/bin/env bash
set -euo pipefail

namespace="restart-lab"
root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root_dir"

command -v kubectl >/dev/null 2>&1 || {
  echo 'kubectl is required.' >&2
  exit 2
}
command -v jq >/dev/null 2>&1 || {
  echo 'jq is required.' >&2
  exit 2
}

kubectl get namespace "$namespace" >/dev/null

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out=".evidence/${stamp}"
mkdir -p "$out/pods" "$out/nodes"

kubectl config current-context > "$out/context.txt"
kubectl version -o yaml > "$out/kubectl-version.yaml" 2>&1 || true
kubectl get namespace "$namespace" -o yaml > "$out/namespace.yaml"
kubectl get deployments,replicasets,pods -n "$namespace" -o wide > "$out/workloads-wide.txt"
kubectl get deployments,replicasets,pods -n "$namespace" -o yaml > "$out/workloads.yaml"
kubectl get pods -n "$namespace" -o json > "$out/pods.json"
kubectl get events -n "$namespace" --sort-by=.lastTimestamp > "$out/events.txt" 2>&1 || true

jq -r '
  .items[] |
  .metadata.name as $pod |
  .metadata.uid as $uid |
  .spec.nodeName as $node |
  (.status.containerStatuses // [])[] |
  [
    $pod,
    $uid,
    $node,
    .name,
    (.ready|tostring),
    (.restartCount|tostring),
    (.state|tojson),
    (.lastState|tojson)
  ] | @tsv
' "$out/pods.json" > "$out/container-status.tsv"

mapfile -t pods < <(kubectl get pods -n "$namespace" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}')
for pod in "${pods[@]}"; do
  pod_dir="$out/pods/$pod"
  mkdir -p "$pod_dir"

  kubectl get pod -n "$namespace" "$pod" -o yaml > "$pod_dir/pod.yaml"
  kubectl describe pod -n "$namespace" "$pod" > "$pod_dir/describe.txt" 2>&1 || true

  mapfile -t containers < <(kubectl get pod -n "$namespace" "$pod" -o jsonpath='{range .spec.containers[*]}{.name}{"\n"}{end}')
  for container in "${containers[@]}"; do
    kubectl logs -n "$namespace" "$pod" -c "$container" --timestamps \
      > "$pod_dir/${container}-current.log" 2>&1 || true
    kubectl logs -n "$namespace" "$pod" -c "$container" --previous --timestamps \
      > "$pod_dir/${container}-previous.log" 2>&1 || true
  done

done

mapfile -t nodes < <(kubectl get pods -n "$namespace" -o jsonpath='{range .items[*]}{.spec.nodeName}{"\n"}{end}' | sort -u)
for node in "${nodes[@]}"; do
  [[ -n "$node" ]] || continue
  kubectl get node "$node" -o yaml > "$out/nodes/${node}.yaml" 2>&1 || true
  kubectl describe node "$node" > "$out/nodes/${node}-describe.txt" 2>&1 || true
done

cat > "$out/README.txt" <<EOF
Restart-forensics evidence
UTC timestamp: ${stamp}
Context: $(cat "$out/context.txt")
Namespace: ${namespace}

Start with:
  container-status.tsv
  events.txt
  pods/<pod>/describe.txt
  pods/<pod>/<container>-previous.log

Then correlate with:
  pod UID and creation time
  owner ReplicaSet/Deployment
  node conditions and events
  current image digest and rendered command
EOF

printf 'Evidence captured under %s\n' "$out"
