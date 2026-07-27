#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTOR_VERSION="${COLLECTOR_VERSION:-0.157.0}"
COLLECTOR_IMAGE="${COLLECTOR_IMAGE:-otel/opentelemetry-collector:${COLLECTOR_VERSION}}"
CONTAINER_NAME="${CONTAINER_NAME:-sre-otel-collector-integration}"
HOST_PORT="${HOST_PORT:-14318}"
KEEP_CONTAINER="${KEEP_CONTAINER:-false}"
OUTPUT_FILE="${OUTPUT_FILE:-$SCRIPT_DIR/collector-output.txt}"
RESPONSE_FILE="${RESPONSE_FILE:-$SCRIPT_DIR/otlp-response.json}"

log() {
  printf '[otel-integration] %s\n' "$*"
}

require() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "required command not found: $1" >&2
    exit 2
  }
}

cleanup() {
  if [[ "$KEEP_CONTAINER" != "true" ]]; then
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

require docker
require curl

rm -f "$OUTPUT_FILE" "$RESPONSE_FILE"
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

log "starting Collector image $COLLECTOR_IMAGE"
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "127.0.0.1:${HOST_PORT}:4318" \
  -v "$SCRIPT_DIR/collector.yaml:/etc/otelcol/config.yaml:ro" \
  "$COLLECTOR_IMAGE" \
  --config=/etc/otelcol/config.yaml >/dev/null

accepted=false
for _ in $(seq 1 60); do
  if ! docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null | grep -qx true; then
    docker logs "$CONTAINER_NAME" >&2 || true
    echo "Collector exited before accepting telemetry" >&2
    exit 1
  fi

  status="$(
    curl -sS \
      --connect-timeout 1 \
      --max-time 3 \
      -o "$RESPONSE_FILE" \
      -w '%{http_code}' \
      -H 'Content-Type: application/json' \
      --data-binary "@$SCRIPT_DIR/trace.json" \
      "http://127.0.0.1:${HOST_PORT}/v1/traces" \
      2>/dev/null || true
  )"

  if [[ "$status" == "200" ]]; then
    accepted=true
    break
  fi
  sleep 1
done

if [[ "$accepted" != "true" ]]; then
  docker logs "$CONTAINER_NAME" >&2 || true
  echo "Collector did not accept the OTLP trace" >&2
  exit 1
fi

log "OTLP HTTP receiver accepted the synthetic trace"

for _ in $(seq 1 30); do
  docker logs "$CONTAINER_NAME" >"$OUTPUT_FILE" 2>&1 || true
  if grep -q 'collector-contract' "$OUTPUT_FILE" \
    && grep -q 'sre.synthetic' "$OUTPUT_FILE" \
    && grep -q 'otlp-http-to-debug-exporter' "$OUTPUT_FILE"; then
    log "debug exporter emitted the expected trace and resource attributes"
    break
  fi
  sleep 1
done

if ! grep -q 'collector-contract' "$OUTPUT_FILE"; then
  cat "$OUTPUT_FILE" >&2
  echo "span name was not found in Collector output" >&2
  exit 1
fi
if ! grep -q 'sre.synthetic' "$OUTPUT_FILE"; then
  cat "$OUTPUT_FILE" >&2
  echo "service.name was not found in Collector output" >&2
  exit 1
fi
if ! grep -q 'otlp-http-to-debug-exporter' "$OUTPUT_FILE"; then
  cat "$OUTPUT_FILE" >&2
  echo "test invariant attribute was not found in Collector output" >&2
  exit 1
fi

if docker logs "$CONTAINER_NAME" 2>&1 | grep -Eiq 'error.*(failed|invalid|panic)|panic:'; then
  docker logs "$CONTAINER_NAME" >&2
  echo "Collector output contained a fatal or invalid configuration signal" >&2
  exit 1
fi

log "PASS: real Collector received, processed, batched, and exported the synthetic trace"
