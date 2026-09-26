# Secure MCP Infrastructure Gateway

A governed gateway core that treats MCP as an interoperability protocol, not an authorization boundary. It models human/agent delegation, filtered discovery, parameter-level authorization, exact approval binding, schema drift quarantine, response redaction and audit events.

The project has executed official MCP Python SDK `2.2.0` `tools/list` and
`tools/call` traffic against one local Streamable HTTP fixture. The gateway has
not yet governed that traffic; signed JWT/JWKS validation, OPA enforcement,
credential broker execution, durable audit, and a second fixture remain
unexecuted.
