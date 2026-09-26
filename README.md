# Secure MCP Infrastructure Gateway

A governed gateway core that treats MCP as an interoperability protocol, not an authorization boundary. It models human/agent delegation, filtered discovery, parameter-level authorization, exact approval binding, schema drift quarantine, response redaction and audit events.

The project has executed a real local transport path: FastAPI gateway route →
official MCP Python SDK `2.2.0` → two local Streamable HTTP fixture servers.
The gateway currently filters protected writes using development-only test
headers; signed JWT/JWKS validation, OPA enforcement, credential broker
execution, durable audit, and the remaining failure paths are still
unexecuted.
