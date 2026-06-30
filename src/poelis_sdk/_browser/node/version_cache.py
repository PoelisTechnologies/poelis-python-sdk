"""Product version list caching for Browser `_Node` (internal)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


def _get_product_versions(node: "_Node") -> list[Any]:
    """Return cached product versions for a product node."""
    if node._level != "product":
        return []

    loaded_at = getattr(node, "_versions_loaded_at", None)
    cache = getattr(node, "_versions_cache", None)
    if cache is not None and loaded_at is not None and time.time() - loaded_at <= node._cache_ttl:
        return cache

    page = node._client.products.list_product_versions(product_id=node._id, limit=100, offset=0)
    versions = list(getattr(page, "data", []) or [])
    node._versions_cache = versions
    node._versions_loaded_at = time.time()
    return versions


def _resolve_baseline_version_number(node: "_Node") -> int | None:
    """Resolve baseline/latest version number without redundant network calls."""
    if node._level != "product":
        return None

    configured = getattr(node, "_baseline_version_number", None)
    if configured is not None:
        return int(configured)

    versions = _get_product_versions(node)
    if not versions:
        return None
    latest = max(versions, key=lambda v: getattr(v, "version_number", 0))
    return getattr(latest, "version_number", None)
