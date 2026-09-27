"""Run the project-local gateway and publish synthetic demo tokens outside source control."""

from __future__ import annotations

import json
import os
from pathlib import Path

import uvicorn
from mcpgw.api import create_app
from mcpgw.auth import JwtVerifier, LocalJwtAuthority


def build_local_app() -> tuple[object, dict[str, str]]:
    state_dir = Path(os.environ.get("MCP_GATEWAY_STATE_DIR", ".local"))
    state_dir.mkdir(parents=True, exist_ok=True)
    authority = LocalJwtAuthority.load_or_create(str(state_dir / "local-ed25519.pem"))
    tokens = {
        "developer": authority.issue(
            subject="developer-1",
            principal_type="human",
            team="payments",
            roles=["developer"],
            scopes=["infra.read", "infra.write", "audit.read"],
        ),
        "approver": authority.issue(
            subject="approver-1",
            principal_type="human",
            team="payments",
            roles=["approver"],
            scopes=["infra.read", "infra.write", "audit.read"],
        ),
        "admin": authority.issue(
            subject="admin-1",
            principal_type="human",
            team="payments",
            roles=["gateway_admin"],
            scopes=["infra.read", "infra.write", "audit.read"],
        ),
        "agent": authority.issue_agent_delegation(
            human="developer-1", agent="agent-1", team="payments", scopes=["infra.read"]
        ),
    }
    tokens_path = state_dir / "demo-tokens.json"
    tokens_path.write_text(json.dumps(tokens), encoding="utf-8")
    os.chmod(tokens_path, 0o600)
    app = create_app(authority=authority, verifier=JwtVerifier(authority.jwks()))
    return app, tokens


def main() -> None:
    app, _ = build_local_app()
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("MCP_GATEWAY_PORT", "18090")))


if __name__ == "__main__":
    main()
