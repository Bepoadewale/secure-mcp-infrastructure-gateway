"""Redact known synthetic secret patterns before returning or auditing tool output."""

from __future__ import annotations

import re
from typing import Any

SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|authorization|token)=([^\s,}]+)")


def redact(value: Any) -> tuple[Any, bool]:
    if isinstance(value, str):
        redacted = SECRET_PATTERN.sub(r"\1=[REDACTED]", value)
        return redacted, redacted != value
    if isinstance(value, list):
        entries = [redact(entry) for entry in value]
        return [entry[0] for entry in entries], any(entry[1] for entry in entries)
    if isinstance(value, dict):
        entries = {key: redact(entry) for key, entry in value.items()}
        return {key: entry[0] for key, entry in entries.items()}, any(entry[1] for entry in entries.values())
    return value, False
