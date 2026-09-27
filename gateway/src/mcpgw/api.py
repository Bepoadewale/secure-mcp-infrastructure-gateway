"""Gateway API that invokes real upstream MCP servers under signed identity."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from mcpgw.auth import Identity, JwtVerifier, LocalJwtAuthority
from mcpgw.live import MCPTransportGateway, UpstreamServer
from mcpgw.policy import OpaPolicyEngine, PolicyEngine
from mcpgw.store import GatewayStore, action_hash
from pydantic import BaseModel


class ToolCall(BaseModel):
    arguments: dict[str, Any]
    approval_id: str | None = None


def create_app(
    transport: MCPTransportGateway | None = None,
    authority: LocalJwtAuthority | None = None,
    verifier: JwtVerifier | None = None,
    policy: PolicyEngine | None = None,
    store: GatewayStore | None = None,
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
    store = store or GatewayStore(os.environ.get("MCP_GATEWAY_DB", ".local/gateway.db"))
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
        store.audit("TOOLS_DISCOVERED", caller.subject, caller.team, metadata={"count": len(allowed)})
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
        approval_valid = False
        if decision.approval_required:
            if not request.approval_id:
                plan = store.create_plan(caller.subject, caller.team, server, tool_name, request.arguments)
                store.audit(
                    "APPROVAL_REQUIRED",
                    caller.subject,
                    caller.team,
                    plan.action_hash,
                    {"plan_id": plan.id, "server": server, "tool": tool_name},
                )
                return JSONResponse(
                    status_code=202,
                    content={"status": "APPROVAL_REQUIRED", "plan_id": plan.id, "reason": decision.reason},
                )
            try:
                approval_current = store.approval_is_current(
                    request.approval_id,
                    caller.subject,
                    caller.team,
                    server,
                    tool_name,
                    request.arguments,
                )
            except KeyError as exc:
                raise HTTPException(status_code=404, detail="approval plan was not found") from exc
            if not approval_current:
                store.audit(
                    "STALE_OR_UNAPPROVED_ACTION",
                    caller.subject,
                    caller.team,
                    action_hash(caller.subject, caller.team, server, tool_name, request.arguments),
                    {"plan_id": request.approval_id, "server": server, "tool": tool_name},
                )
                raise HTTPException(status_code=409, detail="stale or unapproved protected action")
            approval_valid = True
        if not decision.allow and not approval_valid:
            store.audit(
                "TOOL_CALL_DENIED",
                caller.subject,
                caller.team,
                metadata={"server": server, "tool": tool_name, "reason": decision.reason},
            )
            raise HTTPException(status_code=403, detail=decision.reason)
        try:
            response = asyncio.run(transport.call_tool(server, tool_name, request.arguments))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # Transport errors are deliberately not hidden as success.
            store.audit(
                "UPSTREAM_MCP_FAILURE",
                caller.subject,
                caller.team,
                metadata={"server": server, "tool": tool_name},
            )
            raise HTTPException(status_code=502, detail=f"upstream MCP failure: {exc}") from exc
        store.audit(
            "TOOL_CALLED",
            caller.subject,
            caller.team,
            action_hash(caller.subject, caller.team, server, tool_name, request.arguments),
            {"server": server, "tool": tool_name},
        )
        return {"server": server, "tool": tool_name, "response": response}

    @app.post("/api/v1/plans/{plan_id}/approve")
    def approve_plan(plan_id: str, caller: Identity = Depends(identity)) -> dict[str, str]:  # noqa: B008
        if caller.principal_type != "human" or "approver" not in caller.roles:
            raise HTTPException(status_code=403, detail="independent human approver role is required")
        try:
            plan = store.get_plan(plan_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="plan was not found") from exc
        if plan.team != caller.team:
            raise HTTPException(status_code=403, detail="cross-team approval is denied")
        try:
            approved = store.approve(plan_id, caller.subject)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        store.audit(
            "PLAN_APPROVED",
            caller.subject,
            caller.team,
            approved.action_hash,
            {"plan_id": approved.id, "requester": approved.requester},
        )
        return {"plan_id": approved.id, "status": approved.status}

    @app.get("/api/v1/audit")
    def audit(caller: Identity = Depends(identity)) -> dict[str, list[dict[str, Any]]]:  # noqa: B008
        if "audit.read" not in caller.scopes:
            raise HTTPException(status_code=403, detail="audit.read scope is required")
        return {"events": store.audit_events()}

    return app


app = create_app()
