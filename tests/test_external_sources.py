from __future__ import annotations

import json

import httpx

from tests.test_file_upload import _client, _RecordingTransport


def test_external_client_uses_the_file_source_routes() -> None:
    transport = _RecordingTransport(
        [
            httpx.Response(200, json=[{"provider": "sharepoint", "status": "connected"}]),
            httpx.Response(200, json=[{"id": "item-1", "kind": "file", "name": "Spec.pdf"}]),
            httpx.Response(200, json={"ids": ["ref-1"]}),
            httpx.Response(200, json={"hits": [{"id": "item-2", "name": "Spec.pdf"}]}),
            httpx.Response(200, content=b"pdf"),
        ]
    )
    client = _client(transport)

    assert client.external.status()[0]["status"] == "connected"
    assert client.external.list_nodes("drive-1")[0]["name"] == "Spec.pdf"
    assert client.external.pin({"workspaceId": "ws", "items": []})["ids"] == ["ref-1"]
    assert client.external.search("spec", "ws")[0]["id"] == "item-2"
    assert client.external.download("ref-1") == b"pdf"

    paths = [request.url.path for request in transport.requests]
    assert paths == [
        "/v1/file-sources",
        "/v1/file-sources/sharepoint/nodes",
        "/v1/file-sources/sharepoint/pins",
        "/v1/file-sources/sharepoint/search",
        "/v1/file-sources/sharepoint/refs/ref-1/content",
    ]
    assert transport.requests[1].url.params["driveId"] == "drive-1"
    pin_body = json.loads(transport.requests[2].content)
    assert pin_body["workspaceId"] == "ws"
