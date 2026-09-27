# Completion Target

PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE

# Current Completion Blockers

None for the local-first completion gate. Future work must not weaken the executed evidence.

# P0 — Required for Portfolio Claim

P0 blocks PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE; do not select P1/P2 work first.

- [x] Verify current MCP SDK/spec and record supported version.
- [x] Build two local fixture servers; gateway actual `tools/list`/`tools/call`.
- [x] Add signed local JWT/JWKS for human and delegated-agent identities.
- [x] Enforce OPA tool/parameter policy and filtered discovery.
- [x] Demonstrate approval-bound write, short-lived delegation, schema drift denial and persistent audit.

# P1 — Production Hardening

- External identity federation, token exchange with downstream MCP providers, rate limiting, OpenTelemetry export, and PostgreSQL HA.

# P2 — Enhancements

- CLI and policy-administration workflow.

# P3 — Future / Cloud / Hardware

- OAuth federation, enterprise-managed authorization, SPIFFE/Vault.
# Clean-Room Completion Blocker

- [x] Pass the full clean-room reproducibility gate: deterministic bootstrap, smoke, governed MCP and security demos, safe cleanup, a second clean bootstrap, and recorded evidence.
