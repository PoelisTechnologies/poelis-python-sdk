from __future__ import annotations

from typing import Generator, Any, Optional, Dict, List

from ._transport import Transport

"""Items resource client."""


class ItemsClient:
    """Client for item resources (prototype exposes listing iterator only)."""

    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def list_by_product(self, *, product_id: str, q: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List items for a product via GraphQL with optional text filter."""

        query = (
            "query($pid: ID!, $q: String, $limit: Int!, $offset: Int!) {\n"
            "  items(productId: $pid, q: $q, limit: $limit, offset: $offset) { id name code description productId parentId owner }\n"
            "}"
        )
        variables = {"pid": product_id, "q": q, "limit": int(limit), "offset": int(offset)}
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        return payload.get("data", {}).get("items", [])

    def get(self, item_id: str) -> Dict[str, Any]:
        """Get a single item by id via GraphQL."""

        query = (
            "query($id: ID!) {\n"
            "  item(id: $id) { id name code description productId parentId owner }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"id": item_id})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        return payload.get("data", {}).get("item")

    def iter_all_by_product(self, *, product_id: str, q: Optional[str] = None, page_size: int = 100) -> Generator[dict, None, None]:
        """Iterate items via GraphQL for a given product."""

        offset = 0
        while True:
            data = self.list_by_product(product_id=product_id, q=q, limit=page_size, offset=offset)
            if not data:
                break
            for item in data:
                yield item
            offset += len(data)


