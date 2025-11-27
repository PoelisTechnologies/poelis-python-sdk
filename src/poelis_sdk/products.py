from __future__ import annotations

from typing import TYPE_CHECKING, Generator, Optional

from ._transport import Transport
from .models import PaginatedProducts, PaginatedProductVersions, Product, ProductVersion

if TYPE_CHECKING:
    from .workspaces import WorkspacesClient

"""Products resource client."""


class ProductsClient:
    """Client for product resources."""

    def __init__(self, transport: Transport, workspaces_client: Optional["WorkspacesClient"] = None) -> None:
        """Initialize with shared transport and optional workspaces client."""

        self._t = transport
        self._workspaces_client = workspaces_client

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
            "  products(workspaceId: $ws, q: $q, limit: $limit, offset: $offset) { id name readableId workspaceId }\n"
            "}"
        )
        variables = {"ws": workspace_id, "q": q, "limit": int(limit), "offset": int(offset)}
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))

        products = payload.get("data", {}).get("products", [])

        return PaginatedProducts(data=[Product(**r) for r in products], limit=limit, offset=offset)

    def list_product_versions(self, *, product_id: str, limit: int = 50, offset: int = 0) -> PaginatedProductVersions:
        """List versions for a given product.

        Args:
            product_id: Identifier of the product whose versions should be listed.
            limit: Maximum number of versions to return (currently ignored by backend).
            offset: Offset for pagination (currently ignored by backend).

        Returns:
            PaginatedProductVersions: Container with version data and pagination info.

        Raises:
            RuntimeError: If the GraphQL response contains errors.
        """

        query = (
            "query($pid: ID!) {\n"
            "  productVersions(productId: $pid) {\n"
            "    productId\n"
            "    versionNumber\n"
            "    title\n"
            "    description\n"
            "    createdAt\n"
            "  }\n"
            "}"
        )
        variables = {"pid": product_id}
        resp = self._t.graphql(query=query, variables=variables)
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))

        versions = payload.get("data", {}).get("productVersions", [])

        return PaginatedProductVersions(data=[ProductVersion(**v) for v in versions], limit=limit, offset=offset)

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

    def iter_all(self, *, q: Optional[str] = None, page_size: int = 100) -> Generator[Product, None, None]:
        """Iterate products across all workspaces.
        
        Args:
            q: Optional free-text filter.
            page_size: Page size for each workspace iteration.
            
        Raises:
            RuntimeError: If workspaces client is not available.
        """
        if self._workspaces_client is None:
            raise RuntimeError("Workspaces client not available. Cannot iterate across all workspaces.")
            
        # Get all workspaces
        workspaces = self._workspaces_client.list(limit=1000, offset=0)
        
        for workspace in workspaces:
            workspace_id = workspace['id']
            # Iterate through products in this workspace
            for product in self.iter_all_by_workspace(workspace_id=workspace_id, q=q, page_size=page_size):
                yield product


