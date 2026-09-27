"""Integration proof that the official SDK speaks MCP to our local fixture."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from mcp import Client

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


def test_official_sdk_lists_and_calls_local_mcp_tools() -> None:
    port = _free_port()
    environment = {**os.environ, "MCP_FIXTURE_PORT": str(port)}
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "fixtures" / "infra_server.py")],
        cwd=ROOT,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_port(port)

        async def exercise_protocol() -> tuple[list[str], dict[str, str]]:
            async with Client(f"http://127.0.0.1:{port}/mcp") as client:
                tools = await client.list_tools()
                result = await client.call_tool(
                    "get_service_status", {"team": "payments", "service": "api"}
                )
                return [tool.name for tool in tools.tools], result.structured_content

        names, response = asyncio.run(exercise_protocol())
        assert names == ["get_service_status", "scale_service"]
        assert response == {"team": "payments", "service": "api", "status": "healthy"}
    finally:
        process.terminate()
        process.wait(timeout=5)
