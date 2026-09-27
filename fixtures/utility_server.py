"""Local MCP fixture for downstream response-redaction tests."""

from __future__ import annotations

import os

from mcp.server import MCPServer

server = MCPServer("local-utility-fixture")


@server.tool(description="Returns a synthetic secret so the gateway can prove redaction.")
def get_synthetic_secret_demo() -> str:
    return "API_KEY=demo-super-secret-value"


if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=int(os.environ.get("MCP_FIXTURE_PORT", "19082")),
    )
