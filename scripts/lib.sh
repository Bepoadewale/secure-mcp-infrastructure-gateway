#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${ROOT}/.local"
PYTHON="${ROOT}/.venv/bin/python"
GATEWAY_PORT="${MCP_GATEWAY_PORT:-18090}"
INFRA_PORT="${MCP_INFRA_PORT:-19081}"
UTILITY_PORT="${MCP_UTILITY_PORT:-19082}"

require_python() {
  if [[ ! -x "${PYTHON}" ]]; then
    echo "Missing .venv. Run 'make install' first." >&2
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local deadline=$((SECONDS + 30))
  until curl -fsS --max-time 2 "${url}" >/dev/null 2>&1; do
    if (( SECONDS >= deadline )); then
      echo "${name} did not become ready: ${url}" >&2
      exit 1
    fi
    sleep 1
  done
}

wait_for_tcp() {
  local port="$1"
  local name="$2"
  local deadline=$((SECONDS + 30))
  until "${PYTHON}" -c 'import socket,sys; s=socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=1); s.close()' "${port}" 2>/dev/null; do
    if (( SECONDS >= deadline )); then
      echo "${name} did not open TCP port ${port}" >&2
      exit 1
    fi
    sleep 1
  done
}

start_process() {
  local name="$1"
  shift
  local pid_file="${STATE_DIR}/${name}.pid"
  if [[ -f "${pid_file}" ]] && kill -0 "$(cat "${pid_file}")" 2>/dev/null; then
    return
  fi
  "$@" >"${STATE_DIR}/${name}.log" 2>&1 &
  echo $! >"${pid_file}"
}

ensure_port_available() {
  local port="$1"
  local name="$2"
  if "${PYTHON}" -c 'import socket,sys; s=socket.socket(); s.bind(("127.0.0.1", int(sys.argv[1]))); s.close()' "${port}" 2>/dev/null; then
    return
  fi
  echo "${name} port ${port} is already occupied. Run 'make clean-local' or choose a different project port." >&2
  exit 1
}

token() {
  "${PYTHON}" -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])' \
    "${STATE_DIR}/demo-tokens.json" "$1"
}
