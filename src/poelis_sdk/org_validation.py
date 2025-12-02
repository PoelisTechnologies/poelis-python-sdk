"""Organization validation utilities for the Poelis SDK.

This module provides utilities for validating that data belongs to the
configured organization, ensuring proper multi-tenant isolation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .exceptions import ClientError


class OrganizationValidationError(ClientError):
    """Raised when data doesn't belong to the configured organization."""
    
    def __init__(self, message: str, expected_org_id: str, actual_org_id: Optional[str] = None) -> None:
        """Initialize organization validation error.
        
        Args:
            message: Error message describing the validation failure.
            expected_org_id: The organization ID that was expected.
            actual_org_id: The organization ID that was found (if any).
        """
        super().__init__(400, message)
        self.expected_org_id = expected_org_id
        self.actual_org_id = actual_org_id


def validate_organization_id(data: Dict[str, Any], expected_org_id: str, data_type: str = "item") -> None:
    """Validate that data belongs to the expected organization.
    
    Args:
        data: The data dictionary to validate.
        expected_org_id: The organization ID that should match.
        data_type: Type of data being validated (for error messages).
        
    Raises:
        OrganizationValidationError: If the data doesn't belong to the expected organization.
    """
    actual_org_id = data.get('orgId')
    
    if actual_org_id is None:
        raise OrganizationValidationError(
            f"{data_type.capitalize()} does not have an organization ID",
            expected_org_id,
            actual_org_id
        )
    
    if actual_org_id != expected_org_id:
        raise OrganizationValidationError(
            f"{data_type.capitalize()} belongs to organization '{actual_org_id}', "
            f"but client is configured for organization '{expected_org_id}'",
            expected_org_id,
            actual_org_id
        )


def filter_by_organization(data_list: List[Dict[str, Any]], expected_org_id: str, data_type: str = "items") -> List[Dict[str, Any]]:
    """Filter a list of data to only include items from the expected organization.
    
    Args:
        data_list: List of data dictionaries to filter.
        expected_org_id: The organization ID to filter by.
        data_type: Type of data being filtered (for logging).
        
    Returns:
        Filtered list containing only data from the expected organization.
    """
    filtered = []
    cross_org_count = 0
    
    for item in data_list:
        item_org_id = item.get('orgId')
        if item_org_id == expected_org_id:
            filtered.append(item)
        else:
            cross_org_count += 1
    
    return filtered


def validate_workspace_organization(workspace: Dict[str, Any], expected_org_id: str) -> None:
    """Validate that a workspace belongs to the expected organization.
    
    Args:
        workspace: The workspace dictionary to validate.
        expected_org_id: The organization ID that should match.
        
    Raises:
        OrganizationValidationError: If the workspace doesn't belong to the expected organization.
    """
    validate_organization_id(workspace, expected_org_id, "workspace")


def validate_product_organization(product: Any, expected_org_id: str) -> None:
    """Validate that a product belongs to the expected organization.
    
    Args:
        product: The product object to validate (can be dict or Product model).
        expected_org_id: The organization ID that should match.
        
    Raises:
        OrganizationValidationError: If the product doesn't belong to the expected organization.
    """
    # Handle both dict and Product model
    if hasattr(product, 'workspace_id'):
        # Product model - we need to get the workspace to check its org
        # This is a limitation of the current API design
        pass  # We'll handle this in the client methods
    elif isinstance(product, dict):
        # Dict format - check if it has orgId directly
        if 'orgId' in product:
            validate_organization_id(product, expected_org_id, "product")
        # If no orgId, we can't validate (backend should handle this)


def validate_item_organization(item: Dict[str, Any], expected_org_id: str) -> None:
    """Validate that an item belongs to the expected organization.
    
    Args:
        item: The item dictionary to validate.
        expected_org_id: The organization ID that should match.
        
    Raises:
        OrganizationValidationError: If the item doesn't belong to the expected organization.
    """
    validate_organization_id(item, expected_org_id, "item")


def get_organization_context_message(org_id: Optional[str]) -> str:
    """Get a user-friendly message about the current organization context.
    
    The SDK now uses user-bound API keys. Organization and workspace access
    are derived on the server from the authenticated user behind the key.
    
    Args:
        org_id: Deprecated organization identifier (ignored).
        
    Returns:
        A formatted message about the organization/key context.
    """
    if org_id:
        # Kept for backwards compatibility if callers still pass an ID.
        return f"🔒 Organization (derived from key): {org_id}"
    return "🔒 SDK key is user-bound; org and workspaces are derived from the key on the server"


def format_organization_error(error: OrganizationValidationError) -> str:
    """Format an organization validation error for user display.
    
    Args:
        error: The organization validation error.
        
    Returns:
        A formatted error message.
    """
    return (
        f"❌ Organization Mismatch: {error.message}\n"
        f"   Expected: {error.expected_org_id}\n"
        f"   Found: {error.actual_org_id or 'None'}\n"
        f"   This usually means the data belongs to a different organization."
    )
