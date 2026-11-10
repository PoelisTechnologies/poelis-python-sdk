from __future__ import annotations

from typing import Any

from ._transport import Transport


class ExternalSourcesClient:
    """Read and pin SharePoint files through the organization connection.

    Connecting the Microsoft account is a browser flow in Settings. This
    client uses the connection an admin already saved.
    """

    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def status(self) -> list[dict[str, Any]]:
        response = self._t.get("/v1/file-sources")
        body = response.json()
        return body if isinstance(body, list) else []

    def list_nodes(self, drive_id: str | None = None, item_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if drive_id:
            params["driveId"] = drive_id
        if item_id:
            params["itemId"] = item_id
        response = self._t.get("/v1/file-sources/sharepoint/nodes", params=params or None)
        body = response.json()
        return body if isinstance(body, list) else []

    def pin(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._t.post_json("/v1/file-sources/sharepoint/pins", payload)
        body = response.json()
        return body if isinstance(body, dict) else {}

    def search(self, query: str, workspace_id: str) -> list[dict[str, Any]]:
        response = self._t.post_json(
            "/v1/file-sources/sharepoint/search",
            {"q": query, "workspaceId": workspace_id},
        )
        body = response.json()
        hits = body.get("hits") if isinstance(body, dict) else None
        return hits if isinstance(hits, list) else []

    def download(self, ref_id: str) -> bytes:
        response = self._t.get(f"/v1/file-sources/sharepoint/refs/{ref_id}/content")
        return response.content
