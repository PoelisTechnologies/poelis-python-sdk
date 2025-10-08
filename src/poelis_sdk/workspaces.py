from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._transport import Transport

"""Workspaces GraphQL client."""


class WorkspacesClient:
    """Client for querying workspaces via GraphQL."""

    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def list(self, *, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List workspaces (implicitly scoped by org via auth)."""

        query = (
            "query($limit: Int!, $offset: Int!) {\n"
            "  workspaces(limit: $limit, offset: $offset) { id orgId name projectLimit }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"limit": int(limit), "offset": int(offset)})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        return payload.get("data", {}).get("workspaces", [])

    def get(self, *, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get a single workspace by id via GraphQL."""

        query = (
            "query($id: ID!) {\n"
            "  workspace(id: $id) { id orgId name projectLimit }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"id": workspace_id})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        return payload.get("data", {}).get("workspace")


