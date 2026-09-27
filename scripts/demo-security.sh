#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib.sh"
"${ROOT}/scripts/smoke.sh"
developer="$(token developer)"
admin="$(token admin)"
base="http://127.0.0.1:${GATEWAY_PORT}"

redacted="$(curl -fsS --max-time 10 -X POST "${base}/api/v1/tools/utility/get_synthetic_secret_demo" \
  -H "Authorization: Bearer ${developer}" -H 'Content-Type: application/json' -d '{"arguments":{}}')"
if [[ "${redacted}" == *demo-super-secret-value* ]] || [[ "${redacted}" != *'[REDACTED]'* ]]; then
  echo "Security demo failed: synthetic secret was not redacted." >&2
  exit 1
fi
echo "response redaction: ${redacted}"

cross_team_status="$(curl -sS --max-time 10 -o "${STATE_DIR}/cross-team.json" -w '%{http_code}' -X POST "${base}/api/v1/tools/infra/get_service_status" \
  -H "Authorization: Bearer ${developer}" -H 'Content-Type: application/json' \
  -d '{"arguments":{"team":"other-team","service":"api"}}')"
if [[ "${cross_team_status}" != "403" ]]; then
  echo "Security demo failed: cross-team call returned ${cross_team_status}, expected 403." >&2
  exit 1
fi
echo "OPA parameter policy: cross-team call denied with HTTP 403"

curl -fsS --max-time 10 -X POST "${base}/api/v1/admin/write-kill-switch" \
  -H "Authorization: Bearer ${admin}" -H 'Content-Type: application/json' -d '{"writes_disabled":true}' >/dev/null
status="$(curl -sS --max-time 10 -o "${STATE_DIR}/kill-switch.json" -w '%{http_code}' -X POST "${base}/api/v1/tools/infra/scale_service" \
  -H "Authorization: Bearer ${developer}" -H 'Content-Type: application/json' \
  -d '{"arguments":{"team":"payments","service":"api","replicas":2,"environment":"dev"}}')"
curl -fsS --max-time 10 -X POST "${base}/api/v1/admin/write-kill-switch" \
  -H "Authorization: Bearer ${admin}" -H 'Content-Type: application/json' -d '{"writes_disabled":false}' >/dev/null
if [[ "${status}" != "503" ]]; then
  echo "Security demo failed: kill switch returned ${status}, expected 503." >&2
  exit 1
fi
echo "write kill switch: blocked governed write with HTTP 503"
audit="$(curl -fsS --max-time 10 -H "Authorization: Bearer ${developer}" "${base}/api/v1/audit/verify")"
if [[ "${audit}" != *'"valid":true'* ]]; then
  echo "Security demo failed: hash-linked audit chain did not verify." >&2
  exit 1
fi
echo "hash-linked audit: verified"
