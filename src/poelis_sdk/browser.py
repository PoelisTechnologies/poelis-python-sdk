from __future__ import annotations

import re
import time
from types import MethodType
from typing import Any, Dict, List, Optional

from .org_validation import get_organization_context_message

"""GraphQL-backed dot-path browser for Poelis SDK.

Provides lazy, name-based navigation across workspaces → products → items → child items,
with optional property listing on items. Designed for notebook UX.
"""


# Internal guard to avoid repeated completer installation
_AUTO_COMPLETER_INSTALLED: bool = False


class _Node:
    def __init__(self, client: Any, level: str, parent: Optional["_Node"], node_id: Optional[str], name: Optional[str], version_number: Optional[int] = None) -> None:
        self._client = client
        self._level = level
        self._parent = parent
        self._id = node_id
        self._name = name
        self._version_number: Optional[int] = version_number  # Track version context for items
        self._children_cache: Dict[str, "_Node"] = {}
        self._props_cache: Optional[List[Dict[str, Any]]] = None
        # Performance optimization: cache metadata with TTL
        self._children_loaded_at: Optional[float] = None
        self._props_loaded_at: Optional[float] = None
        self._cache_ttl: float = 30.0  # 30 seconds cache TTL

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        path = []
        cur: Optional[_Node] = self
        while cur is not None and cur._name:
            path.append(cur._name)
            cur = cur._parent
        return f"<{self._level}:{'.'.join(reversed(path)) or '*'}>"
    
    def _build_path(self, attr: str) -> Optional[str]:
        """Build a path string for tracking items/properties.
        
        Args:
            attr: Attribute name being accessed.
        
        Returns:
            Optional[str]: Path string like "workspace.product.item" or "workspace.product.item.property", None if invalid.
        """
        if self._level == "root":
            return None  # Root level doesn't have a path
        
        path_parts = []
        cur: Optional[_Node] = self
        
        # Build path from current node up to root
        while cur is not None and cur._level != "root":
            if cur._name:
                path_parts.append(cur._name)
            cur = cur._parent
        
        # Reverse to get root-to-current order
        path_parts.reverse()
        
        # Add the attribute being accessed
        if attr:
            path_parts.append(attr)
        
        return ".".join(path_parts) if path_parts else None

    def __str__(self) -> str:  # pragma: no cover - notebook UX
        """Return the display name of this node for string conversion.
        
        This allows items to be printed directly and show just their name,
        while repr() still shows the full path for debugging.
        
        Returns:
            str: The human-friendly display name, or empty string if unknown.
        """
        return self._name or ""

    @property
    def name(self) -> Optional[str]:
        """Return the display name of this node if available.

        Returns:
            Optional[str]: The human-friendly display name, or None if unknown.
        """
        return self._name

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        # Performance optimization: only load children if cache is stale or empty
        if self._is_children_cache_stale():
            self._load_children()
        keys = list(self._children_cache.keys())
        if self._level == "item":
            # Include property names directly on item for suggestions
            prop_keys = list(self._props_key_map().keys())
            keys.extend(prop_keys)
            keys.extend(["list_items", "list_properties", "get_property"])
        elif self._level == "product":
            # At product level, show items from baseline (latest version) + helper methods + version names
            keys.extend(["list_items", "list_product_versions", "baseline", "draft", "get_version", "get_property"])
            # Include version names (v1, v2, etc.) in autocomplete suggestions
            version_names = self._get_version_names()
            keys.extend(version_names)
        elif self._level == "version":
            keys.extend(["list_items", "get_property"])
        elif self._level == "workspace":
            keys.append("list_products")
        elif self._level == "root":
            keys.append("list_workspaces")
        return sorted(set(keys))

    # Intentionally no public id/name/refresh to keep suggestions minimal
    def _refresh(self) -> "_Node":
        self._children_cache.clear()
        self._props_cache = None
        self._children_loaded_at = None
        self._props_loaded_at = None
        return self

    def _is_children_cache_stale(self) -> bool:
        """Check if children cache is stale and needs refresh."""
        if not self._children_cache:
            return True
        if self._children_loaded_at is None:
            return True
        return time.time() - self._children_loaded_at > self._cache_ttl

    def _is_props_cache_stale(self) -> bool:
        """Check if properties cache is stale and needs refresh."""
        if self._props_cache is None:
            return True
        if self._props_loaded_at is None:
            return True
        return time.time() - self._props_loaded_at > self._cache_ttl

    def _names(self) -> List[str]:
        """Return display names of children at this level (internal).

        For item level, include both child item names and property display names.
        """
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

    # names() removed in favor of list_*().names

    # --- Node-list helpers ---
    def _list_workspaces(self) -> "_NodeList":
        if self._level != "root":
            return _NodeList([], [])
        if self._is_children_cache_stale():
            self._load_children()
        items = list(self._children_cache.values())
        names = [n._name or "" for n in items]
        return _NodeList(items, names)

    def _list_products(self) -> "_NodeList":
        if self._level != "workspace":
            return _NodeList([], [])
        if self._is_children_cache_stale():
            self._load_children()
        items = list(self._children_cache.values())
        names = [n._name or "" for n in items]
        return _NodeList(items, names)

    def _list_items(self) -> "_NodeList":
        if self._level not in ("product", "item", "version"):
            return _NodeList([], [])
        # If called on a product node, delegate to baseline (latest version)
        if self._level == "product":
            try:
                page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
                versions = getattr(page, "data", []) or []
                if versions:
                    latest_version = max(versions, key=lambda v: getattr(v, "version_number", 0))
                    version_number = getattr(latest_version, "version_number", None)
                    if version_number is not None:
                        # Create baseline version node and delegate to it
                        baseline_node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                        baseline_node._cache_ttl = self._cache_ttl
                        return baseline_node._list_items()
                # If no versions found, fall back to draft
                draft_node = _Node(self._client, "version", self, None, "draft")
                draft_node._cache_ttl = self._cache_ttl
                return draft_node._list_items()
            except Exception:
                # On error, fall back to draft
                draft_node = _Node(self._client, "version", self, None, "draft")
                draft_node._cache_ttl = self._cache_ttl
                return draft_node._list_items()
        if self._is_children_cache_stale():
            self._load_children()
        items = list(self._children_cache.values())
        names = [n._name or "" for n in items]
        return _NodeList(items, names)

    def _list_properties(self) -> "_NodeList":
        if self._level != "item":
            return _NodeList([], [])
        props = self._properties()
        wrappers: List[_PropWrapper] = []
        names: List[str] = []
        for i, pr in enumerate(props):
            display = pr.get("readableId") or pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
            names.append(str(display))
            wrappers.append(_PropWrapper(pr, client=self._client))
        return _NodeList(wrappers, names)

    def _get_property(self, readable_id: str) -> "_PropWrapper":
        """Get a property by its readableId from this product version.
        
        Searches for a property with the given readableId across all items
        in this product version. The readableId is unique within a product,
        so this will return the property regardless of which item it belongs to.
        
        When called on a product node, it uses the baseline (latest version)
        as the default.
        
        When called on an item node, it searches recursively through the item
        and all its sub-items to find the property.
        
        Args:
            readable_id: The readableId of the property to retrieve
                (e.g., "demo_property_mass").
        
        Returns:
            _PropWrapper: A wrapper object providing access to the property's
                value, category, unit, and other attributes.
        
        Raises:
            AttributeError: If called on a non-product, non-version, or non-item node.
            RuntimeError: If the property cannot be found or if there's an
                error querying the GraphQL API.
        """
        # If called on a product node, delegate to baseline (latest version)
        if self._level == "product":
            try:
                page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
                versions = getattr(page, "data", []) or []
                if versions:
                    latest_version = max(versions, key=lambda v: getattr(v, "version_number", 0))
                    version_number = getattr(latest_version, "version_number", None)
                    if version_number is not None:
                        # Create baseline version node and delegate to it
                        baseline_node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                        baseline_node._cache_ttl = self._cache_ttl
                        return baseline_node._get_property(readable_id)
                # If no versions found, fall back to draft
                draft_node = _Node(self._client, "version", self, None, "draft")
                draft_node._cache_ttl = self._cache_ttl
                return draft_node._get_property(readable_id)
            except Exception:
                # On error, fall back to draft
                draft_node = _Node(self._client, "version", self, None, "draft")
                draft_node._cache_ttl = self._cache_ttl
                return draft_node._get_property(readable_id)
        
        # If called on an item node, search recursively through the item and its sub-items
        if self._level == "item":
            return self._get_property_from_item_tree(readable_id)
        
        if self._level != "version":
            raise AttributeError("get_property() method is only available on product, version, and item nodes")
        
        # Get product_id from ancestor
        anc = self
        pid: Optional[str] = None
        while anc is not None:
            if anc._level == "product":
                pid = anc._id
                break
            anc = anc._parent  # type: ignore[assignment]
        
        if not pid:
            raise RuntimeError("Cannot determine product ID for version node")
        
        # Get version number (None for draft)
        version_number: Optional[int] = None
        if self._id is not None:
            try:
                version_number = int(self._id)
            except (TypeError, ValueError):
                version_number = None
        
        # Search for property by readableId
        # Since searchProperties doesn't return readableId, we need to iterate through items
        # and query their properties directly. Since readableId is unique per product,
        # we only need to find it once.
        
        # Get all items in this product version
        if version_number is not None:
            items = self._client.versions.list_items(
                product_id=pid,
                version_number=version_number,
                limit=1000,
                offset=0,
            )
        else:
            items = self._client.items.list_by_product(product_id=pid, limit=1000, offset=0)
        
        # Query properties for each item until we find the one with matching readableId
        for item in items:
            item_id = item.get("id")
            if not item_id:
                continue
            
            # Query properties for this item
            if version_number is not None:
                prop_query = (
                    "query($iid: ID!, $version: VersionInput!) {\n"
                    "  properties(itemId: $iid, version: $version) {\n"
                    "    __typename\n"
                    "    ... on NumericProperty { id name readableId category displayUnit value parsedValue }\n"
                    "    ... on TextProperty { id name readableId value parsedValue }\n"
                    "    ... on DateProperty { id name readableId value }\n"
                    "  }\n"
                    "}"
                )
                prop_variables = {
                    "iid": item_id,
                    "version": {"productId": pid, "versionNumber": version_number},
                }
            else:
                prop_query = (
                    "query($iid: ID!) {\n"
                    "  properties(itemId: $iid) {\n"
                    "    __typename\n"
                    "    ... on NumericProperty { id name readableId category displayUnit value parsedValue }\n"
                    "    ... on TextProperty { id name readableId value parsedValue }\n"
                    "    ... on DateProperty { id name readableId value }\n"
                    "  }\n"
                    "}"
                )
                prop_variables = {"iid": item_id}
            
            try:
                r = self._client._transport.graphql(prop_query, prop_variables)
                r.raise_for_status()
                data = r.json()
                if "errors" in data:
                    # Skip this item if there's an error
                    continue
                
                props = data.get("data", {}).get("properties", []) or []
                
                # Look for property with matching readableId
                for prop in props:
                    if prop.get("readableId") == readable_id:
                        return _PropWrapper(prop, client=self._client)
            except Exception:
                # Skip this item if there's an error
                continue
        
        # If not found, raise an error
        raise RuntimeError(
            f"Property with readableId '{readable_id}' not found in product version "
            f"{f'v{version_number}' if version_number is not None else 'draft'}"
        )
    
    def _get_property_from_item_tree(self, readable_id: str) -> "_PropWrapper":
        """Get a property by readableId from this item and all its sub-items recursively.
        
        Searches for a property with the given readableId starting from this item,
        then recursively searching through all sub-items.
        
        Args:
            readable_id: The readableId of the property to retrieve.
        
        Returns:
            _PropWrapper: A wrapper object providing access to the property's
                value, category, unit, and other attributes.
        
        Raises:
            RuntimeError: If the property cannot be found.
        """
        # Get product_id and version_number from ancestors
        anc = self
        pid: Optional[str] = None
        version_number: Optional[int] = None
        
        while anc is not None:
            if anc._level == "product":
                pid = anc._id
            elif anc._level == "version":
                if anc._id is not None:
                    try:
                        version_number = int(anc._id)
                    except (TypeError, ValueError):
                        version_number = None
                else:
                    version_number = None
            elif anc._level == "item":
                # Check if this item has a version_number attribute
                item_version = getattr(anc, "_version_number", None)
                if item_version is not None:
                    version_number = item_version
            anc = anc._parent  # type: ignore[assignment]
        
        if not pid:
            raise RuntimeError("Cannot determine product ID for item node")
        
        # Recursively search through this item and all sub-items
        return self._search_property_in_item_and_children(
            self._id, readable_id, pid, version_number
        )
    
    def _search_property_in_item_and_children(
        self, item_id: Optional[str], readable_id: str, product_id: str, version_number: Optional[int]
    ) -> "_PropWrapper":
        """Recursively search for a property in an item and all its children.
        
        Args:
            item_id: The ID of the item to search.
            readable_id: The readableId of the property to find.
            product_id: The product ID.
            version_number: Optional version number (None for draft).
        
        Returns:
            _PropWrapper: The found property.
        
        Raises:
            RuntimeError: If the property is not found.
        """
        if not item_id:
            raise RuntimeError(f"Property with readableId '{readable_id}' not found")
        
        # Query properties for this item
        if version_number is not None:
            prop_query = (
                "query($iid: ID!, $version: VersionInput!) {\n"
                "  properties(itemId: $iid, version: $version) {\n"
                "    __typename\n"
                "    ... on NumericProperty { id name readableId category displayUnit value parsedValue }\n"
                "    ... on TextProperty { id name readableId value parsedValue }\n"
                "    ... on DateProperty { id name readableId value }\n"
                "  }\n"
                "}"
            )
            prop_variables = {
                "iid": item_id,
                "version": {"productId": product_id, "versionNumber": version_number},
            }
        else:
            prop_query = (
                "query($iid: ID!) {\n"
                "  properties(itemId: $iid) {\n"
                "    __typename\n"
                "    ... on NumericProperty { id name readableId category displayUnit value parsedValue }\n"
                "    ... on TextProperty { id name readableId value parsedValue }\n"
                "    ... on DateProperty { id name readableId value }\n"
                "  }\n"
                "}"
            )
            prop_variables = {"iid": item_id}
        
        try:
            r = self._client._transport.graphql(prop_query, prop_variables)
            r.raise_for_status()
            data = r.json()
            if "errors" not in data:
                props = data.get("data", {}).get("properties", []) or []
                
                # Look for property with matching readableId in this item
                for prop in props:
                    if prop.get("readableId") == readable_id:
                        return _PropWrapper(prop)
        except Exception:
            pass  # Continue to search children
        
        # If not found in this item, search in children
        # Get child items
        if version_number is not None:
            # Get all items for this version and filter by parent
            all_items = self._client.versions.list_items(
                product_id=product_id,
                version_number=version_number,
                limit=1000,
                offset=0,
            )
            child_items = [it for it in all_items if it.get("parentId") == item_id]
        else:
            # Query for child items using GraphQL
            child_query = (
                "query($pid: ID!, $parent: ID!, $limit: Int!, $offset: Int!) {\n"
                "  items(productId: $pid, parentItemId: $parent, limit: $limit, offset: $offset) { id name readableId productId parentId owner position }\n"
                "}"
            )
            try:
                r = self._client._transport.graphql(
                    child_query, {"pid": product_id, "parent": item_id, "limit": 1000, "offset": 0}
                )
                r.raise_for_status()
                data = r.json()
                if "errors" in data:
                    raise RuntimeError(f"Property with readableId '{readable_id}' not found")
                child_items = data.get("data", {}).get("items", []) or []
            except Exception:
                raise RuntimeError(f"Property with readableId '{readable_id}' not found")
        
        # Recursively search in each child
        for child_item in child_items:
            child_id = child_item.get("id")
            if child_id:
                try:
                    return self._search_property_in_item_and_children(
                        child_id, readable_id, product_id, version_number
                    )
                except RuntimeError:
                    continue  # Try next child
        
        # If not found in this item or any children, raise error
        raise RuntimeError(f"Property with readableId '{readable_id}' not found in item tree")

    def _get_version_names(self) -> List[str]:
        """Get list of version names (v1, v2, etc.) for this product.
        
        Returns:
            List[str]: List of version names like ['v1', 'v2', 'v3', ...]
        """
        if self._level != "product":
            return []
        
        version_names: List[str] = []
        try:
            page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
            versions_data = getattr(page, "data", []) or []
            for v in versions_data:
                version_number = getattr(v, "version_number", None)
                if version_number is not None:
                    version_name = f"v{version_number}"
                    version_names.append(version_name)
        except Exception:
            pass  # If versions fail to load, return empty list
        
        return version_names

    def _list_product_versions(self) -> "_NodeList":
        """Return product versions as a list-like object with `.names`.

        Only meaningful for product-level nodes; other levels return an empty
        list. Includes a "draft" pseudo-version at the beginning for the current
        working state, followed by versioned snapshots (v1, v2, ...).
        """

        if self._level != "product":
            return _NodeList([], [])

        items = []
        names: List[str] = []

        # Add draft pseudo-version at the beginning
        draft_node = _Node(self._client, "version", self, None, "draft")
        draft_node._cache_ttl = self._cache_ttl
        items.append(draft_node)
        names.append("draft")

        # Add actual versioned snapshots from backend
        try:
            page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
            for v in getattr(page, "data", []) or []:
                version_number = getattr(v, "version_number", None)
                if version_number is None:
                    continue
                name = f"v{version_number}"
                node = _Node(self._client, "version", self, str(version_number), name)
                node._cache_ttl = self._cache_ttl
                items.append(node)
                names.append(name)
        except Exception:
            pass  # If versions fail to load, still return draft

        return _NodeList(items, names)

    def _get_version(self, version_name: str) -> "_Node":
        """Get a version node by its title/name.

        Only meaningful for product-level nodes. Searches through available
        versions to find one matching the given title/name.

        Args:
            version_name: The title or name of the version to retrieve
                (e.g., "version 1", "v1", or exact title match).

        Returns:
            _Node: A version node for the matching version.

        Raises:
            AttributeError: If called on a non-product node.
            ValueError: If no version matches the given name.
        """
        if self._level != "product":
            raise AttributeError("get_version() method is only available on product nodes")

        try:
            page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
            versions = getattr(page, "data", []) or []
            
            # Normalize the search term (case-insensitive, strip whitespace)
            search_term = version_name.strip().lower()
            
            # Try to find a match by title first
            for v in versions:
                title = getattr(v, "title", None)
                if title and title.strip().lower() == search_term:
                    version_number = getattr(v, "version_number", None)
                    if version_number is not None:
                        node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                        node._cache_ttl = self._cache_ttl
                        return node
            
            # If no exact title match, try partial match
            for v in versions:
                title = getattr(v, "title", None)
                if title and search_term in title.strip().lower():
                    version_number = getattr(v, "version_number", None)
                    if version_number is not None:
                        node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                        node._cache_ttl = self._cache_ttl
                        return node
            
            # If still no match, try matching version number format (e.g., "v1", "1")
            if search_term.startswith("v"):
                try:
                    version_num = int(search_term[1:])
                    for v in versions:
                        version_number = getattr(v, "version_number", None)
                        if version_number == version_num:
                            node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                            node._cache_ttl = self._cache_ttl
                            return node
                except ValueError:
                    pass
            else:
                # Try as direct version number
                try:
                    version_num = int(search_term)
                    for v in versions:
                        version_number = getattr(v, "version_number", None)
                        if version_number == version_num:
                            node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                            node._cache_ttl = self._cache_ttl
                            return node
                except ValueError:
                    pass
            
            # If no match found, raise an error
            available_titles = [getattr(v, "title", f"v{getattr(v, 'version_number', '?')}") for v in versions]
            raise ValueError(
                f"No version found matching '{version_name}'. "
                f"Available versions: {', '.join(available_titles)}"
            )
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            # On other errors, provide a helpful message
            raise ValueError(f"Error retrieving versions: {e}")

    def _suggest(self) -> List[str]:
        """Return suggested attribute names for interactive usage.

        Only child keys are returned; for item level, property keys are also included.
        """
        if self._is_children_cache_stale():
            self._load_children()
        suggestions: List[str] = list(self._children_cache.keys())
        if self._level == "item":
            suggestions.extend(list(self._props_key_map().keys()))
            suggestions.extend(["list_items", "list_properties", "get_property"])
        elif self._level == "product":
            # At product level, show items from baseline (latest version) + helper methods + version names
            suggestions.extend(["list_items", "list_product_versions", "baseline", "draft", "get_version", "get_property"])
            # Include version names (v1, v2, etc.) in autocomplete suggestions
            version_names = self._get_version_names()
            suggestions.extend(version_names)
        elif self._level == "version":
            suggestions.extend(["list_items", "get_property"])
        elif self._level == "workspace":
            suggestions.append("list_products")
        elif self._level == "root":
            suggestions.append("list_workspaces")
        return sorted(set(suggestions))

    def __getattr__(self, attr: str) -> Any:
        # No public properties/id/name/refresh
        if attr == "props":  # item-level properties pseudo-node
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
                # Return the latest version (highest version_number)
                try:
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
                node = _Node(self._client, "version", self, str(version_number), attr)
                node._cache_ttl = self._cache_ttl
                return node
            else:
                # For product nodes, default to latest version for item access
                # First check if it's a list helper - those should work on product directly
                if attr not in ("list_items", "list_product_versions"):
                    # Try to get latest version and redirect to it
                    try:
                        page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
                        versions = getattr(page, "data", []) or []
                        if versions:
                            latest_version = max(versions, key=lambda v: getattr(v, "version_number", 0))
                            version_number = getattr(latest_version, "version_number", None)
                            if version_number is not None:
                                # Create latest version node and try to get attr from it
                                latest_node = _Node(self._client, "version", self, str(version_number), f"v{version_number}")
                                latest_node._cache_ttl = self._cache_ttl
                                # Load children for latest version node
                                if latest_node._is_children_cache_stale():
                                    latest_node._load_children()
                                # Check if the attr exists in latest version's children
                                if attr in latest_node._children_cache:
                                    return latest_node._children_cache[attr]
                                # If not found in latest version, fall through to check draft/default cache
                    except Exception:
                        pass  # Fall through to default behavior (draft)
        
        if attr not in self._children_cache:
            if self._is_children_cache_stale():
                self._load_children()
        if attr in self._children_cache:
            child = self._children_cache[attr]
            # Track accessed items for deletion detection
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
                    pass  # Silently ignore tracking errors
            return child
        # Dynamically expose list helpers only where meaningful
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

        # Expose properties as direct attributes on item level
        if self._level == "item":
            pk = self._props_key_map()
            if attr in pk:
                prop_wrapper = pk[attr]
                # Track accessed properties for deletion detection
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
                        pass  # Silently ignore tracking errors
                return prop_wrapper
            
            # Check if property was previously accessed (deletion detection)
            if self._client is not None:
                try:
                    change_tracker = getattr(self._client, "_change_tracker", None)
                    if change_tracker is not None and change_tracker.is_enabled():
                        property_path = self._build_path(attr)
                        if property_path:
                            change_tracker.warn_if_deleted(property_path=property_path)
                except Exception:
                    pass  # Silently ignore tracking errors
        
        # Check if item was previously accessed (deletion detection)
        if self._client is not None:
            try:
                change_tracker = getattr(self._client, "_change_tracker", None)
                if change_tracker is not None and change_tracker.is_enabled():
                    item_path = self._build_path(attr)
                    if item_path:
                        change_tracker.warn_if_deleted(item_path=item_path)
            except Exception:
                pass  # Silently ignore tracking errors
        
        raise AttributeError(attr)

    def __getitem__(self, key: str) -> "_Node":
        """Access child by display name or a safe attribute key.

        This enables names with spaces or symbols: browser["Workspace Name"].
        """
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

    def _properties(self) -> List[Dict[str, Any]]:
        if not self._is_props_cache_stale():
            return self._props_cache or []
        if self._level != "item":
            self._props_cache = []
            self._props_loaded_at = time.time()
            return self._props_cache
        
        # Get version context if available
        version_number = getattr(self, "_version_number", None)
        # Get product_id from ancestor
        anc = self
        pid: Optional[str] = None
        while anc is not None:
            if anc._level == "product":
                pid = anc._id
                break
            anc = anc._parent  # type: ignore[assignment]
        
        # Check if change detection is enabled - if so, use sdkProperties to get updatedAt/updatedBy
        use_sdk_properties = False
        try:
            change_tracker = getattr(self._client, "_change_tracker", None)
            if change_tracker is not None and change_tracker.is_enabled():
                use_sdk_properties = True
        except Exception:
            pass  # Silently ignore errors
        
        # Try direct properties(itemId: ...) or sdkProperties(...) first; fallback to searchProperties
        # Attempt 1: query with parsedValue support and version if available
        query_name = "sdkProperties" if use_sdk_properties else "properties"
        property_type_prefix = "Sdk" if use_sdk_properties else ""
        
        if version_number is not None and pid is not None:
            # Note: sdkProperties may not support version parameter yet, but we try it
            updated_fields = " updatedAt updatedBy" if use_sdk_properties else ""
            q_parsed = (
                f"query($iid: ID!, $version: VersionInput!) {{\n"
                f"  {query_name}(itemId: $iid, version: $version) {{\n"
                f"    __typename\n"
                f"    ... on {property_type_prefix}NumericProperty {{ id name readableId category displayUnit value parsedValue{updated_fields} }}\n"
                f"    ... on {property_type_prefix}TextProperty {{ id name readableId value parsedValue{updated_fields} }}\n"
                f"    ... on {property_type_prefix}DateProperty {{ id name readableId value{updated_fields} }}\n"
                f"  }}\n"
                f"}}"
            )
            variables = {"iid": self._id, "version": {"productId": pid, "versionNumber": version_number}}
        else:
            updated_fields = " updatedAt updatedBy" if use_sdk_properties else ""
            q_parsed = (
                f"query($iid: ID!) {{\n"
                f"  {query_name}(itemId: $iid) {{\n"
                f"    __typename\n"
                f"    ... on {property_type_prefix}NumericProperty {{ id name readableId category displayUnit value parsedValue{updated_fields} }}\n"
                f"    ... on {property_type_prefix}TextProperty {{ id name readableId value parsedValue{updated_fields} }}\n"
                f"    ... on {property_type_prefix}DateProperty {{ id name readableId value{updated_fields} }}\n"
                f"  }}\n"
                f"}}"
            )
            variables = {"iid": self._id}
        try:
            r = self._client._transport.graphql(q_parsed, variables)
            r.raise_for_status()
            data = r.json()
            if "errors" in data:
                # If sdkProperties query fails, fall back to regular properties query
                if use_sdk_properties:
                    # sdkProperties might not be available or might not support version parameter
                    # Fall through to try regular properties query
                    pass
                else:
                    # If versioned query fails, check if it's a version-related error
                    errors = data["errors"]
                    if version_number is not None:
                        error_msg = str(errors)
                        # Check if the error suggests version isn't supported
                        if "version" in error_msg.lower() and ("unknown" in error_msg.lower() or "cannot" in error_msg.lower()):
                            # Properties API likely doesn't support version parameter yet
                            # Fall through to try without version, but this means we'll get draft properties
                            # TODO: Backend needs to add version support to properties API
                            pass
                        else:
                            raise RuntimeError(data["errors"])  # Other errors should be raised
                    else:
                        raise RuntimeError(data["errors"])  # Draft queries should raise on error
            else:
                # Handle both properties and sdkProperties responses
                props_data = data.get("data", {}).get(query_name, []) or []
                self._props_cache = props_data
                self._props_loaded_at = time.time()
                return self._props_cache  # Return early if successful
        except RuntimeError:
            if not use_sdk_properties:
                raise  # Re-raise RuntimeErrors for regular properties queries
            # For sdkProperties, fall through to try regular properties query
        except Exception:
            if not use_sdk_properties:
                raise  # Re-raise other exceptions for regular properties queries
            # For sdkProperties, fall through to try regular properties query
        
        # If sdkProperties failed, try regular properties query as fallback
        if use_sdk_properties:
            try:
                # Fallback to regular properties query (sdkProperties might not be available or might not support version)
                if version_number is not None and pid is not None:
                    q_value_only = (
                        "query($iid: ID!, $version: VersionInput!) {\n"
                        "  properties(itemId: $iid, version: $version) {\n"
                        "    __typename\n"
                        "    ... on NumericProperty { id name readableId category displayUnit value }\n"
                        "    ... on TextProperty { id name readableId value }\n"
                        "    ... on DateProperty { id name readableId value }\n"
                        "  }\n"
                        "}"
                    )
                    variables = {"iid": self._id, "version": {"productId": pid, "versionNumber": version_number}}
                else:
                    q_value_only = (
                        "query($iid: ID!) {\n"
                        "  properties(itemId: $iid) {\n"
                        "    __typename\n"
                        "    ... on NumericProperty { id name readableId category displayUnit value }\n"
                        "    ... on TextProperty { id name readableId value }\n"
                        "    ... on DateProperty { id name readableId value }\n"
                        "  }\n"
                        "}"
                    )
                    variables = {"iid": self._id}
                try:
                    r = self._client._transport.graphql(q_value_only, variables)
                    r.raise_for_status()
                    data = r.json()
                    if "errors" in data:
                        # If versioned query fails, check if it's a version-related error
                        errors = data["errors"]
                        if version_number is not None:
                            error_msg = str(errors)
                            # Check if the error suggests version isn't supported
                            if "version" in error_msg.lower() and ("unknown" in error_msg.lower() or "cannot" in error_msg.lower()):
                                # Properties API likely doesn't support version parameter yet
                                # Fall through to try without version, but this means we'll get draft properties
                                pass
                            else:
                                raise RuntimeError(data["errors"])  # Other errors should be raised
                        else:
                            raise RuntimeError(data["errors"])  # Draft queries should raise on error
                    self._props_cache = data.get("data", {}).get("properties", []) or []
                    self._props_loaded_at = time.time()
                    return self._props_cache
                except RuntimeError:
                    raise  # Re-raise RuntimeErrors
                except Exception:
                    # If all else fails, try searchProperties as last resort
                    pass
            except Exception:
                # If fallback also fails, continue to searchProperties
                pass
        
        # Attempt 3: searchProperties as last resort (doesn't support version or updatedAt/updatedBy)
        try:
            # Fallback to searchProperties
            q2_parsed = (
                "query($iid: ID!, $limit: Int!, $offset: Int!) {\n"
                "  searchProperties(q: \"*\", itemId: $iid, limit: $limit, offset: $offset) {\n"
                "    hits { id workspaceId productId itemId propertyType name readableId category displayUnit value parsedValue owner }\n"
                "  }\n"
                "}"
            )
            try:
                r2 = self._client._transport.graphql(q2_parsed, {"iid": self._id, "limit": 100, "offset": 0})
                r2.raise_for_status()
                data2 = r2.json()
                if "errors" in data2:
                    raise RuntimeError(data2["errors"])  # try minimal
                self._props_cache = data2.get("data", {}).get("searchProperties", {}).get("hits", []) or []
                self._props_loaded_at = time.time()
            except Exception:
                q2_min = (
                    "query($iid: ID!, $limit: Int!, $offset: Int!) {\n"
                    "  searchProperties(q: \"*\", itemId: $iid, limit: $limit, offset: $offset) {\n"
                    "    hits { id workspaceId productId itemId propertyType name readableId category displayUnit value owner }\n"
                    "  }\n"
                    "}"
                )
                r3 = self._client._transport.graphql(q2_min, {"iid": self._id, "limit": 100, "offset": 0})
                r3.raise_for_status()
                data3 = r3.json()
                if "errors" in data3:
                    raise RuntimeError(data3["errors"])  # propagate
                self._props_cache = data3.get("data", {}).get("searchProperties", {}).get("hits", []) or []
                self._props_loaded_at = time.time()
        except Exception:
            # If all queries fail, return empty list
            self._props_cache = []
            self._props_loaded_at = time.time()
        return self._props_cache

    def _props_key_map(self) -> Dict[str, Dict[str, Any]]:
        """Map safe keys to property wrappers for item-level attribute access."""
        out: Dict[str, Dict[str, Any]] = {}
        if self._level != "item":
            return out
        props = self._properties()
        used_names: Dict[str, int] = {}
        for i, pr in enumerate(props):
            # Try to get name from various possible fields
            display = pr.get("readableId") or pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
            safe = _safe_key(str(display))
            
            # Handle duplicate names by adding a suffix
            if safe in used_names:
                used_names[safe] += 1
                safe = f"{safe}_{used_names[safe]}"
            else:
                used_names[safe] = 0
                
            out[safe] = _PropWrapper(pr, client=self._client)
        return out

    def _load_children(self) -> None:
        if self._level == "root":
            rows = self._client.workspaces.list(limit=200, offset=0)
            for w in rows:
                display = w.get("readableId") or w.get("name") or str(w.get("id"))
                nm = _safe_key(display)
                child = _Node(self._client, "workspace", self, w["id"], display)
                child._cache_ttl = self._cache_ttl
                self._children_cache[nm] = child
        elif self._level == "workspace":
            page = self._client.products.list_by_workspace(workspace_id=self._id, limit=200, offset=0)
            for p in page.data:
                display = p.readableId or p.name or str(p.id)
                nm = _safe_key(display)
                child = _Node(self._client, "product", self, p.id, display)
                child._cache_ttl = self._cache_ttl
                self._children_cache[nm] = child
        elif self._level == "product":
            # Load items from baseline (latest version) for autocomplete suggestions
            # This ensures ws.demo_product. shows items from the latest version, not draft
            # Clear cache first to ensure we always load fresh data from baseline
            self._children_cache.clear()
            
            try:
                page = self._client.products.list_product_versions(product_id=self._id, limit=100, offset=0)
                versions = getattr(page, "data", []) or []
                if versions:
                    # Get the latest version (highest version_number)
                    latest_version = max(versions, key=lambda v: getattr(v, "version_number", 0))
                    version_number = getattr(latest_version, "version_number", None)
                    if version_number is not None:
                        # Load items from the latest version
                        rows = self._client.versions.list_items(
                            product_id=self._id,
                            version_number=version_number,
                            limit=1000,
                            offset=0,
                        )
                        for it in rows:
                            if it.get("parentId") is None:
                                display = it.get("readableId") or it.get("name") or str(it["id"])
                                nm = _safe_key(display)
                                child = _Node(self._client, "item", self, it["id"], display, version_number=version_number)
                                child._cache_ttl = self._cache_ttl
                                self._children_cache[nm] = child
                        # Mark cache as fresh after successful baseline load
                        self._children_loaded_at = time.time()
                        return  # Successfully loaded baseline items
            except (AttributeError, KeyError, TypeError, ValueError):
                # Only catch specific exceptions that might occur during data access
                pass  # Fall through to draft if baseline loading fails
            except Exception:
                # For other exceptions (like network errors), still fall through to draft
                pass
            
            # Fallback: load draft items if no versions exist or baseline loading failed
            # Only load draft if we haven't already loaded baseline items
            if not self._children_cache:
                rows = self._client.items.list_by_product(product_id=self._id, limit=1000, offset=0)
                for it in rows:
                    if it.get("parentId") is None:
                        display = it.get("readableId") or it.get("name") or str(it["id"])
                        nm = _safe_key(display)
                        child = _Node(self._client, "item", self, it["id"], display)
                        child._cache_ttl = self._cache_ttl
                        self._children_cache[nm] = child
        elif self._level == "version":
            # Fetch top-level items for this specific product version (or draft if version_number is None).
            anc = self
            pid: Optional[str] = None
            while anc is not None:
                if anc._level == "product":
                    pid = anc._id
                    break
                anc = anc._parent  # type: ignore[assignment]
            if not pid:
                return
            try:
                version_number = int(self._id) if self._id is not None else None
            except (TypeError, ValueError):
                version_number = None
            
            if version_number is None:
                # Draft: load items without version number
                rows = self._client.items.list_by_product(product_id=pid, limit=1000, offset=0)
            else:
                # Versioned: load items for specific version
                rows = self._client.versions.list_items(
                    product_id=pid,
                    version_number=version_number,
                    limit=1000,
                    offset=0,
                )
            
            for it in rows:
                if it.get("parentId") is None:
                    display = it.get("readableId") or it.get("name") or str(it["id"])
                    nm = _safe_key(display)
                    child = _Node(self._client, "item", self, it["id"], display, version_number=version_number)
                    child._cache_ttl = self._cache_ttl
                    self._children_cache[nm] = child
        elif self._level == "item":
            # Fetch children items by parent; derive productId from ancestor product
            anc = self
            pid: Optional[str] = None
            while anc is not None:
                if anc._level == "product":
                    pid = anc._id
                    break
                anc = anc._parent  # type: ignore[assignment]
            if not pid:
                return
            
            # Use version context if this item came from a version
            version_number = getattr(self, "_version_number", None)
            
            if version_number is not None:
                # Load child items from versioned API
                all_items = self._client.versions.list_items(
                    product_id=pid,
                    version_number=version_number,
                    limit=1000,
                    offset=0,
                )
                # Filter to children of this item
                rows = [it for it in all_items if it.get("parentId") == self._id]
            else:
                # Draft: use regular items query
                q = (
                    "query($pid: ID!, $parent: ID!, $limit: Int!, $offset: Int!) {\n"
                    "  items(productId: $pid, parentItemId: $parent, limit: $limit, offset: $offset) { id name readableId productId parentId owner position }\n"
                    "}"
                )
                r = self._client._transport.graphql(q, {"pid": pid, "parent": self._id, "limit": 1000, "offset": 0})
                r.raise_for_status()
                data = r.json()
                if "errors" in data:
                    raise RuntimeError(data["errors"])  # surface
                rows = data.get("data", {}).get("items", []) or []
            
            for it2 in rows:
                # Skip the current item (GraphQL returns parent + direct children)
                if str(it2.get("id")) == str(self._id):
                    continue
                display = it2.get("readableId") or it2.get("name") or str(it2["id"]) 
                nm = _safe_key(display)
                child = _Node(self._client, "item", self, it2["id"], display, version_number=version_number)
                child._cache_ttl = self._cache_ttl
                self._children_cache[nm] = child
        
        # Mark cache as fresh
        self._children_loaded_at = time.time()


class Browser:
    """Public browser entrypoint."""

    def __init__(self, client: Any, cache_ttl: float = 30.0) -> None:
        """Initialize browser with optional cache TTL.
        
        Args:
            client: PoelisClient instance
            cache_ttl: Cache time-to-live in seconds (default: 30)
        """
        self._root = _Node(client, "root", None, None, None)
        # Set cache TTL for all nodes
        self._root._cache_ttl = cache_ttl
        # Best-effort: auto-enable curated completion in interactive shells
        global _AUTO_COMPLETER_INSTALLED
        if not _AUTO_COMPLETER_INSTALLED:
            try:
                if enable_dynamic_completion():
                    _AUTO_COMPLETER_INSTALLED = True
            except Exception:
                # Non-interactive or IPython not available; ignore silently
                pass

    def __getattr__(self, attr: str) -> Any:  # pragma: no cover - notebook UX
        return getattr(self._root, attr)

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        org_context = get_organization_context_message(None)
        return f"<browser root> ({org_context})"

    def __getitem__(self, key: str) -> Any:  # pragma: no cover - notebook UX
        """Delegate index-based access to the root node so names work: browser["Workspace Name"]."""
        return self._root[key]

    def __dir__(self) -> list[str]:  # pragma: no cover - notebook UX
        # Performance optimization: only load children if cache is stale or empty
        if self._root._is_children_cache_stale():
            self._root._load_children()
        keys = [*self._root._children_cache.keys(), "list_workspaces"]
        return sorted(keys)

    def _names(self) -> List[str]:
        """Return display names of root-level children (workspaces)."""
        return self._root._names()

    # keep suggest internal so it doesn't appear in help/dir
    def _suggest(self) -> List[str]:
        sugg = list(self._root._suggest())
        sugg.append("list_workspaces")
        return sorted(set(sugg))

    # suggest() removed from public API; dynamic completion still uses internal _suggest

    def list_workspaces(self) -> "_NodeList":
        """Return workspaces as a list-like object with `.names`."""
        return self._root._list_workspaces()


def _safe_key(name: str) -> str:
    """Convert arbitrary display name to a safe attribute key (letters/digits/_)."""
    key = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    key = key.strip("_")
    return key or "_"


class _PropsNode:
    """Pseudo-node that exposes item properties as child attributes by display name.

    Usage: item.props.<Property_Name> or item.props["Property Name"].
    Returns the raw property dictionaries from GraphQL.
    """

    def __init__(self, item_node: _Node) -> None:
        self._item = item_node
        self._children_cache: Dict[str, _PropWrapper] = {}
        self._names: List[str] = []
        self._loaded_at: Optional[float] = None
        self._cache_ttl: float = item_node._cache_ttl  # Inherit cache TTL from parent node

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        return f"<props of {self._item.name or self._item.id}>"

    def _ensure_loaded(self) -> None:
        # Performance optimization: only load if cache is stale or empty
        if self._children_cache and self._loaded_at is not None:
            if time.time() - self._loaded_at <= self._cache_ttl:
                return
        
        props = self._item._properties()
        used_names: Dict[str, int] = {}
        names_list = []
        for i, pr in enumerate(props):
            # Try to get name from various possible fields
            display = pr.get("readableId") or pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
            safe = _safe_key(str(display))
            
            # Handle duplicate names by adding a suffix
            if safe in used_names:
                used_names[safe] += 1
                safe = f"{safe}_{used_names[safe]}"
            else:
                used_names[safe] = 0
                
            self._children_cache[safe] = _PropWrapper(pr, client=self._item._client)
            names_list.append(display)
        self._names = names_list
        self._loaded_at = time.time()

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        self._ensure_loaded()
        return sorted(list(self._children_cache.keys())) 

    # names() removed; use item.list_properties().names instead

    def __getattr__(self, attr: str) -> Any:
        self._ensure_loaded()
        if attr in self._children_cache:
            prop_wrapper = self._children_cache[attr]
            # Track accessed properties for deletion detection
            if self._item._client is not None:
                try:
                    change_tracker = getattr(self._item._client, "_change_tracker", None)
                    if change_tracker is not None and change_tracker.is_enabled():
                        property_path = self._item._build_path(attr)
                        if property_path:
                            prop_name = (
                                getattr(prop_wrapper, "_raw", {}).get("readableId")
                                or getattr(prop_wrapper, "_raw", {}).get("name")
                                or attr
                            )
                            prop_id = getattr(prop_wrapper, "_raw", {}).get("id")
                            change_tracker.record_accessed_property(property_path, prop_name, prop_id)
                except Exception:
                    pass  # Silently ignore tracking errors
            return prop_wrapper
        
        # Check if property was previously accessed (deletion detection)
        if self._item._client is not None:
            try:
                change_tracker = getattr(self._item._client, "_change_tracker", None)
                if change_tracker is not None and change_tracker.is_enabled():
                    property_path = self._item._build_path(attr)
                    if property_path:
                        change_tracker.warn_if_deleted(property_path=property_path)
            except Exception:
                pass  # Silently ignore tracking errors
        
        raise AttributeError(attr)

    def __getitem__(self, key: str) -> Any:
        self._ensure_loaded()
        if key in self._children_cache:
            return self._children_cache[key]
        # match by display name
        for safe, data in self._children_cache.items():
            try:
                raw = getattr(data, "_raw", {})
                if raw.get("readableId") == key or raw.get("name") == key:  # type: ignore[arg-type]
                    return data
            except Exception:
                continue
        safe = _safe_key(key)
        if safe in self._children_cache:
            return self._children_cache[safe]
        raise KeyError(key)

    # keep suggest internal so it doesn't appear in help/dir
    def _suggest(self) -> List[str]:
        self._ensure_loaded()
        return sorted(list(self._children_cache.keys()))


class _NodeList:
    """Lightweight sequence wrapper for node/property lists with `.names`.

    Provides iteration and index access to underlying items, plus a `.names`
    attribute returning the display names in the same order.
    """

    def __init__(self, items: List[Any], names: List[str]) -> None:
        self._items = list(items)
        self._names = list(names)

    def __iter__(self):  # pragma: no cover - trivial
        return iter(self._items)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._items)

    def __getitem__(self, idx: int) -> Any:  # pragma: no cover - trivial
        return self._items[idx]

    @property
    def names(self) -> List[str]:
        return list(self._names)


class _PropWrapper:
    """Lightweight accessor for a property dict, exposing `.value` and `.raw`.

    Normalizes different property result shapes (union vs search) into `.value`.
    """

    def __init__(self, prop: Dict[str, Any], client: Any = None) -> None:
        """Initialize property wrapper.

        Args:
            prop: Property dictionary from GraphQL.
            client: Optional PoelisClient instance for change tracking.
        """
        self._raw = prop
        self._client = client

    def _get_property_value(self) -> Any:
        """Extract and parse the property value from raw data.

        Returns:
            Any: The parsed property value.
        """
        p = self._raw
        # Use parsedValue if available and not None (new backend feature)
        if "parsedValue" in p:
            parsed_val = p.get("parsedValue")
            if parsed_val is not None:
                # Recursively parse arrays/matrices that might contain string numbers
                return self._parse_nested_value(parsed_val)
        # Fallback to legacy parsing logic for backward compatibility
        # searchProperties shape
        if "numericValue" in p and p.get("numericValue") is not None:
            return p["numericValue"]
        if "textValue" in p and p.get("textValue") is not None:
            return p["textValue"]
        if "dateValue" in p and p.get("dateValue") is not None:
            return p["dateValue"]
        # union shape
        if "integerPart" in p:
            integer_part = p.get("integerPart")
            exponent = p.get("exponent", 0) or 0
            try:
                return (integer_part or 0) * (10 ** int(exponent))
            except Exception:
                return integer_part
        # If parsedValue was None or missing, try to parse the raw value for numeric properties
        if "value" in p:
            raw_value = p.get("value")
            # Check if this is a numeric property and try to parse the string
            property_type = (p.get("__typename") or p.get("propertyType") or "").lower()
            is_numeric = property_type in ("numericproperty", "numeric")
            # If it's a numeric property, try to parse the string as a number
            if isinstance(raw_value, str) and is_numeric:
                try:
                    # Try to parse as float first (handles decimals), then int
                    parsed = float(raw_value)
                    # Return int if it's a whole number, otherwise float
                    return int(parsed) if parsed.is_integer() else parsed
                except (ValueError, TypeError):
                    # If parsing fails, return the raw string
                    return raw_value
            return raw_value
        return None

    @property
    def value(self) -> Any:  # type: ignore[override]
        """Get the property value, with change detection if enabled.

        Returns:
            Any: The property value.
        """
        current_value = self._get_property_value()

        # Check for changes if client is available and change detection is enabled
        if self._client is not None:
            try:
                change_tracker = getattr(self._client, "_change_tracker", None)
                if change_tracker is not None and change_tracker.is_enabled():
                    # Skip tracking for versioned properties (they're immutable)
                    # Versioned properties have productVersionNumber set
                    if self._raw.get("productVersionNumber") is not None:
                        return current_value
                    
                    # Get property ID for tracking
                    property_id = self._raw.get("id")
                    if property_id:
                        # Get property name for warning message
                        prop_name = (
                            self._raw.get("readableId")
                            or self._raw.get("name")
                            or self._raw.get("id")
                        )
                        # Get updatedAt and updatedBy if available (from sdkProperties)
                        updated_at = self._raw.get("updatedAt")
                        updated_by = self._raw.get("updatedBy")
                        # Check and warn if changed
                        change_tracker.warn_if_changed(
                            property_id, current_value, name=prop_name,
                            updated_at=updated_at, updated_by=updated_by
                        )
            except Exception:
                # Silently ignore errors in change tracking to avoid breaking property access
                pass

        return current_value
    
    def _parse_nested_value(self, value: Any) -> Any:
        """Recursively parse nested lists/arrays that might contain string numbers."""
        if isinstance(value, list):
            return [self._parse_nested_value(item) for item in value]
        elif isinstance(value, str):
            # Try to parse string as number if it looks numeric
            if self._looks_like_number(value):
                try:
                    parsed = float(value)
                    return int(parsed) if parsed.is_integer() else parsed
                except (ValueError, TypeError):
                    return value
            return value
        else:
            # Already a number or other type, return as-is
            return value
    
    def _looks_like_number(self, value: str) -> bool:
        """Check if a string value looks like a numeric value."""
        if not isinstance(value, str):
            return False
        value = value.strip()
        if not value:
            return False
        # Allow optional leading sign, digits, optional decimal point, optional exponent
        # This matches patterns like: "123", "-45.67", "1.23e-4", "+100"
        try:
            float(value)
            return True
        except ValueError:
            return False

    @property
    def category(self) -> Optional[str]:
        """Return the category for this property.
        
        Note: Category values are normalized/canonicalized by the backend.
        Values may be upper-cased and some previously distinct categories
        may have been merged into canonical forms.
        
        Returns:
            Optional[str]: The category string, or None if not available.
        """
        p = self._raw
        cat = p.get("category")
        return str(cat) if cat is not None else None

    @property
    def unit(self) -> Optional[str]:
        """Return the display unit for this property.

        Returns:
            Optional[str]: The unit string (e.g., "kg", "°C"), or None if not available.
        """
        p = self._raw
        unit = p.get("displayUnit") or p.get("display_unit")
        return str(unit) if unit is not None else None

    @property
    def name(self) -> Optional[str]:
        """Return the best-effort display name for this property.

        Falls back to name, id, or category when readableId is not present.
        """
        p = self._raw
        n = p.get("readableId") or p.get("name") or p.get("id") or p.get("category")
        return str(n) if n is not None else None

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        # Expose only the minimal attributes for browsing
        return ["value", "category", "unit"]

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        name = self._raw.get("readableId") or self._raw.get("name") or self._raw.get("id")
        return f"<property {name}: {self.value}>"

    def __str__(self) -> str:  # pragma: no cover - notebook UX
        """Return the display name for this property for string conversion.

        This allows printing a property object directly (e.g., ``print(prop)``)
        and seeing its human-friendly name instead of the full representation.

        Returns:
            str: The best-effort display name, or an empty string if unknown.
        """
        return self.name or ""



def enable_dynamic_completion() -> bool:
    """Enable dynamic attribute completion in IPython/Jupyter environments.

    This helper attempts to configure IPython to use runtime-based completion
    (disabling Jedi) so that our dynamic `__dir__` and `suggest()` methods are
    respected by TAB completion. Returns True if an interactive shell was found
    and configured, False otherwise.
    """

    try:
        # Deferred import to avoid hard dependency
        from IPython import get_ipython  # type: ignore
    except Exception:
        return False

    ip = None
    try:
        ip = get_ipython()  # type: ignore[assignment]
    except Exception:
        ip = None
    if ip is None:
        return False

    enabled = False
    # Best-effort configuration: rely on IPython's fallback (non-Jedi) completer
    try:
        if hasattr(ip, "Completer") and hasattr(ip.Completer, "use_jedi"):
            # Disable Jedi to let IPython consult __dir__ dynamically
            ip.Completer.use_jedi = False  # type: ignore[assignment]
            # Greedy completion improves attribute completion depth
            if hasattr(ip.Completer, "greedy"):
                ip.Completer.greedy = True  # type: ignore[assignment]
            enabled = True
    except Exception:
        pass

    # Additionally, install a lightweight attribute completer that uses suggest()
    try:
        comp = getattr(ip, "Completer", None)
        if comp is not None and hasattr(comp, "attr_matches"):
            orig_attr_matches = comp.attr_matches  # type: ignore[attr-defined]

            def _poelis_attr_matches(self: Any, text: str) -> List[str]:  # pragma: no cover - interactive behavior
                try:
                    # text is like "client.browser.uh2.pr" → split at last dot
                    obj_expr, _, prefix = text.rpartition(".")
                    if not obj_expr:
                        return orig_attr_matches(text)  # type: ignore[operator]
                    # Evaluate the object in the user namespace
                    ns = getattr(self, "namespace", {})
                    obj_val = eval(obj_expr, ns, ns)

                    # For Poelis browser objects, show ONLY our curated suggestions
                    from_types = (Browser, _Node, _PropsNode, _PropWrapper)
                    if isinstance(obj_val, from_types):
                        # Build suggestion list
                        if isinstance(obj_val, _PropWrapper):
                            sugg: List[str] = ["value", "category", "unit"]
                        elif hasattr(obj_val, "_suggest"):
                            sugg = list(getattr(obj_val, "_suggest")())  # type: ignore[no-untyped-call]
                        else:
                            sugg = list(dir(obj_val))
                        # Filter by prefix and format matches as full attribute paths
                        out: List[str] = []
                        for s in sugg:
                            if not prefix or str(s).startswith(prefix):
                                out.append(f"{obj_expr}.{s}")
                        return out

                    # Otherwise, fall back to default behavior
                    return orig_attr_matches(text)  # type: ignore[operator]
                except Exception:
                    # fall back to original on any error
                    return orig_attr_matches(text)  # type: ignore[operator]

            comp.attr_matches = MethodType(_poelis_attr_matches, comp)  # type: ignore[assignment]
            enabled = True
    except Exception:
        pass

    # Also register as a high-priority matcher in IPCompleter.matchers
    try:
        comp = getattr(ip, "Completer", None)
        if comp is not None and hasattr(comp, "matchers") and not getattr(comp, "_poelis_matcher_installed", False):
            orig_attr_matches = comp.attr_matches  # type: ignore[attr-defined]

            def _poelis_matcher(self: Any, text: str) -> List[str]:  # pragma: no cover - interactive behavior
                # Delegate to our attribute logic for dotted expressions; otherwise empty
                if "." in text:
                    try:
                        return self.attr_matches(text)  # type: ignore[operator]
                    except Exception:
                        return orig_attr_matches(text)  # type: ignore[operator]
                return []

            # Prepend our matcher so it's consulted early
            comp.matchers.insert(0, MethodType(_poelis_matcher, comp))  # type: ignore[arg-type]
            setattr(comp, "_poelis_matcher_installed", True)
            enabled = True
    except Exception:
        pass

    return bool(enabled)

