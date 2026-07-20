"""Child-loading logic for Browser `_Node` (internal)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from poelis_sdk._item_filter import item_draft_id

from .item_queries import (
    _direct_child_rows,
    _list_draft_items,
    _list_versioned_items,
    _node_parent_filter_id,
)
from .version_cache import _resolve_baseline_version_number
from ..utils import _safe_key

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


def _append_item_child(parent: "_Node", item_row: dict, *, version_number: Optional[int]) -> None:
    display = item_row.get("readableId") or item_row.get("name") or str(item_row["id"])
    nm = _safe_key(display)
    child = parent.__class__(
        parent._client,
        "item",
        parent,
        item_row["id"],
        display,
        version_number=version_number,
        draft_item_id=item_draft_id(item_row),
    )
    child._cache_ttl = parent._cache_ttl
    parent._children_cache[nm] = child


def load_children(node: "_Node") -> None:
    """Populate `_children_cache` for the given node (behavior preserved)."""
    if node._level == "root":
        rows = node._client.workspaces.list(limit=200, offset=0)
        for w in rows:
            display = w.get("readableId") or w.get("name") or str(w.get("id"))
            nm = _safe_key(display)
            child = node.__class__(node._client, "workspace", node, w["id"], display)
            child._cache_ttl = node._cache_ttl
            node._children_cache[nm] = child
    elif node._level == "workspace":
        page = node._client.products.list_by_workspace(workspace_id=node._id, limit=200, offset=0)
        for p in page.data:
            display = p.readableId or p.name or str(p.id)
            nm = _safe_key(display)
            child = node.__class__(
                node._client,
                "product",
                node,
                p.id,
                display,
                baseline_version_number=getattr(p, "baseline_version_number", None),
            )
            child._cache_ttl = node._cache_ttl
            node._children_cache[nm] = child
    elif node._level == "product":
        node._children_cache.clear()

        try:
            version_number: Optional[int] = _resolve_baseline_version_number(node)
            if version_number is not None:
                rows = _list_versioned_items(
                    node,
                    product_id=node._id,
                    version_number=version_number,
                    root_only=True,
                )
                for it in rows:
                    _append_item_child(node, it, version_number=version_number)
                node._children_loaded_at = time.time()
                return
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        except Exception:
            pass

        if not node._children_cache:
            rows = _list_draft_items(node, product_id=node._id, root_only=True)
            for it in rows:
                _append_item_child(node, it, version_number=None)
    elif node._level == "version":
        anc = node
        pid: Optional[str] = None
        while anc is not None:
            if anc._level == "product":
                pid = anc._id
                break
            anc = anc._parent  # type: ignore[assignment]
        if not pid:
            return
        try:
            version_number = int(node._id) if node._id is not None else None
        except (TypeError, ValueError):
            version_number = None

        if version_number is None:
            rows = _list_draft_items(node, product_id=pid, root_only=True)
        else:
            rows = _list_versioned_items(
                node,
                product_id=pid,
                version_number=version_number,
                root_only=True,
            )

        for it in rows:
            _append_item_child(node, it, version_number=version_number)
    elif node._level == "item":
        anc = node
        pid: Optional[str] = None
        while anc is not None:
            if anc._level == "product":
                pid = anc._id
                break
            anc = anc._parent  # type: ignore[assignment]
        if not pid:
            return

        version_number = getattr(node, "_version_number", None)
        parent_filter_id = _node_parent_filter_id(node)

        if version_number is not None:
            rows = _list_versioned_items(
                node,
                product_id=pid,
                version_number=version_number,
                parent_item_id=parent_filter_id,
            )
        else:
            rows = _list_draft_items(
                node,
                product_id=pid,
                parent_item_id=parent_filter_id,
            )
        rows = _direct_child_rows(rows, parent_node_id=str(node._id))

        for it2 in rows:
            _append_item_child(node, it2, version_number=version_number)

    node._children_loaded_at = time.time()
