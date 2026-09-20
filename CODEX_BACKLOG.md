# Completion Target

PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE

# Current Completion Blockers

- Execute two MCP fixture servers through JWT identity, filtered discovery, OPA parameter policy, approval, delegation, and audit.
- Demonstrate schema drift, secret response, kill switch, delegation expiry, and unauthorized/replay failures.

# P0 — Required for Portfolio Claim

P0 blocks PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE; do not select P1/P2 work first.

- Verify current MCP SDK/spec and record supported version.
- Build two local fixture servers; gateway actual `tools/list`/`tools/call`.
- Add signed local JWT/JWKS for distinct human, agent and client identities.
- Enforce OPA tool/parameter policy and filtered discovery.
- Demonstrate approval-bound write, short-lived downstream token, schema drift denial and persistent audit.

# P1 — Production Hardening

- SQLite/PostgreSQL audit chain, rate limits, kill switch, response scanner and OTel.

# P2 — Enhancements

- CLI and policy-administration workflow.

# P3 — Future / Cloud / Hardware

- OAuth federation, enterprise-managed authorization, SPIFFE/Vault.
# Clean-Room Completion Blocker

- [ ] Pass the full clean-room reproducibility gate: deterministic bootstrap, smoke, governed MCP and security demos, safe cleanup, a second clean bootstrap, and recorded evidence. Break this into focused P0 work only during the scheduled week.
