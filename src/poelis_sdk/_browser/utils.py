"""Shared utilities for the internal Browser refactor package."""

from __future__ import annotations

import re


def _safe_key(name: str) -> str:
    """Convert arbitrary display name to a safe attribute key (letters/digits/_).

    This mirrors the behavior in `poelis_sdk.browser` and is kept internal to
    avoid exposing additional public API surface during refactors.
    """

    key = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    key = key.strip("_")
    return key or "_"




