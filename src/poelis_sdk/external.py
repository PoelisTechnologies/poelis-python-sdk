from __future__ import annotations

from typing import Any

from ._transport import Transport


class ExternalSourcesClient:
    """Pinned SharePoint files for an organization connection."""

    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def status(self) -> list[dict[str, Any]]:
        return self._t.get("/v1/file-sources").json()

    def list_nodes(self, drive_id: str | None = None, item_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if drive_id:
            params["driveId"] = drive_id
        if item_id:
            params["itemId"] = item_id
        return self._t.get("/v1/file-sources/sharepoint/nodes", params=params or None).json()

    def pin(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._t.post_json("/v1/file-sources/sharepoint/pins", payload).json()

    def search(self, query: str, workspace_id: str) -> list[dict[str, Any]]:
        body = self._t.post_json(
            "/v1/file-sources/sharepoint/search",
            {"q": query, "workspaceId": workspace_id},
        ).json()
        return body["hits"]

    def download(self, ref_id: str) -> bytes:
        return self._t.get(f"/v1/file-sources/sharepoint/refs/{ref_id}/content").content
