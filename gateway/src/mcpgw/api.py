"""Gateway API that invokes real upstream MCP servers under signed identity."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from mcpgw.auth import Identity, JwtVerifier, LocalJwtAuthority
from mcpgw.live import MCPTransportGateway, UpstreamServer
from pydantic import BaseModel


class ToolCall(BaseModel):
    arguments: dict[str, Any]


def create_app(
    transport: MCPTransportGateway | None = None,
    authority: LocalJwtAuthority | None = None,
    verifier: JwtVerifier | None = None,
) -> FastAPI:
    transport = transport or MCPTransportGateway(
        [
            UpstreamServer("infra", os.environ.get("MCP_INFRA_URL", "http://127.0.0.1:19081/mcp")),
            UpstreamServer("utility", os.environ.get("MCP_UTILITY_URL", "http://127.0.0.1:19082/mcp")),
        ]
    )
    authority = authority or LocalJwtAuthority.generate()
    verifier = verifier or JwtVerifier(authority.jwks())
    app = FastAPI(title="Secure MCP Infrastructure Gateway", version="0.1.0")

    def identity(authorization: str | None = Header(default=None)) -> Identity:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Bearer identity is required")
        try:
            return verifier.verify(authorization.removeprefix("Bearer "))
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/.well-known/jwks.json")
    def jwks() -> dict[str, list[dict[str, str]]]:
        return authority.jwks()

    @app.get("/api/v1/tools")
    def tools(caller: Identity = Depends(identity)) -> dict[str, list[dict[str, Any]]]:  # noqa: B008
        # OPA becomes the authority in the next increment; identity is already verified.
        discovered = asyncio.run(transport.list_tools())
        allowed = [
            tool
            for tool in discovered
            if tool["name"] != "scale_service" or "infra.write" in caller.scopes
        ]
        return {"tools": allowed}

    @app.post("/api/v1/tools/{server}/{tool_name}")
    def call_tool(
        server: str,
        tool_name: str,
        request: ToolCall,
        caller: Identity = Depends(identity),  # noqa: B008
    ) -> dict[str, Any]:
        if tool_name == "scale_service" and "infra.write" not in caller.scopes:
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
