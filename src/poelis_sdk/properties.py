from __future__ import annotations

import json
from typing import Any, Dict, Optional

from ._transport import Transport
from .exceptions import NotFoundError, UnauthorizedError

"""Properties resource client for updating property values."""


class PropertiesClient:
    """Client for updating property values via GraphQL mutations."""

    def __init__(self, transport: Transport) -> None:
        """Initialize with shared transport.

        Args:
            transport: Shared HTTP/GraphQL transport used by the SDK.
        """
        self._t = transport

    def update_numeric_property(
        self,
        *,
        id: str,  # noqa: A002
        value: Optional[str] = None,
        item_id: Optional[str] = None,
        name: Optional[str] = None,
        readable_id: Optional[str] = None,
        position: Optional[float] = None,
        category: Optional[str] = None,
        display_unit: Optional[str] = None,
        owner: Optional[str] = None,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        changed_via: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a numeric property via GraphQL mutation.

        Args:
            id: Property ID (required).
            value: New value as JSON string (number, array, or matrix).
            item_id: Optional item ID to move property to.
            name: Optional property name.
            readable_id: Optional readable ID.
            position: Optional position for ordering.
            category: Optional category (auto-normalized to uppercase snake_case).
            display_unit: Optional display unit.
            owner: Optional owner.
            reason: Optional reason for history tracking.
            description: Optional description for history tracking.

        Returns:
            Dict[str, Any]: Updated property object from backend.

        Raises:
            NotFoundError: If property doesn't exist.
            UnauthorizedError: If permission denied.
            RuntimeError: For other GraphQL errors.
        """
        # Build mutation - include changedVia only if provided
        if changed_via is not None:
            mutation = (
                "mutation UpdateNumericProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: String, $category: String, $displayUnit: String, "
                "$owner: String, $reason: String, $description: String, $changedVia: ChangedVia) {\n"
                "  updateNumericProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    category: $category\n"
                "    displayUnit: $displayUnit\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "    changedVia: $changedVia\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "    parsedValue\n"
                "    category\n"
                "    displayUnit\n"
                "  }\n"
                "}"
            )
        else:
            mutation = (
                "mutation UpdateNumericProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: String, $category: String, $displayUnit: String, "
                "$owner: String, $reason: String, $description: String) {\n"
                "  updateNumericProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    category: $category\n"
                "    displayUnit: $displayUnit\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "    parsedValue\n"
                "    category\n"
                "    displayUnit\n"
                "  }\n"
                "}"
            )

        variables: Dict[str, Any] = {"id": id}
        if item_id is not None:
            variables["itemId"] = item_id
        if name is not None:
            variables["name"] = name
        if readable_id is not None:
            variables["readableId"] = readable_id
        if position is not None:
            variables["position"] = position
        if value is not None:
            variables["value"] = value
        if category is not None:
            variables["category"] = category
        if display_unit is not None:
            variables["displayUnit"] = display_unit
        if owner is not None:
            variables["owner"] = owner
        if reason is not None:
            variables["reason"] = reason
        if description is not None:
            variables["description"] = description
        if changed_via is not None:
            variables["changedVia"] = changed_via

        resp = self._t.graphql(query=mutation, variables=variables)
        resp.raise_for_status()
        payload = resp.json()

        # CRITICAL: Check for errors FIRST - backend must enforce permissions
        # If a VIEWER user can write, the backend is not properly enforcing permissions
        if "errors" in payload:
            self._handle_graphql_errors(payload["errors"])

        property_data = payload.get("data", {}).get("updateNumericProperty")
        if property_data is None:
            # If we get here without errors but no data, something is wrong
            # This could indicate the backend allowed the mutation but returned no data
            # Check if there are any errors we might have missed
            if "errors" in payload:
                self._handle_graphql_errors(payload["errors"])
            raise RuntimeError("Malformed GraphQL response: missing 'updateNumericProperty' field")

        return property_data

    def update_text_property(
        self,
        *,
        id: str,  # noqa: A002
        value: Optional[str] = None,
        item_id: Optional[str] = None,
        name: Optional[str] = None,
        readable_id: Optional[str] = None,
        position: Optional[float] = None,
        owner: Optional[str] = None,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        changed_via: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a text property via GraphQL mutation.

        Args:
            id: Property ID (required).
            value: New text value.
            item_id: Optional item ID to move property to.
            name: Optional property name.
            readable_id: Optional readable ID.
            position: Optional position for ordering.
            owner: Optional owner.
            reason: Optional reason for history tracking.
            description: Optional description for history tracking.

        Returns:
            Dict[str, Any]: Updated property object from backend.

        Raises:
            NotFoundError: If property doesn't exist.
            UnauthorizedError: If permission denied.
            RuntimeError: For other GraphQL errors.
        """
        # Build mutation - include changedVia only if provided
        if changed_via is not None:
            mutation = (
                "mutation UpdateTextProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: String, $owner: String, $reason: String, $description: String, $changedVia: ChangedVia) {\n"
                "  updateTextProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "    changedVia: $changedVia\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "    parsedValue\n"
                "  }\n"
                "}"
            )
        else:
            mutation = (
                "mutation UpdateTextProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: String, $owner: String, $reason: String, $description: String) {\n"
                "  updateTextProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "    parsedValue\n"
                "  }\n"
                "}"
            )

        variables: Dict[str, Any] = {"id": id}
        if item_id is not None:
            variables["itemId"] = item_id
        if name is not None:
            variables["name"] = name
        if readable_id is not None:
            variables["readableId"] = readable_id
        if position is not None:
            variables["position"] = position
        if value is not None:
            variables["value"] = value
        if owner is not None:
            variables["owner"] = owner
        if reason is not None:
            variables["reason"] = reason
        if description is not None:
            variables["description"] = description
        if changed_via is not None:
            variables["changedVia"] = changed_via

        resp = self._t.graphql(query=mutation, variables=variables)
        resp.raise_for_status()
        payload = resp.json()

        # CRITICAL: Check for errors FIRST - backend must enforce permissions
        # If a VIEWER user can write, the backend is not properly enforcing permissions
        if "errors" in payload:
            self._handle_graphql_errors(payload["errors"])

        property_data = payload.get("data", {}).get("updateTextProperty")
        if property_data is None:
            # If we get here without errors but no data, something is wrong
            if "errors" in payload:
                self._handle_graphql_errors(payload["errors"])
            raise RuntimeError("Malformed GraphQL response: missing 'updateTextProperty' field")

        return property_data

    def update_date_property(
        self,
        *,
        id: str,  # noqa: A002
        value: Optional[str] = None,
        item_id: Optional[str] = None,
        name: Optional[str] = None,
        readable_id: Optional[str] = None,
        position: Optional[float] = None,
        owner: Optional[str] = None,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        changed_via: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a date property via GraphQL mutation.

        Args:
            id: Property ID (required).
            value: New date value in ISO 8601 format (YYYY-MM-DD).
            item_id: Optional item ID to move property to.
            name: Optional property name.
            readable_id: Optional readable ID.
            position: Optional position for ordering.
            owner: Optional owner.
            reason: Optional reason for history tracking.
            description: Optional description for history tracking.

        Returns:
            Dict[str, Any]: Updated property object from backend.

        Raises:
            NotFoundError: If property doesn't exist.
            UnauthorizedError: If permission denied.
            ValueError: If date format is invalid.
            RuntimeError: For other GraphQL errors.
        """
        # Build mutation - include changedVia only if provided
        if changed_via is not None:
            mutation = (
                "mutation UpdateDateProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: String, $owner: String, $reason: String, $description: String, $changedVia: ChangedVia) {\n"
                "  updateDateProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "    changedVia: $changedVia\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "  }\n"
                "}"
            )
        else:
            mutation = (
                "mutation UpdateDateProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: String, $owner: String, $reason: String, $description: String) {\n"
                "  updateDateProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "  }\n"
                "}"
            )

        variables: Dict[str, Any] = {"id": id}
        if item_id is not None:
            variables["itemId"] = item_id
        if name is not None:
            variables["name"] = name
        if readable_id is not None:
            variables["readableId"] = readable_id
        if position is not None:
            variables["position"] = position
        if value is not None:
            variables["value"] = value
        if owner is not None:
            variables["owner"] = owner
        if reason is not None:
            variables["reason"] = reason
        if description is not None:
            variables["description"] = description
        if changed_via is not None:
            variables["changedVia"] = changed_via

        resp = self._t.graphql(query=mutation, variables=variables)
        resp.raise_for_status()
        payload = resp.json()

        # CRITICAL: Check for errors FIRST - backend must enforce permissions
        # If a VIEWER user can write, the backend is not properly enforcing permissions
        if "errors" in payload:
            self._handle_graphql_errors(payload["errors"])

        property_data = payload.get("data", {}).get("updateDateProperty")
        if property_data is None:
            # If we get here without errors but no data, something is wrong
            if "errors" in payload:
                self._handle_graphql_errors(payload["errors"])
            raise RuntimeError("Malformed GraphQL response: missing 'updateDateProperty' field")

        return property_data

    def update_status_property(
        self,
        *,
        id: str,  # noqa: A002
        value: Optional[str] = None,
        item_id: Optional[str] = None,
        name: Optional[str] = None,
        readable_id: Optional[str] = None,
        position: Optional[float] = None,
        owner: Optional[str] = None,
        reason: Optional[str] = None,
        description: Optional[str] = None,
        changed_via: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update a status property via GraphQL mutation.

        Args:
            id: Property ID (required).
            value: New status value (DRAFT, UNDER_REVIEW, or DONE).
            item_id: Optional item ID to move property to.
            name: Optional property name.
            readable_id: Optional readable ID.
            position: Optional position for ordering.
            owner: Optional owner.
            reason: Optional reason for history tracking.
            description: Optional description for history tracking.

        Returns:
            Dict[str, Any]: Updated property object from backend.

        Raises:
            NotFoundError: If property doesn't exist.
            UnauthorizedError: If permission denied.
            ValueError: If status value is invalid.
            RuntimeError: For other GraphQL errors.
        """
        # Build mutation - include changedVia only if provided
        if changed_via is not None:
            mutation = (
                "mutation UpdateStatusProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: StatusPropertyValue, $owner: String, $reason: String, $description: String, $changedVia: ChangedVia) {\n"
                "  updateStatusProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "    changedVia: $changedVia\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "  }\n"
                "}"
            )
        else:
            mutation = (
                "mutation UpdateStatusProperty($id: ID!, $itemId: ID, $name: String, $readableId: String, "
                "$position: Float, $value: StatusPropertyValue, $owner: String, $reason: String, $description: String) {\n"
                "  updateStatusProperty(\n"
                "    id: $id\n"
                "    itemId: $itemId\n"
                "    name: $name\n"
                "    readableId: $readableId\n"
                "    position: $position\n"
                "    value: $value\n"
                "    owner: $owner\n"
                "    reason: $reason\n"
                "    description: $description\n"
                "  ) {\n"
                "    id\n"
                "    readableId\n"
                "    itemId\n"
                "    name\n"
                "    position\n"
                "    value\n"
                "    type\n"
                "    owner\n"
                "    draftPropertyId\n"
                "    deleted\n"
                "    hasChanges\n"
                "  }\n"
                "}"
            )

        variables: Dict[str, Any] = {"id": id}
        if item_id is not None:
            variables["itemId"] = item_id
        if name is not None:
            variables["name"] = name
        if readable_id is not None:
            variables["readableId"] = readable_id
        if position is not None:
            variables["position"] = position
        if value is not None:
            variables["value"] = value
        if owner is not None:
            variables["owner"] = owner
        if reason is not None:
            variables["reason"] = reason
        if description is not None:
            variables["description"] = description
        if changed_via is not None:
            variables["changedVia"] = changed_via

        resp = self._t.graphql(query=mutation, variables=variables)
        resp.raise_for_status()
        payload = resp.json()

        # CRITICAL: Check for errors FIRST - backend must enforce permissions
        # If a VIEWER user can write, the backend is not properly enforcing permissions
        if "errors" in payload:
            self._handle_graphql_errors(payload["errors"])

        property_data = payload.get("data", {}).get("updateStatusProperty")
        if property_data is None:
            # If we get here without errors but no data, something is wrong
            if "errors" in payload:
                self._handle_graphql_errors(payload["errors"])
            raise RuntimeError("Malformed GraphQL response: missing 'updateStatusProperty' field")

        return property_data

    def _handle_graphql_errors(self, errors: list[Dict[str, Any]]) -> None:
        """Handle GraphQL errors and map them to appropriate exceptions.

        Args:
            errors: List of GraphQL error dictionaries.

        Raises:
            NotFoundError: For 'not_found' errors.
            UnauthorizedError: For 'forbidden' errors.
            ValueError: For 'invalid_date_format' or 'invalid_status_value' errors.
            RuntimeError: For other errors.
        """
        if not errors:
            return

        error = errors[0]  # Use first error
        error_code = error.get("extensions", {}).get("code")
        error_message = error.get("message", "GraphQL error")

        if error_code == "not_found":
            raise NotFoundError(404, message=error_message)
        elif error_code == "forbidden":
            # Enhanced error message for permission issues
            enhanced_message = (
                f"{error_message}. "
                "Write operations require EDITOR role for the workspace or product. "
                "Users with VIEWER role can only read data."
            )
            raise UnauthorizedError(403, message=enhanced_message)
        elif error_code == "invalid_date_format":
            raise ValueError(f"Date must be in ISO 8601 format: YYYY-MM-DD. {error_message}")
        elif error_code == "invalid_status_value":
            raise ValueError(f"Status must be one of: DRAFT, UNDER_REVIEW, DONE. {error_message}")
        else:
            raise RuntimeError(f"GraphQL error: {error_message}")

    @staticmethod
    def _convert_numeric_value(value: Any) -> str:
        """Convert a numeric value to JSON string format for GraphQL.

        Args:
            value: Numeric value (int, float, list, or nested list).

        Returns:
            str: JSON string representation of the value.
            Arrays are always formatted as matrices: [[1, 2, 3]] for 1D arrays.
        """
        # If it's a list/array, ensure it's always a matrix (2D array)
        if isinstance(value, (list, tuple)):
            # Handle empty list
            if len(value) == 0:
                value = []
            # Check if it's a 1D array (list of numbers, not nested)
            elif not isinstance(value[0], (list, tuple)):
                # Wrap 1D array in another list to make it a matrix: [1, 2, 3] -> [[1, 2, 3]]
                value = [list(value)]
            else:
                # Already 2D or higher, convert tuples to lists for JSON serialization
                value = [list(row) if isinstance(row, tuple) else row for row in value]
        
        return json.dumps(value)

    @staticmethod
    def _validate_date_format(value: str) -> str:
        """Validate and return date string in ISO 8601 format.

        Args:
            value: Date string to validate.

        Returns:
            str: Validated date string.

        Raises:
            ValueError: If date format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError("Date value must be a string in ISO 8601 format: YYYY-MM-DD")

        # Basic validation: YYYY-MM-DD format
        parts = value.split("-")
        if len(parts) != 3:
            raise ValueError("Date must be in ISO 8601 format: YYYY-MM-DD")

        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            # Basic range checks
            if not (1 <= month <= 12) or not (1 <= day <= 31):
                raise ValueError("Date must be in ISO 8601 format: YYYY-MM-DD")
            # More thorough validation would require datetime, but backend will validate
            return value
        except ValueError as e:
            raise ValueError("Date must be in ISO 8601 format: YYYY-MM-DD") from e

    @staticmethod
    def _validate_status_value(value: str) -> str:
        """Validate status enum value.

        Args:
            value: Status value to validate.

        Returns:
            str: Validated status value.

        Raises:
            ValueError: If status value is invalid.
        """
        valid_statuses = {"DRAFT", "UNDER_REVIEW", "DONE"}
        if value not in valid_statuses:
            raise ValueError(f"Status must be one of: DRAFT, UNDER_REVIEW, DONE. Got: {value}")
        return value

