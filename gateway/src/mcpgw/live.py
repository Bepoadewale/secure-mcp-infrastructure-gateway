"""Real MCP transport adapter used by the local gateway API.

This module deliberately keeps identity and OPA separate.  It owns only the
safe mechanics of discovering a bounded upstream catalogue and invoking a
named MCP tool through the official Python SDK.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from mcp import Client


@dataclass(frozen=True)
class UpstreamServer:
    name: str
    url: str


class MCPTransportGateway:
    """Read tool metadata and invoke tools through real Streamable HTTP MCP."""

    def __init__(self, servers: list[UpstreamServer]) -> None:
        self._servers = {server.name: server for server in servers}

    async def list_tools(self) -> list[dict[str, Any]]:
        catalogue: list[dict[str, Any]] = []
        for server in self._servers.values():
            async with Client(server.url) as client:
                result = await client.list_tools()
            catalogue.extend(
                {
                    "server": server.name,
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.input_schema,
                    "schema_digest": self.schema_digest(tool.input_schema),
                }
                for tool in result.tools
            )
        return sorted(catalogue, key=lambda tool: (tool["server"], tool["name"]))

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> Any:
        server = self._servers.get(server_name)
        if not server:
            raise KeyError(f"unknown upstream server: {server_name}")
        async with Client(server.url) as client:
            result = await client.call_tool(tool_name, arguments)
        if result.structured_content is not None:
            return result.structured_content
        return [content.model_dump(mode="json") for content in result.content]

    @staticmethod
    def schema_digest(schema: dict[str, Any]) -> str:
        canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()
