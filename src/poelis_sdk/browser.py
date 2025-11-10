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
    def __init__(self, client: Any, level: str, parent: Optional["_Node"], node_id: Optional[str], name: Optional[str]) -> None:
        self._client = client
        self._level = level
        self._parent = parent
        self._id = node_id
        self._name = name
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
            keys.extend(["list_items", "list_properties"])
        elif self._level == "product":
            keys.append("list_items")
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
                display = pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
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
        if self._level not in ("product", "item"):
            return _NodeList([], [])
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
            display = pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
            names.append(str(display))
            wrappers.append(_PropWrapper(pr))
        return _NodeList(wrappers, names)

    def _suggest(self) -> List[str]:
        """Return suggested attribute names for interactive usage.

        Only child keys are returned; for item level, property keys are also included.
        """
        if self._is_children_cache_stale():
            self._load_children()
        suggestions: List[str] = list(self._children_cache.keys())
        if self._level == "item":
            suggestions.extend(list(self._props_key_map().keys()))
            suggestions.extend(["list_items", "list_properties"])
        elif self._level == "product":
            suggestions.append("list_items")
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
        if attr not in self._children_cache:
            if self._is_children_cache_stale():
                self._load_children()
        if attr in self._children_cache:
            return self._children_cache[attr]
        # Dynamically expose list helpers only where meaningful
        if attr == "list_workspaces":
            if self._level == "root":
                return MethodType(_Node._list_workspaces, self)
            raise AttributeError(attr)
        if attr == "list_products":
            if self._level == "workspace":
                return MethodType(_Node._list_products, self)
            raise AttributeError(attr)
        if attr == "list_items":
            if self._level in ("product", "item"):
                return MethodType(_Node._list_items, self)
            raise AttributeError(attr)
        if attr == "list_properties":
            if self._level == "item":
                return MethodType(_Node._list_properties, self)
            raise AttributeError(attr)

        # Expose properties as direct attributes on item level
        if self._level == "item":
            pk = self._props_key_map()
            if attr in pk:
                return pk[attr]
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
        # Try direct properties(itemId: ...) first; fallback to searchProperties
        # Attempt 1: query with parsedValue support
        q_parsed = (
            "query($iid: ID!) {\n"
            "  properties(itemId: $iid) {\n"
            "    __typename\n"
            "    ... on NumericProperty { id name category displayUnit value parsedValue }\n"
            "    ... on TextProperty { id name value parsedValue }\n"
            "    ... on DateProperty { id name value }\n"
            "  }\n"
            "}"
        )
        try:
            r = self._client._transport.graphql(q_parsed, {"iid": self._id})
            r.raise_for_status()
            data = r.json()
            if "errors" in data:
                raise RuntimeError(data["errors"])  # try value-only shape
            self._props_cache = data.get("data", {}).get("properties", []) or []
            self._props_loaded_at = time.time()
        except Exception:
            # Attempt 2: value-only, legacy compatible
            q_value_only = (
                "query($iid: ID!) {\n"
                "  properties(itemId: $iid) {\n"
                "    __typename\n"
                "    ... on NumericProperty { id name category displayUnit value }\n"
                "    ... on TextProperty { id name value }\n"
                "    ... on DateProperty { id name value }\n"
                "  }\n"
                "}"
            )
            try:
                r = self._client._transport.graphql(q_value_only, {"iid": self._id})
                r.raise_for_status()
                data = r.json()
                if "errors" in data:
                    raise RuntimeError(data["errors"])  # trigger fallback to search
                self._props_cache = data.get("data", {}).get("properties", []) or []
                self._props_loaded_at = time.time()
            except Exception:
                # Fallback to searchProperties
                q2_parsed = (
                    "query($iid: ID!, $limit: Int!, $offset: Int!) {\n"
                    "  searchProperties(q: \"*\", itemId: $iid, limit: $limit, offset: $offset) {\n"
                    "    hits { id workspaceId productId itemId propertyType name category displayUnit value parsedValue owner }\n"
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
                        "    hits { id workspaceId productId itemId propertyType name category displayUnit value owner }\n"
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
            display = pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
            safe = _safe_key(str(display))
            
            # Handle duplicate names by adding a suffix
            if safe in used_names:
                used_names[safe] += 1
                safe = f"{safe}_{used_names[safe]}"
            else:
                used_names[safe] = 0
                
            out[safe] = _PropWrapper(pr)
        return out

    def _load_children(self) -> None:
        if self._level == "root":
            rows = self._client.workspaces.list(limit=200, offset=0)
            for w in rows:
                display = w.get("name") or str(w.get("id"))
                nm = _safe_key(display)
                child = _Node(self._client, "workspace", self, w["id"], display)
                child._cache_ttl = self._cache_ttl
                self._children_cache[nm] = child
        elif self._level == "workspace":
            page = self._client.products.list_by_workspace(workspace_id=self._id, limit=200, offset=0)
            for p in page.data:
                display = p.name or str(p.id)
                nm = _safe_key(display)
                child = _Node(self._client, "product", self, p.id, display)
                child._cache_ttl = self._cache_ttl
                self._children_cache[nm] = child
        elif self._level == "product":
            rows = self._client.items.list_by_product(product_id=self._id, limit=1000, offset=0)
            for it in rows:
                if it.get("parentId") is None:
                    display = it.get("name") or str(it["id"]) 
                    nm = _safe_key(display)
                    child = _Node(self._client, "item", self, it["id"], display)
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
            q = (
                "query($pid: ID!, $parent: ID!, $limit: Int!, $offset: Int!) {\n"
                "  items(productId: $pid, parentItemId: $parent, limit: $limit, offset: $offset) { id name code description productId parentId owner position }\n"
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
                display = it2.get("name") or str(it2["id"]) 
                nm = _safe_key(display)
                child = _Node(self._client, "item", self, it2["id"], display)
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
        org_id = self._root._client.org_id
        org_context = get_organization_context_message(org_id) if org_id else "🔒 Organization: Not configured"
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
            display = pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
            safe = _safe_key(str(display))
            
            # Handle duplicate names by adding a suffix
            if safe in used_names:
                used_names[safe] += 1
                safe = f"{safe}_{used_names[safe]}"
            else:
                used_names[safe] = 0
                
            self._children_cache[safe] = _PropWrapper(pr)
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
            return self._children_cache[attr]
        raise AttributeError(attr)

    def __getitem__(self, key: str) -> Any:
        self._ensure_loaded()
        if key in self._children_cache:
            return self._children_cache[key]
        # match by display name
        for safe, data in self._children_cache.items():
            try:
                if getattr(data, "_raw", {}).get("name") == key:  # type: ignore[arg-type]
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

    def __init__(self, prop: Dict[str, Any]) -> None:
        self._raw = prop

    @property
    def value(self) -> Any:  # type: ignore[override]
        p = self._raw
        # Use parsedValue if available (new backend feature)
        if "parsedValue" in p:
            return p["parsedValue"]
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
        if "value" in p:
            return p.get("value")
        return None

    @property
    def category(self) -> Optional[str]:
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

        Falls back to id or category when name is not present.
        """
        p = self._raw
        n = p.get("name") or p.get("id") or p.get("category")
        return str(n) if n is not None else None

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        # Expose only the minimal attributes for browsing
        return ["value", "category", "unit"]

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        name = self._raw.get("name") or self._raw.get("id")
        return f"<property {name}: {self.value}>"



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

