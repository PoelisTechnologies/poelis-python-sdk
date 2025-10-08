"""Tests for exception mapping and retry/backoff behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from poelis_sdk import PoelisClient
from poelis_sdk.exceptions import NotFoundError, RateLimitError, UnauthorizedError

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


class _SeqTransport(httpx.BaseTransport):
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.calls = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls += 1
        return self._responses.pop(0)


def _make_client_with_transport(transport: httpx.BaseTransport) -> PoelisClient:
    from poelis_sdk.client import Transport as _T

    def _init(self, base_url: str, api_key: str, org_id: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=timeout_seconds)
        self._api_key = api_key
        self._org_id = org_id
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        return PoelisClient(base_url="http://example.com", api_key="k", org_id="o")
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


def test_401_raises_unauthorized() -> None:
    t = _SeqTransport([httpx.Response(401, json={"message": "bad token"})])
    c = _make_client_with_transport(t)
    with pytest.raises(UnauthorizedError):
        c.search.products(q="x")


def test_404_raises_not_found() -> None:
    t = _SeqTransport([httpx.Response(404, json={"message": "not found"})])
    c = _make_client_with_transport(t)
    with pytest.raises(NotFoundError):
        c.search.products(q="x")


def test_429_retries_then_raises(monkeypatch: "MonkeyPatch") -> None:
    # two 429s then final 429 -> raise RateLimitError
    t = _SeqTransport([
        httpx.Response(429, headers={"Retry-After": "0.0"}),
        httpx.Response(429, headers={"Retry-After": "0.0"}),
        httpx.Response(429, headers={"Retry-After": "0.0"}),
    ])
    c = _make_client_with_transport(t)
    with pytest.raises(RateLimitError):
        c.search.products(q="x")
    assert t.calls == 3


def test_5xx_retries_then_success() -> None:
    t = _SeqTransport([
        httpx.Response(500, json={"message": "oops"}),
        httpx.Response(502, json={"message": "oops"}),
        httpx.Response(200, json={"hits": [], "limit": 20, "offset": 0}),
    ])
    c = _make_client_with_transport(t)
    result = c.search.products(q="x")
    assert result["hits"] == []


