"""Tests for WorkspacesClient list and get."""

from __future__ import annotations

import json

import httpx

from tests.conftest import client_with_transport


class _Transport(httpx.BaseTransport):
    def __init__(self) -> None:
        self.calls: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        payload = json.loads(request.content.decode("utf-8"))
        query = payload.get("query", "")
        variables = payload.get("variables", {})

        if "workspaces(" in query:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "workspaces": [
                            {"id": "w1", "orgId": "o1", "name": "Main", "readableId": "main"},
                        ]
                    }
                },
                request=request,
            )

        if "workspace(id:" in query:
            if variables.get("id") == "w1":
                return httpx.Response(
                    200,
                    json={
                        "data": {
                            "workspace": {
                                "id": "w1",
                                "orgId": "o1",
                                "name": "Main",
                                "readableId": "main",
                            }
                        }
                    },
                    request=request,
                )
            return httpx.Response(200, json={"data": {"workspace": None}}, request=request)

        return httpx.Response(200, json={"data": {}}, request=request)


def test_workspaces_list_passes_limit_offset() -> None:
    t = _Transport()
    c = client_with_transport(t)
    rows = c.workspaces.list(limit=10, offset=5)
    assert rows[0]["id"] == "w1"
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables == {"limit": 10, "offset": 5}


def test_workspaces_get_returns_workspace() -> None:
    t = _Transport()
    c = client_with_transport(t)
    ws = c.workspaces.get(workspace_id="w1")
    assert ws is not None
    assert ws["readableId"] == "main"
    variables = json.loads(t.calls[0].content.decode("utf-8"))["variables"]
    assert variables == {"id": "w1"}


def test_workspaces_get_returns_none_when_missing() -> None:
    t = _Transport()
    c = client_with_transport(t)
    assert c.workspaces.get(workspace_id="missing") is None
