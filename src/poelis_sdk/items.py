from __future__ import annotations

from typing import Any, Generator

from ._item_filter import build_item_filter
from ._transport import Transport
from .files import _version_variable
from .models import Item

"""Items resource client."""


_LIST_ITEMS_QUERY = """
query SdkListItemsAtVersion(
  $pid: ID!, $version: VersionInput, $filter: ItemFilter, $limit: Int!, $offset: Int!
) {
  sdkItems(productId: $pid, version: $version, filter: $filter, limit: $limit, offset: $offset) {
    id readableId productId parentDraftItemId name description partNumber draftItemId deleted position
  }
}
"""


class ItemsClient:
    """Client for item resources.

    ``list`` and ``iter_all`` read items in the draft or at a version. The
    older ``list_by_product`` / ``iter_all_by_product`` read the draft only, and
    ``VersionsClient.list_items`` reads a numbered version.
    """

    def __init__(self, transport: Transport) -> None:
        """Initialize the client with shared transport.

        Args:
            transport: Shared HTTP/GraphQL transport used by the SDK.
        """

        self._t = transport

    def list_by_product(
        self,
        *,
        product_id: str,
        q: str | None = None,
        root_only: bool | None = None,
        parent_item_id: str | None = None,
        include_deleted: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List draft items for a product via GraphQL with optional filters.

        For the draft or any version as ``Item`` models, use ``items.list``.

        This method is intended to return the current draft state of items for
        the given product (items without a bound product version). To retrieve
        historical/versioned items, use `VersionsClient.list_items`.

        Args:
            product_id: Identifier of the parent product.
            q: Optional free-text filter applied to item name.
            root_only: When True, return only root items (no parent).
            parent_item_id: Return the parent item and its direct children.
            include_deleted: Include soft-deleted draft items.
            limit: Maximum number of items to return.
            offset: Offset for pagination.

        Returns:
            List of draft item dictionaries belonging to the client's
            configured organization.

        Raises:
            RuntimeError: If the GraphQL response contains errors.
        """

        query = (
            "query SdkListItems($pid: ID!, $filter: ItemFilter, $limit: Int!, $offset: Int!) {\n"
            "  items(productId: $pid, filter: $filter, limit: $limit, offset: $offset) { id name description readableId productId parentId position draftItemId }\n"
            "}"
        )
        variables = {
            "pid": product_id,
            "filter": build_item_filter(
                q=q,
                root_only=root_only,
                parent_item_id=parent_item_id,
                include_deleted=include_deleted,
            ),
            "limit": int(limit),
            "offset": int(offset),
        }
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        items = payload.get("data", {}).get("items", [])
        
        return items

    def get(self, item_id: str) -> dict[str, Any]:
        """Get a single draft item by identifier via GraphQL.

        Returns the item only if it belongs to the client's configured
        organization. The returned representation reflects the current draft
        state.

        Args:
            item_id: Identifier of the item to retrieve.

        Returns:
            Dictionary representing the draft item.

        Raises:
            RuntimeError: If the GraphQL response contains errors or the item
                cannot be found.
        """

        query = (
            "query SdkItem($id: ID!) {\n"
            "  item(id: $id) { id name description readableId productId parentId position }\n"
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

    def iter_all_by_product(
        self,
        *,
        product_id: str,
        q: str | None = None,
        root_only: bool | None = None,
        parent_item_id: str | None = None,
        include_deleted: bool | None = None,
        page_size: int = 100,
    ) -> Generator[dict[str, Any], None, None]:
        """Iterate draft items via GraphQL for a given product.

        Args:
            product_id: Identifier of the parent product.
            q: Optional free-text filter applied to item name.
            root_only: When True, return only root items (no parent).
            parent_item_id: Return the parent item and its direct children.
            include_deleted: Include soft-deleted draft items.
            page_size: Page size for each GraphQL request.

        Yields:
            Individual draft item dictionaries.
        """

        offset = 0
        while True:
            data = self.list_by_product(
                product_id=product_id,
                q=q,
                root_only=root_only,
                parent_item_id=parent_item_id,
                include_deleted=include_deleted,
                limit=page_size,
                offset=offset,
            )
            if not data:
                break
            for item in data:
                yield item
            offset += len(data)
            if len(data) < page_size:
                break

    def list(
        self,
        product_id: str,
        *,
        version: int | str | None = None,
        q: str | None = None,
        root_only: bool | None = None,
        parent_item_id: str | None = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Item]:
        """Return one page of a product's items, in the draft or at a version.

        Mirrors ``GET /v1/public/items`` of the REST API.

        Args:
            product_id: Product whose items to list.
            version: ``None`` for the draft, a version number, or ``"baseline"``
                for the product's baseline version (no items if none is set).
            q: Optional free-text filter applied to item names.
            root_only: When True, return only root items.
            parent_item_id: Draft id of a parent; returns it and its direct children.
            include_deleted: Include soft-deleted draft items.
            limit: Page size.
            offset: Number of items to skip.

        Raises:
            ValueError: If ``version`` is not an integer, ``"baseline"`` or None.
        """
        variables: dict[str, Any] = {
            "pid": product_id,
            "version": _version_variable(version),
            "filter": build_item_filter(
                q=q,
                root_only=root_only,
                parent_item_id=parent_item_id,
                include_deleted=include_deleted or None,
            ),
            "limit": int(limit),
            "offset": int(offset),
        }
        payload = self._t.graphql(_LIST_ITEMS_QUERY, variables).json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        rows = (payload.get("data") or {}).get("sdkItems") or []
        return [Item.model_validate(row) for row in rows]

    def iter_all(
        self,
        product_id: str,
        *,
        version: int | str | None = None,
        q: str | None = None,
        root_only: bool | None = None,
        parent_item_id: str | None = None,
        include_deleted: bool = False,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Generator[Item, None, None]:
        """Iterate over every item that ``list`` would return, page by page."""
        offset = start_offset
        while True:
            page = self.list(
                product_id,
                version=version,
                q=q,
                root_only=root_only,
                parent_item_id=parent_item_id,
                include_deleted=include_deleted,
                limit=page_size,
                offset=offset,
            )
            yield from page
            if len(page) < page_size:
                break
            offset += len(page)
