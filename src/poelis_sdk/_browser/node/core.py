"""Core `_Node` implementation for the Browser DSL (internal).

This file contains the `_Node` class and delegates large method bodies to
helper modules in this package.
"""

from __future__ import annotations

from types import MethodType
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from .cache import is_children_cache_stale, is_props_cache_stale, node_refresh
from .children import load_children
from .lists import list_items, list_products, list_properties, list_workspaces
from .properties import get_property, get_property_from_item_tree, properties, props_key_map
from .properties import search_property_in_item_and_children
from .versions import get_version, get_version_names, list_product_versions
from ..props import _NodeList, _PropsNode
from ..utils import _safe_key

if TYPE_CHECKING:  # pragma: no cover
    from ..props import _PropWrapper


class _Node:
    def __init__(
        self,
        client: Any,
        level: str,
        parent: Optional["_Node"],
        node_id: Optional[str],
        name: Optional[str],
        version_number: Optional[int] = None,
        baseline_version_number: Optional[int] = None,
    ) -> None:
        self._client = client
        self._level = level
        self._parent = parent
        self._id = node_id
        self._name = name
        self._version_number: Optional[int] = version_number
        self._baseline_version_number: Optional[int] = baseline_version_number
        self._children_cache: Dict[str, "_Node"] = {}
        self._props_cache: Optional[List[Dict[str, Any]]] = None
        self._children_loaded_at: Optional[float] = None
        self._props_loaded_at: Optional[float] = None
        self._cache_ttl: float = 30.0

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        path = []
        cur: Optional[_Node] = self
        while cur is not None and cur._name:
            path.append(cur._name)
            cur = cur._parent
        return f"<{self._level}:{'.'.join(reversed(path)) or '*'}>"

    def _build_path(self, attr: str) -> Optional[str]:
        if self._level == "root":
            return None
        path_parts = []
        cur: Optional[_Node] = self
        while cur is not None and cur._level != "root":
            if cur._name:
                path_parts.append(cur._name)
            cur = cur._parent
        path_parts.reverse()
        if attr:
            path_parts.append(attr)
        return ".".join(path_parts) if path_parts else None

    def __str__(self) -> str:  # pragma: no cover - notebook UX
        return self._name or ""

    @property
    def name(self) -> Optional[str]:
        return self._name

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        if self._is_children_cache_stale():
            self._load_children()
        keys = list(self._children_cache.keys())
        if self._level == "item":
            keys.extend(list(self._props_key_map().keys()))
            keys.extend(["list_items", "list_properties", "get_property"])
        elif self._level == "product":
            keys.extend(["list_items", "list_product_versions", "baseline", "draft", "get_version", "get_property"])
            keys.extend(self._get_version_names())
        elif self._level == "version":
            keys.extend(["list_items", "get_property"])
        elif self._level == "workspace":
            keys.append("list_products")
        elif self._level == "root":
            keys.append("list_workspaces")
        return sorted(set(keys))

    # --- cache helpers ---
    def _refresh(self) -> "_Node":
        return node_refresh(self)

    def _is_children_cache_stale(self) -> bool:
        return is_children_cache_stale(self)

    def _is_props_cache_stale(self) -> bool:
        return is_props_cache_stale(self)

    # --- list helpers ---
    def _list_workspaces(self) -> "_NodeList":
        return list_workspaces(self)

    def _list_products(self) -> "_NodeList":
        return list_products(self)

    def _list_items(self) -> "_NodeList":
        return list_items(self)

    def _list_properties(self) -> "_NodeList":
        return list_properties(self)

    # --- version helpers ---
    def _get_version_names(self) -> List[str]:
        return get_version_names(self)

    def _list_product_versions(self) -> "_NodeList":
        return list_product_versions(self)

    def _get_version(self, version_name: str) -> "_Node":
        return get_version(self, version_name)

    # --- properties ---
    def _properties(self) -> List[Dict[str, Any]]:
        return properties(self)

    def _props_key_map(self) -> Dict[str, Dict[str, Any]]:
        return props_key_map(self)

    def _get_property(self, readable_id: str) -> "_PropWrapper":
        """Get a property by readableId from this node context."""
        return get_property(self, readable_id)

    def _get_property_from_item_tree(self, readable_id: str) -> "_PropWrapper":
        """Get a property by readableId from this item and its descendants."""
        return get_property_from_item_tree(self, readable_id)

    def _search_property_in_item_and_children(
        self,
        item_id: Optional[str],
        readable_id: str,
        product_id: str,
        version_number: Optional[int],
    ) -> "_PropWrapper":
        """Recursive property search helper used by item-level get_property()."""
        return search_property_in_item_and_children(self, item_id, readable_id, product_id, version_number)

    def _load_children(self) -> None:
        load_children(self)

    # --- navigation helpers (kept inline; still sizable but behavior-critical) ---
    def _names(self) -> List[str]:
        if self._is_children_cache_stale():
            self._load_children()
        child_names = [child._name or "" for child in self._children_cache.values()]
        if self._level == "item":
            props = self._properties()
            prop_names: List[str] = []
            for i, pr in enumerate(props):
                display = pr.get("readableId") or pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
                prop_names.append(str(display))
            return child_names + prop_names
        return child_names

    def _suggest(self) -> List[str]:
        if self._is_children_cache_stale():
            self._load_children()
        suggestions: List[str] = list(self._children_cache.keys())
        if self._level == "item":
            suggestions.extend(list(self._props_key_map().keys()))
            suggestions.extend(["list_items", "list_properties", "get_property"])
        elif self._level == "product":
            suggestions.extend(["list_items", "list_product_versions", "baseline", "draft", "get_version", "get_property"])
            suggestions.extend(self._get_version_names())
        elif self._level == "version":
            suggestions.extend(["list_items", "get_property"])
        elif self._level == "workspace":
            suggestions.append("list_products")
        elif self._level == "root":
            suggestions.append("list_workspaces")
        return sorted(set(suggestions))

    def __getitem__(self, key: str) -> "_Node":
        if self._is_children_cache_stale():
            self._load_children()
        if key in self._children_cache:
            return self._children_cache[key]
        for child in self._children_cache.values():
            if child._name == key:
                return child
        safe = _safe_key(key)
        if safe in self._children_cache:
            return self._children_cache[safe]
        raise KeyError(key)

    def __getattr__(self, attr: str) -> Any:
        # No public properties/id/name/refresh
        if attr == "props":
            if self._level != "item":
                raise AttributeError("props")
            return _PropsNode(self)

        # Version pseudo-children for product nodes (e.g., v4, draft, baseline)
        if self._level == "product":
            if attr == "draft":
                node = _Node(self._client, "version", self, None, "draft")
                node._cache_ttl = self._cache_ttl
                return node
            elif attr == "baseline":
                # Return the configured baseline version if available, otherwise latest.
                try:
                    # Prefer configured baseline_version_number from the product model
                    version_number: Optional[int] = getattr(self, "_baseline_version_number", None)
                    if version_number is None:
                        # Fallback to latest version from backend if no baseline is configured
                        page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
                        versions = getattr(page, "data", []) or []
                        if versions:
                            latest_version = max(versions, key=lambda v: getattr(v, "version_number", 0))
                            version_number = getattr(latest_version, "version_number", None)
                    if version_number is not None:
                        node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                        node._cache_ttl = self._cache_ttl
                        return node
                    # If no versions found, fall back to draft
                    node = _Node(self._client, "version", self, None, "draft")
                    node._cache_ttl = self._cache_ttl
                    return node
                except Exception:
                    # On error, fall back to draft
                    node = _Node(self._client, "version", self, None, "draft")
                    node._cache_ttl = self._cache_ttl
                    return node
            elif attr.startswith("v") and attr[1:].isdigit():
                version_number = int(attr[1:])
                # Verify that this version actually exists before creating the node
                try:
                    page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
                    versions = getattr(page, "data", []) or []
                    version_numbers = [getattr(v, "version_number", None) for v in versions]
                    if version_number not in version_numbers:
                        available_versions = [v for v in version_numbers if v is not None]
                        raise AttributeError(
                            f"Version '{attr}' does not exist for product '{self._name or self._id}'. "
                            f"Available versions: {', '.join(f'v{v}' for v in sorted(available_versions)) if available_versions else 'none'}"
                        )
                except Exception as e:
                    # If it's already an AttributeError, re-raise it
                    if isinstance(e, AttributeError):
                        raise
                    # For other errors (e.g., network issues), still create the node
                    # to avoid breaking existing code that might handle errors differently
                    pass
                node = _Node(self._client, "version", self, str(version_number), attr)
                node._cache_ttl = self._cache_ttl
                return node
            if attr not in ("list_items", "list_product_versions"):
                try:
                    version_number: Optional[int] = getattr(self, "_baseline_version_number", None)
                    if version_number is None:
                        page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
                        versions = getattr(page, "data", []) or []
                        if versions:
                            latest_version = max(versions, key=lambda v: getattr(v, "version_number", 0))
                            version_number = getattr(latest_version, "version_number", None)
                    if version_number is not None:
                        latest_node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                        latest_node._cache_ttl = self._cache_ttl
                        if latest_node._is_children_cache_stale():
                            latest_node._load_children()
                        if attr in latest_node._children_cache:
                            return latest_node._children_cache[attr]
                except Exception:
                    pass

        if self._is_children_cache_stale():
            self._load_children()
        if attr in self._children_cache:
            child = self._children_cache[attr]
            if self._client is not None:
                try:
                    change_tracker = getattr(self._client, "_change_tracker", None)
                    if change_tracker is not None and change_tracker.is_enabled():
                        item_path = self._build_path(attr)
                        if item_path:
                            child_name = getattr(child, "_name", attr) or attr
                            child_id = getattr(child, "_id", None)
                            change_tracker.record_accessed_item(item_path, child_name, child_id)
                except Exception:
                    pass
            return child

        if attr == "list_workspaces":
            if self._level == "root":
                return MethodType(_Node._list_workspaces, self)
            raise AttributeError(attr)
        if attr == "list_products":
            if self._level == "workspace":
                return MethodType(_Node._list_products, self)
            raise AttributeError(attr)
        if attr == "list_product_versions":
            if self._level == "product":
                return MethodType(_Node._list_product_versions, self)
            raise AttributeError(attr)
        if attr == "get_version":
            if self._level == "product":
                return MethodType(_Node._get_version, self)
            raise AttributeError(attr)
        if attr == "list_items":
            if self._level in ("product", "item", "version"):
                return MethodType(_Node._list_items, self)
            raise AttributeError(attr)
        if attr == "list_properties":
            if self._level == "item":
                return MethodType(_Node._list_properties, self)
            raise AttributeError(attr)
        if attr == "get_property":
            if self._level in ("product", "version", "item"):
                return MethodType(_Node._get_property, self)
            raise AttributeError(attr)

        if self._level == "item":
            pk = self._props_key_map()
            if attr in pk:
                prop_wrapper = pk[attr]
                if self._client is not None:
                    try:
                        change_tracker = getattr(self._client, "_change_tracker", None)
                        if change_tracker is not None and change_tracker.is_enabled():
                            property_path = self._build_path(attr)
                            if property_path:
                                prop_name = (
                                    getattr(prop_wrapper, "_raw", {}).get("readableId")
                                    or getattr(prop_wrapper, "_raw", {}).get("name")
                                    or attr
                                )
                                prop_id = getattr(prop_wrapper, "_raw", {}).get("id")
                                change_tracker.record_accessed_property(property_path, prop_name, prop_id)
                    except Exception:
                        pass
                return prop_wrapper

            if self._client is not None:
                try:
                    change_tracker = getattr(self._client, "_change_tracker", None)
                    if change_tracker is not None and change_tracker.is_enabled():
                        property_path = self._build_path(attr)
                        if property_path:
                            change_tracker.warn_if_deleted(property_path=property_path)
                except Exception:
                    pass

        if self._client is not None:
            try:
                change_tracker = getattr(self._client, "_change_tracker", None)
                if change_tracker is not None and change_tracker.is_enabled():
                    item_path = self._build_path(attr)
                    if item_path:
                        change_tracker.warn_if_deleted(item_path=item_path)
            except Exception:
                pass

        raise AttributeError(attr)




