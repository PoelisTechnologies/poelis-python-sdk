"""Integration smoke test for Poelis SDK.

Skips by default unless POELIS_API_KEY is set.
"""

from __future__ import annotations

import os

import pytest

from poelis_sdk import PoelisClient


@pytest.mark.integration
def test_smoke_list_workspaces() -> None:
    """List workspaces as a minimal live check if creds are provided."""
    api_key = os.getenv("POELIS_API_KEY")
    base_url = os.getenv("POELIS_BASE_URL", "https://api.poelis.com")

    if not api_key:
        pytest.skip("Integration creds not set; skipping smoke test")

    client = PoelisClient(api_key=api_key, base_url=base_url)
    # It is sufficient to verify that a call can be made without raising.
    _ = client.workspaces.list(limit=1, offset=0)


@pytest.mark.integration
def test_smoke_read_chain() -> None:
    api_key = os.environ.get("POELIS_API_KEY")
    if not api_key:
        pytest.skip("POELIS_API_KEY not set")

    client = PoelisClient(api_key=api_key, enable_change_detection=False)
    workspaces = client.workspaces.list(limit=1)
    assert workspaces
    ws_id = workspaces[0]["id"]
    assert client.workspaces.get(workspace_id=ws_id) is not None
    products = client.products.list_by_workspace(workspace_id=ws_id, limit=1)
    if not products.data:
        pytest.skip("no products in workspace")
    product = products.data[0]
    versions = client.products.list_product_versions(product_id=product.id, limit=1)
    items = client.items.list_by_product(product_id=product.id, limit=1)
    assert isinstance(items, list)
    _ = client.search.products(q="*", workspace_id=ws_id, limit=1)
    if versions.data:
        _ = client.versions.list_items(
            product_id=product.id,
            version_number=versions.data[0].version_number,
            limit=1,
        )
