from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional

from ._transport import Transport
from .models import UserAccessibleResources

"""Workspaces GraphQL client."""


class WorkspacesClient:
    """Client for querying workspaces via GraphQL."""

    def __init__(self, transport: Transport) -> None:
        self._t = transport

    def list(self, *, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List workspaces (implicitly scoped by org via auth).
        
        Workspaces are automatically filtered based on the user's API key.
        Only workspaces the user has access to are returned. Access control
        is enforced server-side based on the user's workspace roles.
        """

        query = (
            "query SdkListWorkspaces($limit: Int!, $offset: Int!) {\n"
            "  workspaces(limit: $limit, offset: $offset) { id orgId name readableId }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"limit": int(limit), "offset": int(offset)})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        workspaces = payload.get("data", {}).get("workspaces", [])
        return workspaces

    def get(self, *, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get a single workspace by id via GraphQL."""

        query = (
            "query SdkWorkspace($id: ID!) {\n"
            "  workspace(id: $id) { id orgId name readableId }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"id": workspace_id})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        workspace = payload.get("data", {}).get("workspace")
        return workspace

    def get_user_accessible_resources(self, *, user_id: str) -> UserAccessibleResources:
        """Get accessible resources (workspaces and products) for a user with role information.
        
        This query returns all workspaces and products a user can access, along with
        their roles. Product-level roles override workspace roles when set.
        Requires the current user to be in the same organization as the queried user.
        
        Args:
            user_id: Identifier of the user whose accessible resources to query.
            
        Returns:
            UserAccessibleResources: Container with workspaces and products the user
                can access, including role information.
                
        Raises:
            RuntimeError: If the GraphQL response contains errors.
            UnauthorizedError: If the current user is not in the same organization.
        """
        
        query = (
            "query SdkUserAccessibleResources($userId: String!) {\n"
            "  userAccessibleResources(userId: $userId) {\n"
            "    id\n"
            "    name\n"
            "    readableId\n"
            "    role\n"
            "    products {\n"
            "      id\n"
            "      name\n"
            "      readableId\n"
            "      role\n"
            "    }\n"
            "  }\n"
            "}"
        )
        resp = self._t.graphql(query=query, variables={"userId": user_id})
        resp.raise_for_status()
        payload = resp.json()
        if "errors" in payload:
            raise RuntimeError(str(payload["errors"]))
        
        raw = payload.get("data", {}).get("userAccessibleResources")
        if raw is None:
            raise RuntimeError("Malformed GraphQL response: missing 'userAccessibleResources' field")
        workspaces = raw if isinstance(raw, list) else [raw]
        return UserAccessibleResources(workspaces=workspaces)

    def iter_all(self, *, page_size: int = 100, start_offset: int = 0) -> Generator[Dict[str, Any], None, None]:
        """Iterate every workspace the API key can see, one page at a time.

        Args:
            page_size: Page size for each GraphQL request.
            start_offset: Initial offset for pagination.

        Yields:
            Workspace dictionaries, in the same shape as :meth:`list`.
        """

        offset = start_offset
        while True:
            page = self.list(limit=page_size, offset=offset)
            if not page:
                break
            yield from page
            offset += len(page)
            if len(page) < page_size:
                break
