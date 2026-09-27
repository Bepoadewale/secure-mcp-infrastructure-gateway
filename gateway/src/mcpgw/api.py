"""Gateway API that invokes real upstream MCP servers under signed identity."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from mcpgw.auth import Identity, JwtVerifier, LocalJwtAuthority
from mcpgw.live import MCPTransportGateway, UpstreamServer
from mcpgw.policy import OpaPolicyEngine, PolicyEngine
from pydantic import BaseModel


class ToolCall(BaseModel):
    arguments: dict[str, Any]


def create_app(
    transport: MCPTransportGateway | None = None,
    authority: LocalJwtAuthority | None = None,
    verifier: JwtVerifier | None = None,
    policy: PolicyEngine | None = None,
) -> FastAPI:
    transport = transport or MCPTransportGateway(
        [
            UpstreamServer("infra", os.environ.get("MCP_INFRA_URL", "http://127.0.0.1:19081/mcp")),
            UpstreamServer("utility", os.environ.get("MCP_UTILITY_URL", "http://127.0.0.1:19082/mcp")),
        ]
    )
    authority = authority or LocalJwtAuthority.generate()
    verifier = verifier or JwtVerifier(authority.jwks())
    policy = policy or OpaPolicyEngine(os.environ.get("OPA_URL", "http://127.0.0.1:18181"))
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
        discovered = asyncio.run(transport.list_tools())
        allowed = [
            tool
            for tool in discovered
            if policy.decide(caller, "discover", tool, {}).allow
        ]
        return {"tools": allowed}

    @app.post("/api/v1/tools/{server}/{tool_name}")
    def call_tool(
        server: str,
        tool_name: str,
        request: ToolCall,
        caller: Identity = Depends(identity),  # noqa: B008
    ) -> dict[str, Any]:
        tool = {"server": server, "name": tool_name}
        decision = policy.decide(caller, "call", tool, request.arguments)
        if decision.approval_required:
            raise HTTPException(status_code=202, detail=decision.reason)
        if not decision.allow:
            raise HTTPException(status_code=403, detail=decision.reason)
        try:
            response = asyncio.run(transport.call_tool(server, tool_name, request.arguments))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # Transport errors are deliberately not hidden as success.
            raise HTTPException(status_code=502, detail=f"upstream MCP failure: {exc}") from exc
        return {"server": server, "tool": tool_name, "response": response}

    return app


app = create_app()
