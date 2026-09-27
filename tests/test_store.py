from __future__ import annotations

from fastapi.testclient import TestClient
from mcpgw.api import create_app
from mcpgw.store import GatewayStore


def test_hash_linked_audit_detects_tampering() -> None:
    store = GatewayStore()
    store.audit("TOOL_CALLED", "alice", "payments", metadata={"tool": "get_service_status"})
    store.audit("TOOL_CALL_DENIED", "alice", "payments", metadata={"tool": "scale_service"})
    assert store.verify_audit_chain()
    store._connection.execute("UPDATE audit_events SET metadata_json = '{}' WHERE sequence = 1")
    store._connection.commit()
    assert not store.verify_audit_chain()


def test_audit_counts_are_persisted_metric_evidence() -> None:
    store = GatewayStore()
    store.audit("TOOL_CALLED", "alice", "payments")
    store.audit("TOOL_CALLED", "alice", "payments")
    store.audit("TOOL_CALL_DENIED", "alice", "payments")
    assert store.audit_counts() == {"TOOL_CALLED": 2, "TOOL_CALL_DENIED": 1}


def test_dashboard_exposes_only_aggregate_gateway_evidence() -> None:
    store = GatewayStore()
    store.audit("TOOL_CALLED", "alice", "payments", metadata={"secret": "not exposed"})
    client = TestClient(create_app(store=store))
    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Secure MCP Gateway" in dashboard.text
    assert "not exposed" not in dashboard.text
    assert client.get("/api/v1/dashboard").json() == {
        "audit_counts": {"TOOL_CALLED": 1},
        "total_events": 1,
        "writes_disabled": False,
    }
