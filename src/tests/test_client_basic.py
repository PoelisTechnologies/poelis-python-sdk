"""Basic tests for PoelisClient scaffolding.

These tests ensure that the client can be imported and instantiated
with minimal configuration and that resource accessors are present.
"""

from __future__ import annotations

from typing import TYPE_CHECKING


from poelis_sdk import PoelisClient

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def test_client_instantiation() -> None:
    """Client instantiation validates config and exposes resources."""

    client = PoelisClient(api_key="k", org_id="o", base_url="http://localhost:8000")
    assert client.base_url == "http://localhost:8000/"
    assert client.org_id == "o"
    assert hasattr(client, "products")


def test_client_default_base_url() -> None:
    """Client uses production URL as default when base_url not provided."""

    client = PoelisClient(api_key="k", org_id="o")
    assert client.base_url == "https://api.poelis.ai/"
    assert client.org_id == "o"
    assert hasattr(client, "products")


def test_client_api_key_headers(monkeypatch: "MonkeyPatch") -> None:
    """When api_key and org_id are provided, use ApiKey and X-Poelis-Org headers."""

    import httpx
    from poelis_sdk.client import Transport as _T

    class _Tpt(httpx.BaseTransport):
        def __init__(self) -> None:
            self.last: httpx.Request | None = None

        def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
            self.last = request
            return httpx.Response(200, json={"data": [], "limit": 1, "offset": 0})

    t = _Tpt()

    def _init(self, base_url: str, api_key: str, org_id: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._org_id = org_id
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        client = PoelisClient(api_key="poelis_live_abc", org_id="tenant_x", base_url="http://localhost:8000")
        # trigger a request to test headers
        client._transport.get("/health")
        assert t.last is not None
        assert t.last.headers.get("Authorization") == "ApiKey poelis_live_abc"
        assert t.last.headers.get("X-Poelis-Org") == "tenant_x"
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


def test_from_env(monkeypatch: "MonkeyPatch") -> None:
    """from_env reads env vars and constructs client accordingly."""

    monkeypatch.setenv("POELIS_BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("POELIS_API_KEY", "poelis_live_abc")
    monkeypatch.setenv("POELIS_ORG_ID", "tenant_x")

    c = PoelisClient.from_env()
    assert c.base_url == "http://localhost:8000/"


def test_from_env_default_url(monkeypatch: "MonkeyPatch") -> None:
    """from_env uses production URL as default when POELIS_BASE_URL not set."""

    monkeypatch.delenv("POELIS_BASE_URL", raising=False)
    monkeypatch.setenv("POELIS_API_KEY", "poelis_live_abc")
    monkeypatch.setenv("POELIS_ORG_ID", "tenant_x")

    c = PoelisClient.from_env()
    assert c.base_url == "https://api.poelis.ai/"


