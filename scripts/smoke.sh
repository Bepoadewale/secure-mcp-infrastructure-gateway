#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_python
wait_for_url "http://127.0.0.1:18181/health" "OPA"
wait_for_url "http://127.0.0.1:${GATEWAY_PORT}/healthz" "gateway"
if ! curl -fsS --max-time 10 "http://127.0.0.1:${GATEWAY_PORT}/metrics" | grep -q 'mcp_gateway_write_kill_switch_enabled'; then
  echo "Smoke failed: gateway metrics endpoint is unavailable." >&2
  exit 1
fi
agent="$(token agent)"
client="$(token client)"
tools="$(curl -fsS --max-time 10 -H "Authorization: Bearer ${agent}" "http://127.0.0.1:${GATEWAY_PORT}/api/v1/tools")"
if [[ "${tools}" == *scale_service* ]]; then
  echo "Smoke failed: read-only agent discovered protected write." >&2
  exit 1
fi
if [[ "${tools}" != *get_service_status* ]]; then
  echo "Smoke failed: expected read tool absent." >&2
  exit 1
fi
if ! curl -fsS --max-time 10 -H "Authorization: Bearer ${client}" "http://127.0.0.1:${GATEWAY_PORT}/api/v1/tools" | grep -q 'get_service_status'; then
  echo "Smoke failed: signed client identity could not discover its allowed read tool." >&2
  exit 1
fi
echo "smoke passed: OPA, gateway, two MCP fixtures, and filtered discovery are ready"
