from __future__ import annotations

import httpx

from poelis_sdk import PoelisClient
from poelis_sdk.client import Transport


def client_with_transport(transport: httpx.BaseTransport) -> PoelisClient:
    def _init(self: Transport, base_url: str, api_key: str, timeout_seconds: float) -> None:
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds

    original = Transport.__init__
    Transport.__init__ = _init  # type: ignore[method-assign]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k", enable_change_detection=False)
    finally:
        Transport.__init__ = original  # type: ignore[method-assign]
