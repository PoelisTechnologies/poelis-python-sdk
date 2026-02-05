from __future__ import annotations

from typing import Any, Dict, Optional

from ._transport import Transport

"""Search resource client using GraphQL endpoints only."""


class SearchClient:
    """Search for products, items, and properties via GraphQL (/v1/graphql)."""

    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def products(self, *, q: str, workspace_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Search/list products via GraphQL products(workspaceId, filter: { q })."""

        query = (
            "query($ws: ID!, $filter: ProductFilter, $limit: Int!, $offset: Int!) {\n"
            "  products(workspaceId: $ws, filter: $filter, limit: $limit, offset: $offset) { id name workspaceId }\n"
            "}"
        )
        variables = {"ws": workspace_id, "filter": {"q": q} if q else None, "limit": int(limit), "offset": int(offset)}
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        hits = payload.get("data", {}).get("products", [])
        return {"query": q, "hits": hits, "total": None, "limit": limit, "offset": offset}

    def items(self, *, q: Optional[str], product_id: str, parent_item_id: Optional[str] = None, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Search/list items via GraphQL items(product_id, q, parent_item_id)."""

        query = (
            "query($pid: ID!, $filter: ItemFilter, $limit: Int!, $offset: Int!) {\n"
            "  items(productId: $pid, filter: $filter, limit: $limit, offset: $offset) { id name productId parentId position }\n"
            "}"
        )
        filter_obj: Dict[str, Any] = {}
        if q is not None:
            filter_obj["q"] = q
        if parent_item_id is not None:
            filter_obj["parentItemId"] = parent_item_id
        variables = {"pid": product_id, "filter": filter_obj if filter_obj else None, "limit": int(limit), "offset": int(offset)}
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        hits = payload.get("data", {}).get("items", [])
        return {"query": q, "hits": hits, "total": None, "limit": limit, "offset": offset}

    def properties(self, *, q: str, workspace_id: Optional[str] = None, product_id: Optional[str] = None, item_id: Optional[str] = None, property_type: Optional[str] = None, category: Optional[str] = None, limit: int = 20, offset: int = 0, sort: Optional[str] = None) -> Dict[str, Any]:
        """Search properties via GraphQL search_properties."""

        query = (
            "query($q: String!, $ws: ID, $pid: ID, $iid: ID, $ptype: String, $cat: String, $limit: Int!, $offset: Int!, $sort: String) {\n"
            "  searchProperties(q: $q, workspaceId: $ws, productId: $pid, itemId: $iid, propertyType: $ptype, category: $cat, limit: $limit, offset: $offset, sort: $sort) {\n"
            "    query total limit offset processingTimeMs\n"
            "    hits { id workspaceId productId itemId propertyType name category value }\n"
            "  }\n"
            "}"
        )
        variables: Dict[str, Any] = {
            "q": q,
            "ws": workspace_id,
            "pid": product_id,
            "iid": item_id,
            "ptype": property_type,
            "cat": category,
            "limit": int(limit),
            "offset": int(offset),
            "sort": sort,
        }
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        data = payload.get("data", {}).get("searchProperties", {})
        # Normalize to match previous REST shape
        return {
            "query": data.get("query", q),
            "hits": data.get("hits", []),
            "total": data.get("total"),
            "limit": data.get("limit", limit),
            "offset": data.get("offset", offset),
            "processing_time_ms": data.get("processingTimeMs", 0),
        }


