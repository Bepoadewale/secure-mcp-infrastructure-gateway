# Secure MCP Infrastructure Gateway — Agent Guide

Mission: be the zero-trust authorization boundary between agents and MCP tools. The agent, tool metadata and downstream response are untrusted.

Stack: Python 3.12 gateway core; future official MCP SDK, FastAPI, JWT/JWKS, OPA and SQLite/PostgreSQL.

Commands: `PYTHONPATH=gateway/src python3 -m pytest -q`; add lint/run targets only when configured.

Rules: protocol-agnostic tests do not validate MCP; fail closed on identity/policy/audit failure; do not audit secrets or issue broad credentials; no main pushes/secrets; update status/backlog after meaningful work.
