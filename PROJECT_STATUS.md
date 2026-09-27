# Project Status

## Current Maturity

PARTIALLY VALIDATED

## Maturity Model

`FOUNDATION` → `PARTIALLY VALIDATED` → `LOCAL END-TO-END VALIDATED` → `PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE`.

## Executed and Verified

- Delegation bounds, filtered registry, approval hashing, schema-drift quarantine and redaction core tests.
- Official MCP Python SDK `2.2.0` Streamable HTTP traffic to the local infrastructure fixture: real `tools/list` and `tools/call` executed.
- Gateway FastAPI route → official MCP client → two independent local MCP fixtures executed. Discovery filters the protected write tool and an allowed read call reaches the upstream fixture.
- Ed25519 JWT/JWKS verification executed for human and agent identities; unsigned, wrong-key, expired, wrong-issuer, and wrong-audience tokens were rejected.
- Live OPA `1.21.0` evaluated structured MCP identity, tool, and parameter input through its REST API. Protected policy transport failures fail closed.
- Protected production write flow executed through the gateway using an exact persisted action hash: plan → independent human approval → upstream MCP call. A modified action was rejected as stale; audit events persisted in SQLite.

## Implemented but Not End-to-End Validated

- Delegation, schema-drift enforcement, response redaction, kill switch, and OPA-backed approval integration remain outside the live path.

## Simulated

- Audit storage, approval and downstream execution.

## Architecture / Contracts Only

- Credential exchange and schema-drift/kill-switch persistence.

## Known Failures

- None known from the current local validation suite.

## Current P0 Objective

Add bounded downstream delegation plus live response redaction, schema quarantine, and kill-switch enforcement.

## Completion Blockers

- Delegation, schema-drift enforcement, response redaction, kill switch, and replay/failure evidence remain unexecuted.
- Filtered discovery, parameter denials, schema quarantine, response redaction, kill switch, and replay/failure evidence are unexecuted.

## Explicitly Unexecuted Production Adapters

- Enterprise OAuth federation, SPIFFE/Vault, production PKI, and managed authorization systems.

## Last Validation

- `.venv/bin/python -m pytest -q`: 8 passed, including signed JWT/JWKS negative cases and two-fixture gateway interception.
- `.venv/bin/python -m ruff check gateway/src fixtures tests`: passed.

## Last Updated

2026-09-26, Week 9 gateway transport interception increment (uncommitted).

## Clean-Room Reproducibility

**Status: NOT YET VALIDATED**

Completion requires two executed clean-room cycles: clean start → bootstrap → smoke → primary demo
→ failure/security demo → validation → project-scoped cleanup, followed by a second clean bootstrap
and demo. Existing developer state is not evidence. This status must be `VALIDATED` before
`PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE` is allowed.
