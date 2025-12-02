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
    base_url = os.getenv("POELIS_BASE_URL", "https://api.poelis.ai")

    if not api_key:
        pytest.skip("Integration creds not set; skipping smoke test")

    client = PoelisClient(api_key=api_key, base_url=base_url)
    # It is sufficient to verify that a call can be made without raising.
    _ = client.workspaces.list(limit=1, offset=0)

