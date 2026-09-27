"""Local integration proof: gateway API → official MCP client → fixture server."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi.testclient import TestClient
from mcpgw.api import create_app
from mcpgw.auth import JwtVerifier, LocalJwtAuthority
from mcpgw.live import MCPTransportGateway, UpstreamServer
from mcpgw.policy import PolicyDecision
from mcpgw.store import GatewayStore

ROOT = Path(__file__).resolve().parents[1]


class FixturePolicy:
    def decide(self, identity, action, tool, _arguments):
        if (
            action == "discover"
            and tool["name"] == "scale_service"
            and "infra.write" not in identity.scopes
        ):
            return PolicyDecision(False, False, "write_scope_required")
        if action == "call" and tool["name"] == "scale_service":
            return PolicyDecision(False, False, "write_denied_for_test")
        return PolicyDecision(True, False, "fixture_policy_allowed")


class ProtectedWritePolicy:
    def decide(self, _identity, action, tool, arguments):
        if action == "call" and tool["name"] == "scale_service" and arguments["environment"] == "production":
            return PolicyDecision(False, True, "protected_write_requires_approval")
        return PolicyDecision(True, False, "fixture_policy_allowed")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(port: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise AssertionError("fixture MCP server did not become reachable")


@contextmanager
def _fixtures(infra_script: str = "infra_server.py") -> Iterator[MCPTransportGateway]:
    infra_port, utility_port = _free_port(), _free_port()
    processes = [
        subprocess.Popen(
            [sys.executable, str(ROOT / "fixtures" / script)],
            cwd=ROOT,
            env={**os.environ, "MCP_FIXTURE_PORT": str(port)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for script, port in ((infra_script, infra_port), ("utility_server.py", utility_port))
    ]
    try:
        _wait_for_port(infra_port)
        _wait_for_port(utility_port)
        yield MCPTransportGateway(
            [
                UpstreamServer("infra", f"http://127.0.0.1:{infra_port}/mcp"),
                UpstreamServer("utility", f"http://127.0.0.1:{utility_port}/mcp"),
            ]
        )
    finally:
        for process in processes:
            process.terminate()
        for process in processes:
            process.wait(timeout=5)


def test_gateway_filters_discovery_and_invokes_real_upstream_mcp_tool() -> None:
    with _fixtures() as transport:
        authority = LocalJwtAuthority.generate()
        client = TestClient(
            create_app(transport, authority, JwtVerifier(authority.jwks()), FixturePolicy())
        )
        read_token = authority.issue_agent_delegation(
            human="alice",
            agent="agent-1",
            team="payments",
            scopes=["infra.read"],
        )
        write_token = authority.issue(
            subject="developer-1",
            principal_type="human",
            team="payments",
            roles=["developer"],
            scopes=["infra.read", "infra.write"],
        )
        read_only = client.get("/api/v1/tools", headers={"Authorization": f"Bearer {read_token}"})
        assert read_only.status_code == 200
        assert {tool["name"] for tool in read_only.json()["tools"]} == {
            "get_service_status",
            "get_synthetic_secret_demo",
        }

        writable = client.get("/api/v1/tools", headers={"Authorization": f"Bearer {write_token}"})
        assert {tool["name"] for tool in writable.json()["tools"]} == {
            "get_service_status",
            "get_synthetic_secret_demo",
            "scale_service",
        }

        denied = client.post(
            "/api/v1/tools/infra/scale_service",
            json={"arguments": {"team": "payments", "service": "api", "replicas": 2, "environment": "dev"}},
            headers={"Authorization": f"Bearer {read_token}"},
        )
        assert denied.status_code == 403

        called = client.post(
            "/api/v1/tools/infra/get_service_status",
            json={"arguments": {"team": "payments", "service": "api"}},
            headers={"Authorization": f"Bearer {read_token}"},
        )
        assert called.status_code == 200
        assert called.json()["response"] == {"team": "payments", "service": "api", "status": "healthy"}


def test_protected_write_requires_independent_exact_approval_and_audits() -> None:
    with _fixtures() as transport:
        authority = LocalJwtAuthority.generate()
        store = GatewayStore()
        client = TestClient(
            create_app(
                transport,
                authority,
                JwtVerifier(authority.jwks()),
                ProtectedWritePolicy(),
                store,
            )
        )
        requester = authority.issue_agent_delegation(
            human="alice",
            agent="agent-1",
            team="payments",
            scopes=["infra.write"],
        )
        approver = authority.issue(
            subject="bob",
            principal_type="human",
            team="payments",
            roles=["approver"],
            scopes=["infra.write", "audit.read"],
        )
        args = {"team": "payments", "service": "api", "replicas": 3, "environment": "production"}
        planned = client.post(
            "/api/v1/tools/infra/scale_service",
            json={"arguments": args},
            headers={"Authorization": f"Bearer {requester}"},
        )
        assert planned.status_code == 202
        plan_id = planned.json()["plan_id"]
        assert client.post(
            f"/api/v1/plans/{plan_id}/approve", headers={"Authorization": f"Bearer {requester}"}
        ).status_code == 403
        assert client.post(
            f"/api/v1/plans/{plan_id}/approve", headers={"Authorization": f"Bearer {approver}"}
        ).status_code == 200
        stale = client.post(
            "/api/v1/tools/infra/scale_service",
            json={"arguments": {**args, "replicas": 4}, "approval_id": plan_id},
            headers={"Authorization": f"Bearer {requester}"},
        )
        assert stale.status_code == 409
        executed = client.post(
            "/api/v1/tools/infra/scale_service",
            json={"arguments": args, "approval_id": plan_id},
            headers={"Authorization": f"Bearer {requester}"},
        )
        assert executed.status_code == 200
        assert [event["event_type"] for event in store.audit_events()] == [
            "APPROVAL_REQUIRED",
            "PLAN_APPROVED",
            "STALE_OR_UNAPPROVED_ACTION",
            "TOOL_CALLED",
        ]


def test_gateway_redacts_upstream_secret_and_enforces_write_kill_switch() -> None:
    with _fixtures() as transport:
        authority = LocalJwtAuthority.generate()
        store = GatewayStore()
        client = TestClient(
            create_app(transport, authority, JwtVerifier(authority.jwks()), ProtectedWritePolicy(), store)
        )
        reader = authority.issue(
            subject="reader-1",
            principal_type="human",
            team="payments",
            roles=["developer"],
            scopes=["infra.read", "audit.read"],
        )
        admin = authority.issue(
            subject="admin-1",
            principal_type="human",
            team="payments",
            roles=["gateway_admin"],
            scopes=["infra.write"],
        )
        secret_response = client.post(
            "/api/v1/tools/utility/get_synthetic_secret_demo",
            json={"arguments": {}},
            headers={"Authorization": f"Bearer {reader}"},
        )
        assert secret_response.status_code == 200
        assert "demo-super-secret-value" not in secret_response.text
        assert "[REDACTED]" in secret_response.text

        assert client.post(
            "/api/v1/admin/write-kill-switch",
            json={"writes_disabled": True},
            headers={"Authorization": f"Bearer {admin}"},
        ).status_code == 200
        blocked = client.post(
            "/api/v1/tools/infra/scale_service",
            json={
                "arguments": {
                    "team": "payments",
                    "service": "api",
                    "replicas": 2,
                    "environment": "dev",
                }
            },
            headers={"Authorization": f"Bearer {admin}"},
        )
        assert blocked.status_code == 503
        assert [event["event_type"] for event in store.audit_events()][-2:] == [
            "WRITE_KILL_SWITCH_CHANGED",
            "WRITE_KILL_SWITCH_DENIED",
        ]
        assert client.get(
            "/api/v1/audit/verify", headers={"Authorization": f"Bearer {reader}"}
        ).json() == {"valid": True}
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert 'mcp_gateway_audit_events_total{event_type="RESPONSE_REDACTED"} 1' in metrics.text


def test_schema_drift_is_quarantined_before_an_upstream_call() -> None:
    authority = LocalJwtAuthority.generate()
    store = GatewayStore()
    writer = authority.issue(
        subject="developer-1",
        principal_type="human",
        team="payments",
        roles=["developer"],
        scopes=["infra.read", "infra.write"],
    )
    with _fixtures() as initial_transport:
        initial_client = TestClient(
            create_app(initial_transport, authority, JwtVerifier(authority.jwks()), FixturePolicy(), store)
        )
        assert initial_client.get(
            "/api/v1/tools", headers={"Authorization": f"Bearer {writer}"}
        ).status_code == 200

    with _fixtures("infra_server_drift.py") as drifted_transport:
        drifted_client = TestClient(
            create_app(drifted_transport, authority, JwtVerifier(authority.jwks()), FixturePolicy(), store)
        )
        discovered = drifted_client.get(
            "/api/v1/tools", headers={"Authorization": f"Bearer {writer}"}
        )
        assert discovered.status_code == 200
        assert "scale_service" not in {tool["name"] for tool in discovered.json()["tools"]}
        blocked = drifted_client.post(
            "/api/v1/tools/infra/scale_service",
            json={
                "arguments": {
                    "team": "payments",
                    "service": "api",
                    "replicas": 2,
                    "environment": "dev",
                    "reason": "test",
                }
            },
            headers={"Authorization": f"Bearer {writer}"},
        )
        assert blocked.status_code == 409
        assert store.audit_events()[-1]["event_type"] == "TOOL_SCHEMA_QUARANTINED"
