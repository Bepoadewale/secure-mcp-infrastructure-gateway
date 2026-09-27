# Validation

## Standard validation

```bash
make verify
```

This runs Ruff and the test suite. The suite includes real localhost Streamable HTTP
MCP fixture processes, FastAPI gateway routes, signed JWT verification, OPA policy
composition, persisted approvals, response redaction, schema quarantine, kill-switch
and audit-chain tests.

## Executed Clean-Room Evidence

- **Date:** 2026-09-27
- **Implementation commits:** `499f384` (`feat: complete governed MCP gateway local workflow`) and
  `4076d17` (signed client-identity smoke proof).
- **Environment:** macOS, Docker Desktop 29.0.1, Docker Compose v2.40.3-desktop.1,
  Python 3.14.0, MCP Python SDK 2.2.0, OPA 1.21.0.
- **Starting state:** `.local` absent; no project Compose services; no listeners on
  `18090` (gateway), `19081` (infra fixture), or `19082` (utility fixture).

### Cycle 1

```bash
make clean-local
make bootstrap-local
make smoke
make demo-mcp
make demo-security
make verify
```

Result: passed. Bootstrap created the project-scoped OPA Compose service/network,
two local MCP fixture processes, FastAPI gateway, local SQLite state and synthetic
Ed25519 demo signer. Smoke proved OPA/gateway readiness and filtered discovery.
The primary demo executed a delegated agent read, approval-required production write,
independent approval, live upstream MCP write and replay rejection (`409`). The security
demo redacted the synthetic secret, denied a cross-team request through OPA (`403`),
blocked a governed write through the kill switch (`503`), and verified the audit hash
chain. `make verify` passed: Ruff clean and `14 passed`.

### Teardown and Cycle 2

```bash
make clean-local
test ! -e .local
docker compose ps
make bootstrap-local
make smoke
make demo-mcp
make demo-security
make verify
```

Result: post-cleanup verification confirmed no project local state, Compose services,
or listeners on the three project ports. Cycle 2 passed the same smoke, primary and
security scenarios and again reported Ruff clean with `14 passed`.

### Final cleanup

```bash
make clean-local
```

Result: `.local` absent, no project Compose service, and no project listener on ports
`18090`, `19081` or `19082`. `clean-local` only targets PID files/state under this
repository plus this repository’s Compose project; it does not use global Docker prune
or broad host cleanup.
