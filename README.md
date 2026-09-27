# Secure MCP Infrastructure Gateway

A local-first, zero-trust gateway for Model Context Protocol (MCP) tools. It makes
an MCP server an **integration endpoint**, not an automatic authorization boundary.

The gateway lets a human or a delegated agent discover and invoke only the tools it
is allowed to use. It does not give an agent direct infrastructure credentials,
unfiltered tool discovery, approval authority, or permission to change an approved
action after the fact.

## What runs locally

```text
delegated human / agent JWT
        |
        v
FastAPI gateway -> OPA parameter policy -> persisted plan / independent approval
        |                                      |
        +-> filtered tools/list                +-> hash-linked audit + metrics
        |
        v
two real Streamable HTTP MCP fixture servers (official Python MCP SDK)
```

The primary local path uses the current project-pinned MCP Python SDK (`>=2,<3`),
OPA 1.21.0, FastAPI, SQLite, and two independently running MCP fixture servers.
No cloud account or commercial MCP service is required.

## Guardrails demonstrated

| Control | Local evidence |
| --- | --- |
| Signed identity | Ed25519 JWT/JWKS signature, issuer, audience, expiry, tenant/team, roles and scopes are verified for human, delegated-agent and client principals. |
| Delegated agents | An agent JWT must name its human delegator; local delegations are capped at 60 seconds. |
| Filtered discovery | A read-only agent cannot see `scale_service` in `tools/list`. |
| Parameter policy | OPA denies cross-team reads and constrains writes by environment and replica count. |
| Protected write | Production scale needs a persisted exact action hash and an independent human approver. |
| Replay/stale protection | Changed parameters and consumed approval replays return `409` before upstream invocation. |
| Response security | A synthetic `API_KEY` returned by a fixture is redacted before the client receives it. |
| Schema drift | A changed tool input schema is quarantined and hidden before it can be called. |
| Emergency stop | A human `gateway_admin` can stop governed writes; calls then return `503`. |
| Audit/metrics | SQLite audit events are hash-linked and verifiable; `/metrics` exposes persisted audit counters. |

## Quick start

Prerequisites: Docker Desktop and Python 3.12+.

```bash
make install
make bootstrap-local
make smoke
make demo-mcp
make demo-security
make verify
make clean-local
```

`make bootstrap-local` creates only project-scoped resources: the Compose OPA
container/network plus three project-local processes (gateway and two MCP fixtures)
recorded in `.local/`. It fails clearly if a required port is already occupied.
`make clean-local` stops only those processes and `secure-mcp-infrastructure-gateway`
Compose resources; it does not prune Docker globally or modify unrelated projects.

When the stack is running, open `http://localhost:18090/` for the local operator
dashboard. It auto-refreshes safe aggregate audit counts and control state; it never
renders bearer tokens, raw tool arguments, or unredacted upstream responses.

## Main scenarios

### Delegated read

A developer delegates a short-lived `infra.read` capability to an agent. The agent
can discover and call `get_service_status` for its own team. It cannot discover the
protected write tool.

### Approval-bound production write

A developer asks to scale a production service. OPA returns
`APPROVAL_REQUIRED`; the gateway persists a plan containing requester, team, tool,
arguments and SHA-256 action hash. A distinct human with the `approver` role approves
that exact plan. The approved call reaches the live MCP infrastructure fixture once.
Changing replicas or replaying the consumed approval is rejected.

### Security failures

The security demo proves a secret response is redacted, a cross-team read is denied
by live OPA, and the write kill switch blocks a permitted development write. The test
suite also starts a fixture with a changed `scale_service` schema and verifies that
the gateway quarantines it before an upstream call.

## Evidence boundaries

See [implementation status](docs/IMPLEMENTATION_STATUS.md) and
[validation evidence](docs/VALIDATION.md). This project does **not** claim execution
of enterprise identity federation, Vault/SPIFFE, production PKI, external MCP
providers, managed OPA, or multi-region HA. Those are production adapters/roadmap,
not local validation claims.

## Portfolio relationship

This is the portfolio's governed agent-tool boundary. It can conceptually expose
safe, approval-gated operations from the infrastructure control plane, model release
plane, remediation platform, and edge fleet controller—while remaining independently
runnable with local fixtures.
