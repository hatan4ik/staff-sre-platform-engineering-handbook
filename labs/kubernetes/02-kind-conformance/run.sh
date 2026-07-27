#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-sre-conformance}"
CREATE_CLUSTER="${CREATE_CLUSTER:-true}"
KEEP_CLUSTER="${KEEP_CLUSTER:-true}"
NAMESPACE="sre-conformance"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
  printf '[conformance] %s\n' "$*"
}

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required command not found: $1" >&2
    exit 2
  }
}

ready_endpoint_count() {
  kubectl get endpointslice \
    -n "$NAMESPACE" \
    -l kubernetes.io/service-name=probe-demo \
    -o jsonpath='{range .items[*].endpoints[*]}{.conditions.ready}{"\n"}{end}' \
    | grep -c '^true$' || true
}

wait_for_endpoint_count() {
  local expected="$1"
  local deadline=$((SECONDS + 90))
  local actual

  while (( SECONDS < deadline )); do
    actual="$(ready_endpoint_count)"
    if [[ "$actual" == "$expected" ]]; then
      log "ready endpoint count reached $expected"
      return 0
    fi
    sleep 1
  done

  kubectl get endpointslice -n "$NAMESPACE" -o yaml >&2 || true
  echo "timed out waiting for $expected ready endpoints; observed ${actual:-unknown}" >&2
  return 1
}

run_service_client() {
  local name="client-$(date +%s%N | tail -c 8)"
  kubectl run "$name" \
    -n "$NAMESPACE" \
    --image=busybox:1.36.1 \
    --restart=Never \
    --attach \
    --rm \
    --quiet \
    -- sh -c 'wget -T 5 -qO- http://probe-demo.sre-conformance.svc.cluster.local/'
}

cleanup() {
  kubectl delete pod impossible-placement -n "$NAMESPACE" --ignore-not-found >/dev/null 2>&1 || true
  if [[ "$CREATE_CLUSTER" == "true" && "$KEEP_CLUSTER" != "true" ]]; then
    kind delete cluster --name "$CLUSTER_NAME" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

require kubectl

if [[ "$CREATE_CLUSTER" == "true" ]]; then
  require kind
  require docker
  if ! kind get clusters | grep -qx "$CLUSTER_NAME"; then
    log "creating Kind cluster $CLUSTER_NAME"
    kind create cluster --name "$CLUSTER_NAME" --config "$SCRIPT_DIR/kind-config.yaml"
  else
    log "reusing existing Kind cluster $CLUSTER_NAME"
  fi
  kubectl config use-context "kind-$CLUSTER_NAME" >/dev/null
fi

log "applying probe, Service, and PDB workload"
kubectl apply -f "$SCRIPT_DIR/manifests/probe-demo.yaml"
kubectl rollout status deployment/probe-demo -n "$NAMESPACE" --timeout=180s
wait_for_endpoint_count 2

log "verifying in-cluster DNS and Service routing"
service_output="$(run_service_client)"
printf '%s\n' "$service_output"
grep -q '"ready": true' <<<"$service_output"

log "injecting an impossible nodeSelector"
kubectl apply -f "$SCRIPT_DIR/manifests/bad-placement.yaml"

placement_deadline=$((SECONDS + 60))
while (( SECONDS < placement_deadline )); do
  phase="$(kubectl get pod impossible-placement -n "$NAMESPACE" -o jsonpath='{.status.phase}' 2>/dev/null || true)"
  if [[ "$phase" == "Pending" ]] && kubectl describe pod impossible-placement -n "$NAMESPACE" | grep -q 'FailedScheduling'; then
    log "unschedulable placement produced FailedScheduling evidence"
    break
  fi
  sleep 1
done

if ! kubectl describe pod impossible-placement -n "$NAMESPACE" | grep -q 'FailedScheduling'; then
  kubectl describe pod impossible-placement -n "$NAMESPACE" >&2 || true
  echo "expected FailedScheduling evidence was not observed" >&2
  exit 1
fi
kubectl delete pod impossible-placement -n "$NAMESPACE" --wait=false >/dev/null

log "forcing one pod unready and checking EndpointSlice propagation"
pod="$(kubectl get pods -n "$NAMESPACE" -l app=probe-demo -o jsonpath='{.items[0].metadata.name}')"
kubectl exec -n "$NAMESPACE" "$pod" -- touch /tmp/force-unready
wait_for_endpoint_count 1
run_service_client >/dev/null
kubectl exec -n "$NAMESPACE" "$pod" -- rm -f /tmp/force-unready
wait_for_endpoint_count 2

log "forcing liveness failure and verifying container restart"
restart_before="$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}')"
kubectl exec -n "$NAMESPACE" "$pod" -- touch /tmp/fail-live
restart_deadline=$((SECONDS + 60))
while (( SECONDS < restart_deadline )); do
  restart_after="$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}' 2>/dev/null || echo 0)"
  if (( restart_after > restart_before )); then
    log "liveness restart count increased from $restart_before to $restart_after"
    break
  fi
  sleep 1
done

restart_after="$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.status.containerStatuses[0].restartCount}')"
if (( restart_after <= restart_before )); then
  kubectl describe pod "$pod" -n "$NAMESPACE" >&2 || true
  echo "liveness probe did not restart the container" >&2
  exit 1
fi
kubectl wait --for=condition=Ready pod/"$pod" -n "$NAMESPACE" --timeout=90s
wait_for_endpoint_count 2

log "deleting one pod and preserving graceful-drain logs"
drain_log="$(mktemp)"
kubectl logs -n "$NAMESPACE" "$pod" -f >"$drain_log" 2>&1 &
log_pid=$!
sleep 1
kubectl delete pod "$pod" -n "$NAMESPACE" --grace-period=15 --wait=true >/dev/null
wait "$log_pid" || true

if ! grep -q 'DRAIN_STARTED' "$drain_log"; then
  cat "$drain_log" >&2
  echo "graceful shutdown did not emit DRAIN_STARTED" >&2
  exit 1
fi
if ! grep -q 'DRAIN_COMPLETE' "$drain_log"; then
  cat "$drain_log" >&2
  echo "graceful shutdown did not emit DRAIN_COMPLETE" >&2
  exit 1
fi
rm -f "$drain_log"

kubectl rollout status deployment/probe-demo -n "$NAMESPACE" --timeout=180s
wait_for_endpoint_count 2
run_service_client >/dev/null

log "collecting final evidence"
kubectl get pods -n "$NAMESPACE" -o wide
kubectl get service,endpointslice,poddisruptionbudget -n "$NAMESPACE"
kubectl get events -n "$NAMESPACE" --sort-by=.lastTimestamp | tail -n 30

log "PASS: scheduling, DNS, Service routing, readiness propagation, liveness restart, and graceful drain invariants held"
