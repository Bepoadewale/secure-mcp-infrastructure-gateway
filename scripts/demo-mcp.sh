#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
"${ROOT}/scripts/smoke.sh"
agent="$(token agent)"
developer="$(token developer)"
approver="$(token approver)"
base="http://127.0.0.1:${GATEWAY_PORT}"

read_response="$(curl -fsS --max-time 10 -X POST "${base}/api/v1/tools/infra/get_service_status" \
  -H "Authorization: Bearer ${agent}" -H 'Content-Type: application/json' \
  -d '{"arguments":{"team":"payments","service":"api"}}')"
echo "delegated agent read: ${read_response}"

plan_response="$(curl -fsS --max-time 10 -X POST "${base}/api/v1/tools/infra/scale_service" \
  -H "Authorization: Bearer ${developer}" -H 'Content-Type: application/json' \
  -d '{"arguments":{"team":"payments","service":"api","replicas":3,"environment":"production"}}')"
plan_id="$("${PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)["plan_id"])' <<<"${plan_response}")"
echo "protected write plan: ${plan_response}"
approval="$(curl -fsS --max-time 10 -X POST "${base}/api/v1/plans/${plan_id}/approve" -H "Authorization: Bearer ${approver}")"
echo "independent approval: ${approval}"
executed="$(curl -fsS --max-time 10 -X POST "${base}/api/v1/tools/infra/scale_service" \
  -H "Authorization: Bearer ${developer}" -H 'Content-Type: application/json' \
  -d "{\"arguments\":{\"team\":\"payments\",\"service\":\"api\",\"replicas\":3,\"environment\":\"production\"},\"approval_id\":\"${plan_id}\"}")"
echo "approved upstream MCP write: ${executed}"
replay_status="$(curl -sS --max-time 10 -o "${STATE_DIR}/replay.json" -w '%{http_code}' -X POST "${base}/api/v1/tools/infra/scale_service" \
  -H "Authorization: Bearer ${developer}" -H 'Content-Type: application/json' \
  -d "{\"arguments\":{\"team\":\"payments\",\"service\":\"api\",\"replicas\":3,\"environment\":\"production\"},\"approval_id\":\"${plan_id}\"}")"
if [[ "${replay_status}" != "409" ]]; then
  echo "Demo failed: consumed approval replay returned ${replay_status}, expected 409." >&2
  exit 1
fi
echo "approval replay: rejected with HTTP 409"
