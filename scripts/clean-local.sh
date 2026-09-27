#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"

if [[ -d "${STATE_DIR}" ]]; then
  for name in gateway infra utility; do
    pid_file="${STATE_DIR}/${name}.pid"
    if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
      kill "$(cat "${pid_file}")"
    fi
  done
  rm -rf "${STATE_DIR}"
fi
docker compose -f "${ROOT}/docker-compose.yml" down --volumes --remove-orphans
echo "teardown complete: only secure-mcp-infrastructure-gateway project resources were removed"
