# Definition of Done

# Portfolio Complete — Local-First Scope Gate

- [ ] Current supported MCP SDK/spec runs at least two local fixture servers with actual `tools/list` and `tools/call` traffic through the gateway.
- [ ] Signed JWT/JWKS or equivalent validates human, agent, client, and relevant downstream identities.
- [ ] Unauthorized tools are filtered from discovery where policy requires, not only denied on call.
- [ ] Live OPA or equivalent enforces tool and parameter-level policy.
- [ ] Protected write binds exact action hash to approval; mutation/stale action and self-approval are denied.
- [ ] Short-lived downstream delegation cannot amplify privilege and expiration is executed.
- [ ] Response security redacts secrets and contains relevant injection behavior.
- [ ] Schema drift quarantines changed tools; kill switch blocks governed writes.
- [ ] Persistent tamper-evident/hash-linked audit operates where claimed.
- [ ] Unauthorized tool/parameter, expired delegation, schema rug pull, secret response, kill switch, and replay/failure scenarios are executed.
- [ ] Reproducible core demo, meaningful tests, current-spec record, and green CI exist; docs label unexecuted enterprise adapters.

## Maturity Levels

- **FOUNDATION:** policy/domain logic exists.
- **PARTIALLY VALIDATED:** live MCP integration exists but central governance story is incomplete.
- **LOCAL END-TO-END VALIDATED:** success path runs locally with material security/recovery/audit gaps.
- **PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE:** every checked gate has executed evidence.

# Clean-Room Reproducibility Gate

`PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE` requires two executed clean-room cycles: clone → install → bootstrap gateway, identity/policy fixtures, two MCP servers → smoke → filtered discovery/governed call/approval/delegation demo → schema or policy failure/audit demo → validation → project-scoped cleanup → second clean bootstrap/demo. Planned commands: `make install`, `make bootstrap-local`, `make smoke`, `make demo-mcp`, `make demo-security`, `make verify`, `make clean-local`.

- [ ] Clean clone/bootstrap has no hidden state; primary and failure demos pass.
- [ ] Cleanup removes only this project and unrelated resources survive.
- [ ] Post-cleanup absence and second bootstrap/demo are recorded in `docs/VALIDATION.md`.
