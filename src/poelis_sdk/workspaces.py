from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._transport import Transport
from .org_validation import filter_by_organization, validate_workspace_organization

"""Workspaces GraphQL client."""


class WorkspacesClient:
    """Client for querying workspaces via GraphQL."""

    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def list(self, *, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List workspaces (implicitly scoped by org via auth).
        
        Returns only workspaces that belong to the client's configured organization.
        """

        query = (
            "query($limit: Int!, $offset: Int!) {\n"
            "  workspaces(limit: $limit, offset: $offset) { id orgId name readableId projectLimit }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"limit": int(limit), "offset": int(offset)})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        workspaces = payload.get("data", {}).get("workspaces", [])
        
        # Client-side organization filtering as backup protection
        expected_org_id = self._t._org_id
        filtered_workspaces = filter_by_organization(workspaces, expected_org_id, "workspaces")
        
        return filtered_workspaces

    def get(self, *, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get a single workspace by id via GraphQL.
        
        Returns the workspace only if it belongs to the client's configured organization.
        """

        query = (
            "query($id: ID!) {\n"
            "  workspace(id: $id) { id orgId name readableId projectLimit }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"id": workspace_id})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        workspace = payload.get("data", {}).get("workspace")
        if workspace is None:
            return None
        
        # Validate that the workspace belongs to the configured organization
        expected_org_id = self._t._org_id
        validate_workspace_organization(workspace, expected_org_id)
        
        return workspace


