from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional

from ._transport import Transport

"""Items resource client."""


class ItemsClient:
    """Client for draft item resources.

    This client is intended for accessing the current draft view of items,
    i.e., items that are not bound to a specific product version. Versioned
    (snapshot) items for a given product version should be accessed via the
    `VersionsClient`.
    """

    def __init__(self, transport: Transport) -> None:
        """Initialize the client with shared transport.

        Args:
            transport: Shared HTTP/GraphQL transport used by the SDK.
        """

        self._t = transport

    def list_by_product(self, *, product_id: str, q: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List draft items for a product via GraphQL with optional text filter.

        This method is intended to return the current draft state of items for
        the given product (items without a bound product version). To retrieve
        historical/versioned items, use `VersionsClient.list_items`.

        Args:
            product_id: Identifier of the parent product.
            q: Optional free-text filter applied to item name/description.
            limit: Maximum number of items to return.
            offset: Offset for pagination.

        Returns:
            List of draft item dictionaries belonging to the client's
            configured organization.

        Raises:
            RuntimeError: If the GraphQL response contains errors.
        """

        query = (
            "query($pid: ID!, $q: String, $limit: Int!, $offset: Int!) {\n"
            "  items(productId: $pid, q: $q, limit: $limit, offset: $offset) { id name readableId productId parentId owner position }\n"
            "}"
        )
        variables = {"pid": product_id, "q": q, "limit": int(limit), "offset": int(offset)}
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        items = payload.get("data", {}).get("items", [])
        
        return items

    def get(self, item_id: str) -> Dict[str, Any]:
        """Get a single draft item by identifier via GraphQL.

        Returns the item only if it belongs to the client's configured
        organization. The returned representation reflects the current draft
        state, not a specific historical product version.

        Args:
            item_id: Identifier of the item to retrieve.

        Returns:
            Dictionary representing the draft item.

        Raises:
            RuntimeError: If the GraphQL response contains errors or the item
                cannot be found.
        """

        query = (
            "query($id: ID!) {\n"
            "  item(id: $id) { id name readableId productId parentId owner position }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"id": item_id})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        item = payload.get("data", {}).get("item")
        if item is None:
            raise RuntimeError(f"Item with id '{item_id}' not found")
        
        return item

    def iter_all_by_product(self, *, product_id: str, q: Optional[str] = None, page_size: int = 100) -> Generator[dict, None, None]:
        """Iterate draft items via GraphQL for a given product.

        Args:
            product_id: Identifier of the parent product.
            q: Optional free-text filter applied to item name/description.
            page_size: Page size for each GraphQL request.

        Yields:
            Individual draft item dictionaries.
        """

        offset = 0
        while True:
            data = self.list_by_product(product_id=product_id, q=q, limit=page_size, offset=offset)
            if not data:
                break
            for item in data:
                yield item
            offset += len(data)


