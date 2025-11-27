from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional

from ._transport import Transport

"""Versions resource client.

Provides read-only access to product versions and their versioned items.
This client is focused on versioned (snapshot) data; draft mutations should
continue to go through the non-versioned clients.
"""


class VersionsClient:
    """Client for product version resources."""

    def __init__(self, transport: Transport) -> None:
        """Initialize the client with shared transport.

        Args:
            transport: Shared HTTP/GraphQL transport used by the SDK.
        """

        self._t = transport

    def list_items(
        self,
        *,
        product_id: str,
        version_number: int,
        q: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List versioned items for a specific product version via GraphQL.

        This method returns the snapshot of items as they were frozen in the
        specified product version. Draft items should be accessed through the
        non-versioned `ItemsClient`.

        Args:
            product_id: Identifier of the parent product.
            version_number: Version number of the product whose items to list.
            q: Optional free-text filter applied to item name/description.
            limit: Maximum number of items to return.
            offset: Offset for pagination.

        Returns:
            List of item dictionaries belonging to the given product version.

        Raises:
            RuntimeError: If the GraphQL response contains errors.
        """

        query = (
            "query($pid: ID!, $version: VersionInput!, $q: String, $limit: Int!, $offset: Int!) {\n"
            "  items(productId: $pid, version: $version, q: $q, limit: $limit, offset: $offset) {\n"
            "    id\n"
            "    name\n"
            "    readableId\n"
            "    productId\n"
            "    parentId\n"
            "    owner\n"
            "    position\n"
            "  }\n"
            "}"
        )
        variables = {
            "pid": product_id,
            "version": {"productId": product_id, "versionNumber": int(version_number)},
            "q": q,
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

    def iter_items(
        self,
        *,
        product_id: str,
        version_number: int,
        q: Optional[str] = None,
        page_size: int = 100,
        start_offset: int = 0,
    ) -> Generator[Dict[str, Any], None, None]:
        """Iterate versioned items for a specific product version.

        Args:
            product_id: Identifier of the parent product.
            version_number: Version number whose items to iterate.
            q: Optional free-text filter applied to item name/description.
            page_size: Page size for each GraphQL request.
            start_offset: Initial offset for pagination.

        Yields:
            Individual item dictionaries for the given product version.
        """

        offset = start_offset
        while True:
            page = self.list_items(
                product_id=product_id,
                version_number=version_number,
                q=q,
                limit=page_size,
                offset=offset,
            )
            if not page:
                break
            for item in page:
                yield item
            offset += len(page)


