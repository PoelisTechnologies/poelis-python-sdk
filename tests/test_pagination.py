"""Paging against a fake backend that pages like the real one.

Workspaces are filtered in SQL, so a short page is the last one. Products are
paged in SQL and then filtered by access, so a page can be short, or hold
fewer products than were skipped, before the end.
"""

from __future__ import annotations

import json

import httpx

from tests.conftest import client_with_transport


class _PagingBackend(httpx.BaseTransport):
    def __init__(self, *, workspaces: int, products: dict[str, list[str]], hidden: set[str] = frozenset()) -> None:
        self._workspaces = [
            {"id": f"w{i}", "orgId": "o1", "name": f"Workspace {i}", "readableId": f"ws_{i}"} for i in range(workspaces)
        ]
        self._products = products
        self._hidden = hidden
        self.requests: list[tuple[str, dict]] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.read())
        query, variables = body["query"], body["variables"]
        start, limit = variables.get("offset", 0), variables.get("limit", 50)
        if "workspaces(" in query:
            self.requests.append(("workspaces", variables))
            return httpx.Response(200, json={"data": {"workspaces": self._workspaces[start : start + limit]}})
        if "products(" in query:
            self.requests.append(("products", variables))
            page = self._products.get(variables["ws"], [])[start : start + limit]
            rows = [
                {"id": pid, "name": pid, "readableId": pid, "workspaceId": variables["ws"], "reviewers": []}
                for pid in page
                if pid not in self._hidden
            ]
            return httpx.Response(200, json={"data": {"products": rows}})
        raise AssertionError(f"unexpected query: {query[:60]}")

    def count(self, kind: str) -> int:
        return sum(1 for name, _ in self.requests if name == kind)


def test_iter_all_by_workspace_yields_each_visible_product_once_when_a_page_is_filtered() -> None:
    ids = [f"p{i}" for i in range(10)]
    backend = _PagingBackend(workspaces=1, products={"w0": ids}, hidden={"p1", "p2"})
    client = client_with_transport(backend)

    result = [p.id for p in client.products.iter_all_by_workspace(workspace_id="w0", page_size=4)]

    assert result == [pid for pid in ids if pid not in {"p1", "p2"}]
    assert [v["offset"] for _, v in backend.requests] == [0, 4, 8, 12]


def test_iter_all_reaches_workspaces_past_the_first_thousand() -> None:
    backend = _PagingBackend(workspaces=1001, products={"w1000": ["last"]})
    client = client_with_transport(backend)

    result = [p.id for p in client.products.iter_all(page_size=10)]

    assert result == ["last"]
    assert backend.count("workspaces") == 11


def test_browser_lists_more_than_two_hundred_workspaces() -> None:
    backend = _PagingBackend(workspaces=201, products={})
    client = client_with_transport(backend)

    names = client.browser.list_workspaces().names

    assert len(names) == 201
    assert "ws_200" in names


def test_browser_lists_more_than_two_hundred_products_in_a_workspace() -> None:
    ids = [f"p{i:03d}" for i in range(250)]
    backend = _PagingBackend(workspaces=1, products={"w0": ids})
    client = client_with_transport(backend)

    names = client.browser["ws_0"].list_products().names

    assert len(names) == 250
    assert "p249" in names
