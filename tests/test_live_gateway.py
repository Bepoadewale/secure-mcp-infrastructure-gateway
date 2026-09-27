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

ROOT = Path(__file__).resolve().parents[1]


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
def _fixtures() -> Iterator[MCPTransportGateway]:
    infra_port, utility_port = _free_port(), _free_port()
    processes = [
        subprocess.Popen(
            [sys.executable, str(ROOT / "fixtures" / script)],
            cwd=ROOT,
            env={**os.environ, "MCP_FIXTURE_PORT": str(port)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for script, port in (("infra_server.py", infra_port), ("utility_server.py", utility_port))
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
        client = TestClient(create_app(transport, authority, JwtVerifier(authority.jwks())))
        read_token = authority.issue(
            subject="agent-1",
            principal_type="agent",
            team="payments",
            roles=["agent"],
            scopes=[],
        )
        write_token = authority.issue(
            subject="developer-1",
            principal_type="human",
            team="payments",
            roles=["developer"],
            scopes=["infra.write"],
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
