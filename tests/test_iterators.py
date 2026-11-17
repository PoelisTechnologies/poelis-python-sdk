from __future__ import annotations

import json

import httpx

from tests.conftest import client_with_transport


class _PagedRows(httpx.BaseTransport):
    """Serves ``workspaces`` and draft ``items`` sliced by limit and offset."""

    def __init__(self, count: int) -> None:
        self._count = count
        self.pages: list[tuple[int, int]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        variables = body["variables"]
        offset, limit = variables["offset"], variables["limit"]
        self.pages.append((offset, limit))
        ids = list(range(self._count))[offset : offset + limit]
        if "workspaces(" in body["query"]:
            rows = [{"id": f"w{i}", "orgId": "o1", "name": f"W{i}", "readableId": f"w{i}"} for i in ids]
            return httpx.Response(200, json={"data": {"workspaces": rows}})
        rows = [{"id": f"i{i}", "name": f"I{i}", "productId": "p1"} for i in ids]
        return httpx.Response(200, json={"data": {"items": rows}})


def test_workspaces_iter_all_walks_every_page_and_stops_on_a_short_page() -> None:
    backend = _PagedRows(5)
    client = client_with_transport(backend)

    ids = [w["id"] for w in client.workspaces.iter_all(page_size=2)]

    assert ids == ["w0", "w1", "w2", "w3", "w4"]
    assert backend.pages == [(0, 2), (2, 2), (4, 2)]


def test_workspaces_iter_all_starts_at_start_offset() -> None:
    backend = _PagedRows(4)
    client = client_with_transport(backend)

    assert [w["id"] for w in client.workspaces.iter_all(page_size=2, start_offset=2)] == ["w2", "w3"]
    assert backend.pages == [(2, 2), (4, 2)]


def test_items_iter_all_by_product_starts_at_start_offset() -> None:
    backend = _PagedRows(5)
    client = client_with_transport(backend)

    ids = [it["id"] for it in client.items.iter_all_by_product(product_id="p1", page_size=2, start_offset=3)]

    assert ids == ["i3", "i4"]
    assert backend.pages == [(3, 2), (5, 2)]
