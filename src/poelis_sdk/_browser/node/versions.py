"""Product version helper methods for Browser `_Node` (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from ..props import _NodeList

if TYPE_CHECKING:  # pragma: no cover
    from ..nodes import _Node


def get_version_names(node: "_Node") -> List[str]:
    """Return a list of version names (v1, v2, ...) for product nodes."""
    if node._level != "product":
        return []

    version_names: List[str] = []
    try:
        page = node._client.products.list_product_versions(product_id=node._id, limit=100, offset=0)
        versions_data = getattr(page, "data", []) or []
        for v in versions_data:
            version_number = getattr(v, "version_number", None)
            if version_number is not None:
                version_names.append(f"v{version_number}")
    except Exception:
        pass

    return version_names


def list_product_versions(node: "_Node") -> "_NodeList":
    """Return product versions as a list-like object with `.names`."""
    if node._level != "product":
        return _NodeList([], [])

    items = []
    names: List[str] = []

    draft_node = node.__class__(node._client, "version", node, None, "draft")
    draft_node._cache_ttl = node._cache_ttl
    items.append(draft_node)
    names.append("draft")

    try:
        page = node._client.products.list_product_versions(product_id=node._id, limit=100, offset=0)
        for v in getattr(page, "data", []) or []:
            version_number = getattr(v, "version_number", None)
            if version_number is None:
                continue
            name = f"v{version_number}"
            ver_node = node.__class__(node._client, "version", node, str(version_number), name)
            ver_node._cache_ttl = node._cache_ttl
            items.append(ver_node)
            names.append(name)
    except Exception:
        pass

    return _NodeList(items, names)


def get_version(node: "_Node", version_name: str) -> "_Node":
    """Return a version node by title/name for product nodes."""
    if node._level != "product":
        raise AttributeError("get_version() method is only available on product nodes")

    try:
        page = node._client.products.list_product_versions(product_id=node._id, limit=100, offset=0)
        versions = getattr(page, "data", []) or []

        search_term = version_name.strip().lower()

        for v in versions:
            title = getattr(v, "title", None)
            if title and title.strip().lower() == search_term:
                version_number = getattr(v, "version_number", None)
                if version_number is not None:
                    out = node.__class__(node._client, "version", node, str(version_number), f"v{version_number}")
                    out._cache_ttl = node._cache_ttl
                    return out

        for v in versions:
            title = getattr(v, "title", None)
            if title and search_term in title.strip().lower():
                version_number = getattr(v, "version_number", None)
                if version_number is not None:
                    out = node.__class__(node._client, "version", node, str(version_number), f"v{version_number}")
                    out._cache_ttl = node._cache_ttl
                    return out

        if search_term.startswith("v"):
            try:
                version_num = int(search_term[1:])
                for v in versions:
                    version_number = getattr(v, "version_number", None)
                    if version_number == version_num:
                        out = node.__class__(node._client, "version", node, str(version_number), f"v{version_number}")
                        out._cache_ttl = node._cache_ttl
                        return out
            except ValueError:
                pass
        else:
            try:
                version_num = int(search_term)
                for v in versions:
                    version_number = getattr(v, "version_number", None)
                    if version_number == version_num:
                        out = node.__class__(node._client, "version", node, str(version_number), f"v{version_number}")
                        out._cache_ttl = node._cache_ttl
                        return out
            except ValueError:
                pass

        available_titles = [getattr(v, "title", f"v{getattr(v, 'version_number', '?')}") for v in versions]
        raise ValueError(
            f"No version found matching '{version_name}'. "
            f"Available versions: {', '.join(available_titles)}"
        )
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Error retrieving versions: {e}")




