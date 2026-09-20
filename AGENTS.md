# Secure MCP Infrastructure Gateway — Agent Guide

Mission: be the zero-trust authorization boundary between agents and MCP tools. The agent, tool metadata and downstream response are untrusted.

Stack: Python 3.12 gateway core; future official MCP SDK, FastAPI, JWT/JWKS, OPA and SQLite/PostgreSQL.

Commands: `PYTHONPATH=gateway/src python3 -m pytest -q`; add lint/run targets only when configured.

Rules: protocol-agnostic tests do not validate MCP; fail closed on identity/policy/audit failure; do not audit secrets or issue broad credentials; no main pushes/secrets; update status/backlog after meaningful work.

Completion rule: do not mark **PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE** unless the gate in `DEFINITION_OF_DONE.md` has executed evidence. Protocol-agnostic methods, mocked policy, schemas, and documentation do not prove MCP governance. The real MCP discovery/call path must run locally through identity, policy, approval, delegation, response security, and audit; enterprise identity/PKI remains explicit.

## Clean-room reproducibility

Clean-room reproducibility is a mandatory completion criterion. Do not mark this repository
`PORTFOLIO COMPLETE — LOCAL-FIRST SCOPE` until a new engineer can reproduce the platform from a
clean project state using documented commands, execute the primary and required failure demos, run
validation, and safely tear down only this project's local resources. Do not infer reproducibility
from an existing developer environment; execute it after project-specific cleanup.
