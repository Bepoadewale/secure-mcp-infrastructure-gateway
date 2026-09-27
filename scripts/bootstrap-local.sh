#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
require_python
mkdir -p "${STATE_DIR}"

for spec in "${INFRA_PORT}:infra" "${UTILITY_PORT}:utility" "${GATEWAY_PORT}:gateway"; do
  port="${spec%%:*}"
  name="${spec##*:}"
  pid_file="${STATE_DIR}/${name}.pid"
  if [[ ! -f "${pid_file}" ]] || ! kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    ensure_port_available "${port}" "${name}"
  fi
done

docker compose -f "${ROOT}/docker-compose.yml" up -d opa
wait_for_url "http://127.0.0.1:18181/health" "OPA"

start_process infra env MCP_FIXTURE_PORT="${INFRA_PORT}" "${PYTHON}" "${ROOT}/fixtures/infra_server.py"
start_process utility env MCP_FIXTURE_PORT="${UTILITY_PORT}" "${PYTHON}" "${ROOT}/fixtures/utility_server.py"
wait_for_tcp "${INFRA_PORT}" "infrastructure MCP fixture"
wait_for_tcp "${UTILITY_PORT}" "utility MCP fixture"

start_process gateway env \
  MCP_GATEWAY_STATE_DIR="${STATE_DIR}" \
  MCP_GATEWAY_DB="${STATE_DIR}/gateway.db" \
  MCP_GATEWAY_PORT="${GATEWAY_PORT}" \
  MCP_INFRA_URL="http://127.0.0.1:${INFRA_PORT}/mcp" \
  MCP_UTILITY_URL="http://127.0.0.1:${UTILITY_PORT}/mcp" \
  OPA_URL="http://127.0.0.1:18181" \
  "${PYTHON}" -m mcpgw.local_server
wait_for_url "http://127.0.0.1:${GATEWAY_PORT}/healthz" "gateway"
echo "Local gateway ready at http://127.0.0.1:${GATEWAY_PORT}"
