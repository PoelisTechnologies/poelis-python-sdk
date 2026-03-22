"""Shared utilities for the internal Browser refactor package."""

from __future__ import annotations

import re
from typing import Any, Mapping


def _safe_key(name: str) -> str:
    """Convert arbitrary display name to a safe attribute key (letters/digits/_).

    This mirrors the behavior in `poelis_sdk.browser` and is kept internal to
    avoid exposing additional public API surface during refactors.
    """

    key = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    key = key.strip("_")
    return key or "_"


def _is_visible_version_item(item: Mapping[str, Any]) -> bool:
    """Return True when a versioned item should appear in tree navigation."""

    return not bool(item.get("deleted"))


def _is_visible_version_property(prop: Mapping[str, Any]) -> bool:
    """Return True when a versioned property should appear in browser reads."""

    return not bool(prop.get("deleted"))


