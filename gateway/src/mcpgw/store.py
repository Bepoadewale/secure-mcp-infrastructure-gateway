"""SQLite persistence for approval-bound actions and tamper-evident audit data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def action_hash(requester: str, team: str, server: str, tool: str, arguments: dict[str, Any]) -> str:
    canonical = json.dumps(
        {
            "requester": requester,
            "team": team,
            "server": server,
            "tool": tool,
            "arguments": arguments,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class Plan:
    id: str
    requester: str
    team: str
    server: str
    tool: str
    action_hash: str
    status: str


class GatewayStore:
    def __init__(self, database: str = ":memory:") -> None:
        if database != ":memory":
            Path(database).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id TEXT PRIMARY KEY,
                requester TEXT NOT NULL,
                team TEXT NOT NULL,
                server TEXT NOT NULL,
                tool TEXT NOT NULL,
                action_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                approved_by TEXT,
                consumed_at REAL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                subject TEXT NOT NULL,
                team TEXT NOT NULL,
                action_hash TEXT,
                metadata_json TEXT NOT NULL,
                previous_hash TEXT,
                event_hash TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tool_schemas (
                server TEXT NOT NULL,
                tool TEXT NOT NULL,
                schema_digest TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (server, tool)
            );
            CREATE TABLE IF NOT EXISTS gateway_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        try:
            self._connection.execute("ALTER TABLE plans ADD COLUMN consumed_at REAL")
        except sqlite3.OperationalError:
            pass
        self._connection.execute(
            "INSERT OR IGNORE INTO gateway_settings (key, value) VALUES ('writes_disabled', 'false')"
        )
        self._connection.commit()

    def create_plan(
        self, requester: str, team: str, server: str, tool: str, arguments: dict[str, Any]
    ) -> Plan:
        digest = action_hash(requester, team, server, tool, arguments)
        plan = Plan(str(uuid.uuid4()), requester, team, server, tool, digest, "PENDING_APPROVAL")
        self._connection.execute(
            """INSERT INTO plans
            (id, requester, team, server, tool, action_hash, status, created_at, approved_by, consumed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)""",
            (*plan.__dict__.values(), time.time()),
        )
        self._connection.commit()
        return plan

    def approve(self, plan_id: str, approver: str) -> Plan:
        plan = self.get_plan(plan_id)
        if plan.requester == approver:
            raise PermissionError("requester cannot approve their own protected action")
        if plan.status != "PENDING_APPROVAL":
            raise ValueError("plan is not pending approval")
        self._connection.execute(
            "UPDATE plans SET status = 'APPROVED', approved_by = ? WHERE id = ?", (approver, plan_id)
        )
        self._connection.commit()
        return self.get_plan(plan_id)

    def get_plan(self, plan_id: str) -> Plan:
        row = self._connection.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if not row:
            raise KeyError("unknown plan")
        return Plan(
            row["id"],
            row["requester"],
            row["team"],
            row["server"],
            row["tool"],
            row["action_hash"],
            row["status"],
        )

    def approval_is_current(
        self, plan_id: str, requester: str, team: str, server: str, tool: str, arguments: dict[str, Any]
    ) -> bool:
        plan = self.get_plan(plan_id)
        return plan.status == "APPROVED" and plan.action_hash == action_hash(
            requester, team, server, tool, arguments
        )

    def consume_approval(self, plan_id: str) -> None:
        updated = self._connection.execute(
            "UPDATE plans SET status = 'EXECUTED', consumed_at = ? WHERE id = ? AND status = 'APPROVED'",
            (time.time(), plan_id),
        )
        self._connection.commit()
        if updated.rowcount != 1:
            raise ValueError("approval was already consumed or is not approved")

    def observe_schema(self, server: str, tool: str, digest: str) -> str:
        row = self._connection.execute(
            "SELECT schema_digest, status FROM tool_schemas WHERE server = ? AND tool = ?", (server, tool)
        ).fetchone()
        if row is None:
            self._connection.execute(
                "INSERT INTO tool_schemas VALUES (?, ?, ?, 'APPROVED')", (server, tool, digest)
            )
            self._connection.commit()
            return "APPROVED"
        if row["schema_digest"] != digest:
            self._connection.execute(
                "UPDATE tool_schemas SET status = 'QUARANTINED' WHERE server = ? AND tool = ?",
                (server, tool),
            )
            self._connection.commit()
            return "QUARANTINED"
        return str(row["status"])

    def writes_disabled(self) -> bool:
        value = self._connection.execute(
            "SELECT value FROM gateway_settings WHERE key = 'writes_disabled'"
        ).fetchone()["value"]
        return value == "true"

    def set_writes_disabled(self, disabled: bool) -> None:
        self._connection.execute(
            "UPDATE gateway_settings SET value = ? WHERE key = 'writes_disabled'",
            ("true" if disabled else "false",),
        )
        self._connection.commit()

    def audit(
        self,
        event_type: str,
        subject: str,
        team: str,
        action_digest: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        previous = self._connection.execute(
            "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else None
        safe_metadata = json.dumps(metadata or {}, sort_keys=True, separators=(",", ":"))
        created_at = time.time()
        material = "|".join(
            [event_type, subject, team, action_digest or "", safe_metadata, previous_hash or "", str(created_at)]
        )
        event_hash = hashlib.sha256(material.encode()).hexdigest()
        self._connection.execute(
            "INSERT INTO audit_events (event_type, subject, team, action_hash, metadata_json, previous_hash, event_hash, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (event_type, subject, team, action_digest, safe_metadata, previous_hash, event_hash, created_at),
        )
        self._connection.commit()
        return event_hash

    def audit_events(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._connection.execute("SELECT * FROM audit_events ORDER BY sequence")]

    def verify_audit_chain(self) -> bool:
        """Verify immutable event material and predecessor links before trusting an audit export."""
        previous_hash: str | None = None
        for event in self.audit_events():
            if event["previous_hash"] != previous_hash:
                return False
            material = "|".join(
                [
                    event["event_type"],
                    event["subject"],
                    event["team"],
                    event["action_hash"] or "",
                    event["metadata_json"],
                    previous_hash or "",
                    str(event["created_at"]),
                ]
            )
            expected = hashlib.sha256(material.encode()).hexdigest()
            if event["event_hash"] != expected:
                return False
            previous_hash = event["event_hash"]
        return True

    def audit_counts(self) -> dict[str, int]:
        return {
            str(row["event_type"]): int(row["count"])
            for row in self._connection.execute(
                "SELECT event_type, COUNT(*) AS count FROM audit_events GROUP BY event_type"
            )
        }
