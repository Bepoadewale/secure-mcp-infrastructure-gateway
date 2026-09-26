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
