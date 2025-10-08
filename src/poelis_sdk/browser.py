from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

"""GraphQL-backed dot-path browser for Poelis SDK.

Provides lazy, name-based navigation across workspaces → products → items → child items,
with optional property listing on items. Designed for notebook UX.
"""


class _Node:
    def __init__(self, client: Any, level: str, parent: Optional["_Node"], node_id: Optional[str], name: Optional[str]) -> None:
        self._client = client
        self._level = level
        self._parent = parent
        self._id = node_id
        self._name = name
        self._children_cache: Dict[str, "_Node"] = {}
        self._props_cache: Optional[List[Dict[str, Any]]] = None

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        path = []
        cur: Optional[_Node] = self
        while cur is not None and cur._name:
            path.append(cur._name)
            cur = cur._parent
        return f"<{self._level}:{'.'.join(reversed(path)) or '*'}>"

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        # Ensure children are loaded so TAB shows options immediately
        self._load_children()
        keys = list(self._children_cache.keys()) + ["properties", "id", "name", "refresh", "names", "props"]
        if self._level == "item":
            # Include property names directly on item for suggestions
            prop_keys = list(self._props_key_map().keys())
            keys.extend(prop_keys)
        return sorted(keys)

    @property
    def id(self) -> Optional[str]:
        return self._id

    @property
    def name(self) -> Optional[str]:
        return self._name

    def refresh(self) -> "_Node":
        self._children_cache.clear()
        self._props_cache = None
        return self

    def names(self) -> List[str]:
        """Return display names of children at this level (forces a lazy load)."""
        self._load_children()
        return [child._name or "" for child in self._children_cache.values()]

    def __getattr__(self, attr: str) -> Any:
        if attr in {"properties", "id", "name", "refresh"}:
            return object.__getattribute__(self, attr)
        if attr == "props":  # item-level properties pseudo-node
            if self._level != "item":
                raise AttributeError("props")
            return _PropsNode(self)
        if attr not in self._children_cache:
            self._load_children()
        if attr in self._children_cache:
            return self._children_cache[attr]
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

    @property
    def properties(self) -> List[Dict[str, Any]]:
        if self._props_cache is not None:
            return self._props_cache
        if self._level != "item":
            self._props_cache = []
            return self._props_cache
        # Try direct properties(item_id: ...) first; fallback to searchProperties
        q = (
            "query($iid: ID!) {\n"
            "  properties(item_id: $iid) {\n"
            "    __typename id name owner\n"
            "    ... on NumericProperty { integerPart exponent category }\n"
            "    ... on TextProperty { value }\n"
            "    ... on DateProperty { value }\n"
            "  }\n"
            "}"
        )
        try:
            r = self._client._transport.graphql(q, {"iid": self._id})
            r.raise_for_status()
            data = r.json()
            if "errors" in data:
                raise RuntimeError(data["errors"])  # trigger fallback
            self._props_cache = data.get("data", {}).get("properties", []) or []
        except Exception:
            q2 = (
                "query($iid: ID!, $limit: Int!, $offset: Int!) {\n"
                "  searchProperties(q: \"*\", itemId: $iid, limit: $limit, offset: $offset) {\n"
                "    hits { id name propertyType category textValue numericValue dateValue owner }\n"
                "  }\n"
                "}"
            )
            r2 = self._client._transport.graphql(q2, {"iid": self._id, "limit": 100, "offset": 0})
            r2.raise_for_status()
            data2 = r2.json()
            if "errors" in data2:
                raise RuntimeError(data2["errors"])  # propagate
            self._props_cache = data2.get("data", {}).get("searchProperties", {}).get("hits", []) or []
        return self._props_cache

    def _props_key_map(self) -> Dict[str, Dict[str, Any]]:
        """Map safe keys to property wrappers for item-level attribute access."""
        out: Dict[str, Dict[str, Any]] = {}
        if self._level != "item":
            return out
        props = self.properties
        for pr in props:
            display = pr.get("name") or pr.get("id")
            safe = _safe_key(str(display))
            out[safe] = _PropWrapper(pr)
        return out

    def _load_children(self) -> None:
        if self._level == "root":
            rows = self._client.workspaces.list(limit=200, offset=0)
            for w in rows:
                display = w.get("name") or str(w.get("id"))
                nm = _safe_key(display)
                self._children_cache[nm] = _Node(self._client, "workspace", self, w["id"], display)
        elif self._level == "workspace":
            page = self._client.products.list_by_workspace(workspace_id=self._id, limit=200, offset=0)
            for p in page.data:
                display = p.name or str(p.id)
                nm = _safe_key(display)
                self._children_cache[nm] = _Node(self._client, "product", self, p.id, display)
        elif self._level == "product":
            rows = self._client.items.list_by_product(product_id=self._id, limit=1000, offset=0)
            for it in rows:
                if it.get("parentId") is None:
                    display = it.get("name") or str(it["id"]) 
                    nm = _safe_key(display)
                    self._children_cache[nm] = _Node(self._client, "item", self, it["id"], display)
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
                "  items(productId: $pid, parentItemId: $parent, limit: $limit, offset: $offset) { id name code description productId parentId owner }\n"
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
                self._children_cache[nm] = _Node(self._client, "item", self, it2["id"], display)


class Browser:
    """Public browser entrypoint."""

    def __init__(self, client: Any) -> None:
        self._root = _Node(client, "root", None, None, None)

    def __getattr__(self, attr: str) -> Any:  # pragma: no cover - notebook UX
        return getattr(self._root, attr)

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        return "<browser root>"

    def __getitem__(self, key: str) -> Any:  # pragma: no cover - notebook UX
        """Delegate index-based access to the root node so names work: browser["Workspace Name"]."""
        return self._root[key]

    def __dir__(self) -> list[str]:  # pragma: no cover - notebook UX
        # Ensure children are loaded so TAB shows options
        self._root._load_children()
        return sorted([*self._root._children_cache.keys(), "names"]) 


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

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        return f"<props of {self._item.name or self._item.id}>"

    def _ensure_loaded(self) -> None:
        if self._children_cache:
            return
        props = self._item.properties
        for pr in props:
            display = pr.get("name") or pr.get("id")
            safe = _safe_key(str(display))
            self._children_cache[safe] = _PropWrapper(pr)
        self._names = [p.get("name") or p.get("id") for p in props]

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        self._ensure_loaded()
        return sorted(list(self._children_cache.keys()) + ["names"]) 

    def names(self) -> List[str]:
        self._ensure_loaded()
        return list(self._names)

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
            if data.raw.get("name") == key:
                return data
        safe = _safe_key(key)
        if safe in self._children_cache:
            return self._children_cache[safe]
        raise KeyError(key)


class _PropWrapper:
    """Lightweight accessor for a property dict, exposing `.value` and `.raw`.

    Normalizes different property result shapes (union vs search) into `.value`.
    """

    def __init__(self, prop: Dict[str, Any]) -> None:
        self._raw = prop

    @property
    def raw(self) -> Dict[str, Any]:
        return self._raw

    @property
    def value(self) -> Any:  # type: ignore[override]
        p = self._raw
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

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        name = self._raw.get("name") or self._raw.get("id")
        return f"<property {name}: {self.value}>"


