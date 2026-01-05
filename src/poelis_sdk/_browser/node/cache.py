"""Cache helpers for the Browser `_Node` implementation (internal)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


def node_refresh(node: "_Node") -> "_Node":
    """Clear `_Node` caches (structural refactor helper; behavior preserved)."""
    node._children_cache.clear()
    node._props_cache = None
    node._children_loaded_at = None
    node._props_loaded_at = None
    return node


def is_children_cache_stale(node: "_Node") -> bool:
    """Return True if the children cache is stale and should be refreshed."""
    if not node._children_cache:
        return True
    if node._children_loaded_at is None:
        return True
    return time.time() - node._children_loaded_at > node._cache_ttl


def is_props_cache_stale(node: "_Node") -> bool:
    """Return True if the properties cache is stale and should be refreshed."""
    if node._props_cache is None:
        return True
    if node._props_loaded_at is None:
        return True
    return time.time() - node._props_loaded_at > node._cache_ttl



