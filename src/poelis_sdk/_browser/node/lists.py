"""List helper methods for Browser `_Node` (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..props import _NodeList, _PropWrapper
from .version_cache import _resolve_baseline_version_number

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


def list_workspaces(node: "_Node") -> "_NodeList":
    """Return workspaces at root as a list-like object with `.names`."""
    if node._level != "root":
        return _NodeList([], [])
    if node._is_children_cache_stale():
        node._load_children()
    items = list(node._children_cache.values())
    names = [n._name or "" for n in items]
    return _NodeList(items, names)


def list_products(node: "_Node") -> "_NodeList":
    """Return products at workspace level as a list-like object with `.names`."""
    if node._level != "workspace":
        return _NodeList([], [])
    if node._is_children_cache_stale():
        node._load_children()
    items = list(node._children_cache.values())
    names = [n._name or "" for n in items]
    return _NodeList(items, names)


def list_items(node: "_Node") -> "_NodeList":
    """Return items at product/item/version level as a list-like object with `.names`."""
    if node._level not in ("product", "item", "version"):
        return _NodeList([], [])

    if node._level == "product":
        try:
            version_number: Optional[int] = _resolve_baseline_version_number(node)
            if version_number is not None:
                baseline_node = node.__class__(node._client, "version", node, str(version_number), f"v{version_number}")
                baseline_node._cache_ttl = node._cache_ttl
                return baseline_node._list_items()
            draft_node = node.__class__(node._client, "version", node, None, "draft")
            draft_node._cache_ttl = node._cache_ttl
            return draft_node._list_items()
        except Exception:
            draft_node = node.__class__(node._client, "version", node, None, "draft")
            draft_node._cache_ttl = node._cache_ttl
            return draft_node._list_items()

    if node._is_children_cache_stale():
        node._load_children()
    items = list(node._children_cache.values())
    names = [n._name or "" for n in items]
    return _NodeList(items, names)


def list_properties(node: "_Node") -> "_NodeList":
    """Return item properties as a list-like object with `.names`."""
    if node._level != "item":
        return _NodeList([], [])
    props = node._properties()
    wrappers: list[_PropWrapper] = []
    names: list[str] = []
    for i, pr in enumerate(props):
        display = pr.get("readableId") or pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
        names.append(str(display))
        wrappers.append(_PropWrapper(pr, client=node._client))
    return _NodeList(wrappers, names)




