# Validation

Run `PYTHONPATH=gateway/src python3 -m pytest -q` and lint once configured. Live status requires versions, services, captured `tools/list` and `tools/call` interactions, signed-token validation, enforced policy denial, audit persistence, and failure evidence; mocked method names are insufficient. Never fabricate validation.

## Clean-Room Validation

Do not populate this section until executed. Record: date, commit SHA, OS/environment, Docker/kind/Kubernetes and key dependency versions where applicable; clean starting state; exact install/bootstrap/smoke/demo/failure/validation/cleanup commands; observed results; post-cleanup absence verification; and the second-bootstrap result. No prior local state or fabricated evidence is acceptable.
# Validation

## MCP fixture baseline

Date: 2026-09-26

Environment: Python 3.14, official MCP Python SDK `2.2.0`, local loopback
Streamable HTTP fixture.

Commands executed:

```bash
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check gateway/src fixtures tests
```

Observed results:

- The official SDK connected to `http://127.0.0.1:<ephemeral-port>/mcp`.
- `tools/list` returned `get_service_status` and `scale_service`.
- `tools/call` executed `get_service_status` and returned structured fixture data.
- Pytest: `5 passed`; Ruff: passed.

This is direct fixture traffic only. The gateway does not yet intercept this
traffic, and this evidence does not validate identity, OPA, approval,
delegation, audit, or clean-room reproducibility.

## Gateway transport interception

The gateway integration test starts both fixture servers on ephemeral loopback
ports, then executes:

```text
FastAPI gateway route → official MCP Client → Streamable HTTP fixture
```

The no-scope discovery response omitted `scale_service`; `infra.write`
discovery included it. A no-scope direct write returned HTTP `403`. A permitted
read invocation returned the structured upstream service-health response.

This uses development-only headers for temporary test scoping. It is not an
identity or policy validation and will be replaced by JWT/JWKS plus OPA.

## Signed identity validation

The gateway now requires an `Authorization: Bearer <JWT>` identity rather than
caller-provided scope headers. Synthetic local Ed25519 identities were used
only for validation. The test suite accepted valid human/agent tokens and
rejected unsigned, wrong-signing-key, expired, wrong-issuer, and
wrong-audience tokens. The gateway still needs live OPA policy, approval,
delegation, and audit before this is a complete governed path.

## Live OPA policy

Docker Compose started the pinned `openpolicyagent/opa:1.21.0` service. Its
`/v1/data/mcp/authz/decision` endpoint evaluated a signed-agent-equivalent
input for `get_service_status` in the caller's team and returned:

```json
{"allow": true, "approval_required": false, "reason": "read_allowed"}
```

The gateway policy client sends the same structured identity/tool/argument
shape and returns a deny decision if the OPA HTTP call fails or is malformed.

## Protected write approval and audit

The local gateway integration test created a production `scale_service` plan
for an agent, then exercised:

```text
agent request → APPROVAL_REQUIRED → independent human approval
→ exact approved action executes through MCP
```

The agent could not approve its own plan. Reusing the approved plan after
changing `replicas` returned HTTP `409` before any upstream call. SQLite audit
recorded `APPROVAL_REQUIRED`, `PLAN_APPROVED`,
`STALE_OR_UNAPPROVED_ACTION`, and `TOOL_CALLED` as a hash-linked sequence.
