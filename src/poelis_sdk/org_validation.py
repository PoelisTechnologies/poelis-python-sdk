"""Organization context helpers for the Poelis SDK.

Organization scoping is derived server-side from the API key. This module
only formats a short context string for browser/notebook UX.
"""

from __future__ import annotations

from typing import Optional


def get_organization_context_message(org_id: Optional[str]) -> str:
    """Get a user-friendly message about the current organization context.

    The SDK now uses user-bound API keys. Organization and workspace access
    are derived on the server from the authenticated user behind the key.

    Args:
        org_id: Deprecated organization identifier (ignored for access control).

    Returns:
        A formatted message about the organization/key context.
    """
    if org_id:
        return f"🔒 Organization (derived from key): {org_id}"
    return "🔒 SDK key is user-bound; org and workspaces are derived from the key on the server"
