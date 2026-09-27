"""A changed upstream schema used only to prove gateway quarantine behavior."""

from __future__ import annotations

import os

from mcp.server import MCPServer

server = MCPServer("local-infrastructure-fixture-drift")


@server.tool(description="Changed schema fixture; gateway must quarantine it.")
def scale_service(team: str, service: str, replicas: int, environment: str, reason: str) -> dict[str, object]:
    return {"team": team, "service": service, "replicas": replicas, "environment": environment, "reason": reason}


if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=int(os.environ.get("MCP_FIXTURE_PORT", "19083")),
    )
