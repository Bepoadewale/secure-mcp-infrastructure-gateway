# Definition of Done

# Portfolio Complete — Local-First Scope Gate

- [x] Current supported MCP SDK/spec runs at least two local fixture servers with actual `tools/list` and `tools/call` traffic through the gateway.
- [x] Signed JWT/JWKS validates human, delegated-agent and client identities; unsigned, wrong-key, expired, wrong issuer/audience, and undelegated agent identities are rejected.
- [x] Unauthorized tools are filtered from discovery where policy requires, not only denied on call.
- [x] Live OPA enforces tool and parameter-level policy.
- [x] Protected write binds exact action hash to approval; mutation/stale action, replay, and self-approval are denied.
- [x] Short-lived local agent delegation is signed, capped at 60 seconds, requires a human delegator, and expiry is tested.
- [x] Response security redacts a synthetic secret before return.
- [x] Schema drift quarantines changed tools; kill switch blocks governed writes.
- [x] Persistent tamper-evident/hash-linked SQLite audit operates and detects modification.
- [x] Unauthorized tool/parameter, expired delegation, schema rug pull, secret response, kill switch, and replay/failure scenarios are executed.
- [x] Reproducible core demo, meaningful tests, current-spec record, and green local validation exist; docs label unexecuted enterprise adapters.

## Maturity Levels

- **FOUNDATION:** policy/domain logic exists.
- **PARTIALLY VALIDATED:** live MCP integration exists but central governance story is incomplete.
- **LOCAL END-TO-END VALIDATED:** success path runs locally with material security/recovery/audit gaps.
- **PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE:** every checked gate has executed evidence.

# Clean-Room Reproducibility Gate

`PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE` requires two executed clean-room cycles: clone → install → bootstrap gateway, identity/policy fixtures, two MCP servers → smoke → filtered discovery/governed call/approval/delegation demo → schema or policy failure/audit demo → validation → project-scoped cleanup → second clean bootstrap/demo. Planned commands: `make install`, `make bootstrap-local`, `make smoke`, `make demo-mcp`, `make demo-security`, `make verify`, `make clean-local`.

- [x] Clean project bootstrap has no hidden project state; primary and failure demos passed twice.
- [x] Cleanup removes only this project’s `.local` processes and its Compose OPA/network; it has no global Docker/Kubernetes prune operation.
- [x] Post-cleanup absence and second bootstrap/demo are recorded in `docs/VALIDATION.md`.
