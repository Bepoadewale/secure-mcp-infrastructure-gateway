"""Development gateway API that invokes real upstream MCP servers.

JWT/JWKS authentication and OPA policy replace the development headers in the
next security increment.  The headers are intentionally limited to local
fixture use and are never described as an authentication mechanism.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from mcpgw.live import MCPTransportGateway, UpstreamServer
from pydantic import BaseModel


class ToolCall(BaseModel):
    arguments: dict[str, Any]


def create_app(transport: MCPTransportGateway | None = None) -> FastAPI:
    transport = transport or MCPTransportGateway(
        [
            UpstreamServer("infra", os.environ.get("MCP_INFRA_URL", "http://127.0.0.1:19081/mcp")),
            UpstreamServer("utility", os.environ.get("MCP_UTILITY_URL", "http://127.0.0.1:19082/mcp")),
        ]
    )
    app = FastAPI(title="Secure MCP Infrastructure Gateway", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/tools")
    def tools(x_gateway_scopes: str = Header(default="")) -> dict[str, list[dict[str, Any]]]:
        # Development-only policy placeholder; replaced by signed identity + OPA.
        scopes = set(filter(None, x_gateway_scopes.split()))
        discovered = asyncio.run(transport.list_tools())
        allowed = [
            tool
            for tool in discovered
            if tool["name"] != "scale_service" or "infra.write" in scopes
        ]
        return {"tools": allowed}

    @app.post("/api/v1/tools/{server}/{tool_name}")
    def call_tool(
        server: str,
        tool_name: str,
        request: ToolCall,
        x_gateway_scopes: str = Header(default=""),
    ) -> dict[str, Any]:
        scopes = set(filter(None, x_gateway_scopes.split()))
        if tool_name == "scale_service" and "infra.write" not in scopes:
            raise HTTPException(status_code=403, detail="tool is not authorized")
        try:
            response = asyncio.run(transport.call_tool(server, tool_name, request.arguments))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # Transport errors are deliberately not hidden as success.
            raise HTTPException(status_code=502, detail=f"upstream MCP failure: {exc}") from exc
        return {"server": server, "tool": tool_name, "response": response}

    return app


app = create_app()
