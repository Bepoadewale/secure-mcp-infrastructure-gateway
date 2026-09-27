"""Local MCP fixture exposing a deliberately small infrastructure surface."""

from __future__ import annotations

import os

from mcp.server import MCPServer

server = MCPServer("local-infrastructure-fixture")


@server.tool(description="Read the health of a named service in a team namespace.")
def get_service_status(team: str, service: str) -> dict[str, str]:
    return {"team": team, "service": service, "status": "healthy"}


@server.tool(description="Scale a named service. This is a protected write in the gateway.")
def scale_service(team: str, service: str, replicas: int, environment: str) -> dict[str, object]:
    return {
        "team": team,
        "service": service,
        "replicas": replicas,
        "environment": environment,
        "result": "scaled-by-fixture",
    }


if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=int(os.environ.get("MCP_FIXTURE_PORT", "19081")),
    )
