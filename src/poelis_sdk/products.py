from __future__ import annotations

from typing import Generator, Optional, List

from ._transport import Transport
from .models import PaginatedProducts, Product

"""Products resource client."""


class ProductsClient:
    """Client for product resources."""

    def __init__(self, transport: Transport) -> None:
        """Initialize with shared transport."""

        self._t = transport

    def list_by_workspace(self, *, workspace_id: str, q: Optional[str] = None, limit: int = 100, offset: int = 0) -> PaginatedProducts:
        """List products using GraphQL for a given workspace.

        Args:
            workspace_id: Workspace ID to scope products.
            q: Optional free-text filter.
            limit: Page size.
            offset: Offset for pagination.
        """

        query = (
            "query($ws: ID!, $q: String, $limit: Int!, $offset: Int!) {\n"
            "  products(workspaceId: $ws, q: $q, limit: $limit, offset: $offset) { id name code description workspaceId }\n"
            "}"
        )
        variables = {"ws": workspace_id, "q": q, "limit": int(limit), "offset": int(offset)}
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        rows: List[dict] = payload.get("data", {}).get("products", [])
        return PaginatedProducts(data=[Product(**r) for r in rows], limit=limit, offset=offset)

    def iter_all_by_workspace(self, *, workspace_id: str, q: Optional[str] = None, page_size: int = 100, start_offset: int = 0) -> Generator[Product, None, None]:
        """Iterate products via GraphQL with offset pagination for a workspace."""

        offset = start_offset
        while True:
            page = self.list_by_workspace(workspace_id=workspace_id, q=q, limit=page_size, offset=offset)
            if not page.data:
                break
            for product in page.data:
                yield product
            offset += len(page.data)


