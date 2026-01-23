"""Child-loading logic for Browser `_Node` (internal)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from ..utils import _safe_key

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


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
            version_number: Optional[int] = getattr(node, "_baseline_version_number", None)
            if version_number is None:
                page = node._client.products.list_product_versions(product_id=node._id, limit=100, offset=0)
                versions = getattr(page, "data", []) or []
                if versions:
                    latest_version = max(versions, key=lambda v: getattr(v, "version_number", 0))
                    version_number = getattr(latest_version, "version_number", None)
            if version_number is not None:
                rows = node._client.versions.list_items(
                    product_id=node._id,
                    version_number=version_number,
                    limit=1000,
                    offset=0,
                )
                for it in rows:
                    if it.get("parentId") is None:
                        display = it.get("readableId") or it.get("name") or str(it["id"])
                        nm = _safe_key(display)
                        child = node.__class__(node._client, "item", node, it["id"], display, version_number=version_number)
                        child._cache_ttl = node._cache_ttl
                        node._children_cache[nm] = child
                node._children_loaded_at = time.time()
                return
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        except Exception:
            pass

        if not node._children_cache:
            rows = node._client.items.list_by_product(product_id=node._id, limit=1000, offset=0)
            for it in rows:
                if it.get("parentId") is None:
                    display = it.get("readableId") or it.get("name") or str(it["id"])
                    nm = _safe_key(display)
                    child = node.__class__(node._client, "item", node, it["id"], display)
                    child._cache_ttl = node._cache_ttl
                    node._children_cache[nm] = child
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
            rows = node._client.items.list_by_product(product_id=pid, limit=1000, offset=0)
        else:
            rows = node._client.versions.list_items(
                product_id=pid,
                version_number=version_number,
                limit=1000,
                offset=0,
            )

        for it in rows:
            if it.get("parentId") is None:
                display = it.get("readableId") or it.get("name") or str(it["id"])
                nm = _safe_key(display)
                child = node.__class__(node._client, "item", node, it["id"], display, version_number=version_number)
                child._cache_ttl = node._cache_ttl
                node._children_cache[nm] = child
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

        if version_number is not None:
            all_items = node._client.versions.list_items(
                product_id=pid,
                version_number=version_number,
                limit=1000,
                offset=0,
            )
            rows = [it for it in all_items if it.get("parentId") == node._id]
        else:
            all_items = node._client.items.list_by_product(product_id=pid, limit=1000, offset=0)
            rows = [it for it in all_items if it.get("parentId") == node._id]

        for it2 in rows:
            if str(it2.get("id")) == str(node._id):
                continue
            display = it2.get("readableId") or it2.get("name") or str(it2["id"])
            nm = _safe_key(display)
            child = node.__class__(node._client, "item", node, it2["id"], display, version_number=version_number)
            child._cache_ttl = node._cache_ttl
            node._children_cache[nm] = child

    node._children_loaded_at = time.time()



