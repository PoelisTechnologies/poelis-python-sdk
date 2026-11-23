"""Shared utilities for the internal Browser refactor package."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..exceptions import AmbiguousKeyError


def _safe_key(name: str) -> str:
    """Convert arbitrary display name to a safe attribute key (letters/digits/_).

    This mirrors the behavior in `poelis_sdk.browser` and is kept internal to
    avoid exposing additional public API surface during refactors.
    """

    key = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    key = key.strip("_")
    return key or "_"


def _assign_keys(rows: Sequence[Mapping[str, Any]]) -> Tuple[List[str], Dict[str, List[Mapping[str, Any]]]]:
    """Give each row a unique attribute key and report the keys several rows share.

    A repeated key gets a numeric suffix so every row stays in listings. The second
    result maps a key to the rows whose readable id is that same key: reading such a
    key raises instead of returning one of them.
    """

    keys: List[str] = []
    taken: set[str] = set()
    by_readable_id: Dict[str, List[Mapping[str, Any]]] = {}
    for index, row in enumerate(rows):
        display = row.get("readableId") or row.get("name") or row.get("id") or row.get("category") or f"property_{index}"
        base = _safe_key(str(display))
        if row.get("readableId"):
            by_readable_id.setdefault(base, []).append(row)
        safe, suffix = base, 0
        while safe in taken:
            suffix += 1
            safe = f"{base}_{suffix}"
        taken.add(safe)
        keys.append(safe)
    return keys, {key: group for key, group in by_readable_id.items() if len(group) > 1}


def _ambiguous_key_error(
    kind: str, key: str, rows: Sequence[Mapping[str, Any]], version_number: Optional[int]
) -> AmbiguousKeyError:
    where = f"version {version_number}" if version_number is not None else "the draft"
    matches = ", ".join(f"'{row.get('name')}' (id {row.get('id')})" for row in rows)
    return AmbiguousKeyError(f"Key '{key}' matches {len(rows)} {kind} in {where}: {matches}.")


def _is_visible_version_item(item: Mapping[str, Any]) -> bool:
    """Return True when a versioned item should appear in tree navigation."""

    return not bool(item.get("deleted"))


def _is_visible_version_property(prop: Mapping[str, Any]) -> bool:
    """Return True when a versioned property should appear in browser reads."""

    return not bool(prop.get("deleted"))


