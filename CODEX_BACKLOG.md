# P0 — Required for Portfolio Claim

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
