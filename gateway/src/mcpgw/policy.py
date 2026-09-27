"""OPA policy client. Protected actions fail closed if OPA is unavailable."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from mcpgw.auth import Identity


@dataclass(frozen=True)
class PolicyDecision:
    allow: bool
    approval_required: bool
    reason: str


class PolicyEngine(Protocol):
    def decide(
        self, identity: Identity, action: str, tool: dict[str, Any], arguments: dict[str, Any]
    ) -> PolicyDecision: ...


class OpaPolicyEngine:
    def __init__(self, url: str, timeout_seconds: float = 2.0) -> None:
        self._url = url.rstrip("/") + "/v1/data/mcp/authz/decision"
        self._timeout_seconds = timeout_seconds

    def decide(
        self, identity: Identity, action: str, tool: dict[str, Any], arguments: dict[str, Any]
    ) -> PolicyDecision:
        payload = json.dumps(
            {
                "input": {
                    "identity": {
                        "subject": identity.subject,
                        "principal_type": identity.principal_type,
                        "team": identity.team,
                        "roles": sorted(identity.roles),
                        "scopes": sorted(identity.scopes),
                        "delegated_by": identity.delegated_by,
                    },
                    "action": action,
                    "tool": tool,
                    "arguments": arguments,
                }
            }
        ).encode()
        request = urllib.request.Request(
            self._url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                result = json.load(response)["result"]
        except (KeyError, OSError, json.JSONDecodeError, urllib.error.URLError) as exc:
            return PolicyDecision(False, False, f"policy_unavailable:{type(exc).__name__}")
        return PolicyDecision(
            bool(result.get("allow", False)),
            bool(result.get("approval_required", False)),
            str(result.get("reason", "unspecified")),
        )
