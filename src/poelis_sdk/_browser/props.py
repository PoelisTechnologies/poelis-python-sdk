"""Property wrappers and property list nodes for the Browser DSL (internal)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..exceptions import NotFoundError, UnauthorizedError
from .utils import _safe_key

if TYPE_CHECKING:  # pragma: no cover
    from .nodes import _Node


class _PropsNode:
    """Pseudo-node that exposes item properties as child attributes by display name.

    Usage: item.props.<Property_Name> or item.props["Property Name"].
    Returns the raw property dictionaries from GraphQL.
    """

    def __init__(self, item_node: "_Node") -> None:
        self._item = item_node
        self._children_cache: Dict[str, _PropWrapper] = {}
        self._names: List[str] = []
        self._loaded_at: Optional[float] = None
        self._cache_ttl: float = item_node._cache_ttl  # Inherit cache TTL from parent node

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        return f"<props of {self._item.name or self._item.id}>"

    def _ensure_loaded(self) -> None:
        # Performance optimization: only load if cache is stale or empty
        if self._children_cache and self._loaded_at is not None:
            if time.time() - self._loaded_at <= self._cache_ttl:
                return

        props = self._item._properties()
        used_names: Dict[str, int] = {}
        names_list = []
        for i, pr in enumerate(props):
            # Try to get name from various possible fields
            display = pr.get("readableId") or pr.get("name") or pr.get("id") or pr.get("category") or f"property_{i}"
            safe = _safe_key(str(display))

            # Handle duplicate names by adding a suffix
            if safe in used_names:
                used_names[safe] += 1
                safe = f"{safe}_{used_names[safe]}"
            else:
                used_names[safe] = 0

            self._children_cache[safe] = _PropWrapper(pr, client=self._item._client)
            names_list.append(display)
        self._names = names_list
        self._loaded_at = time.time()

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        self._ensure_loaded()
        return sorted(list(self._children_cache.keys()))

    # names() removed; use item.list_properties().names instead

    def __getattr__(self, attr: str) -> Any:
        self._ensure_loaded()
        if attr in self._children_cache:
            prop_wrapper = self._children_cache[attr]
            # Track accessed properties for deletion detection
            if self._item._client is not None:
                try:
                    change_tracker = getattr(self._item._client, "_change_tracker", None)
                    if change_tracker is not None and change_tracker.is_enabled():
                        property_path = self._item._build_path(attr)
                        if property_path:
                            prop_name = (
                                getattr(prop_wrapper, "_raw", {}).get("readableId")
                                or getattr(prop_wrapper, "_raw", {}).get("name")
                                or attr
                            )
                            prop_id = getattr(prop_wrapper, "_raw", {}).get("id")
                            change_tracker.record_accessed_property(property_path, prop_name, prop_id)
                except Exception:
                    pass  # Silently ignore tracking errors
            return prop_wrapper

        # Check if property was previously accessed (deletion detection)
        if self._item._client is not None:
            try:
                change_tracker = getattr(self._item._client, "_change_tracker", None)
                if change_tracker is not None and change_tracker.is_enabled():
                    property_path = self._item._build_path(attr)
                    if property_path:
                        change_tracker.warn_if_deleted(property_path=property_path)
            except Exception:
                pass  # Silently ignore tracking errors

        raise AttributeError(attr)

    def __getitem__(self, key: str) -> Any:
        self._ensure_loaded()
        if key in self._children_cache:
            return self._children_cache[key]
        # match by display name
        for safe, data in self._children_cache.items():
            try:
                raw = getattr(data, "_raw", {})
                if raw.get("readableId") == key or raw.get("name") == key:  # type: ignore[arg-type]
                    return data
            except Exception:
                continue
        safe = _safe_key(key)
        if safe in self._children_cache:
            return self._children_cache[safe]
        raise KeyError(key)

    # keep suggest internal so it doesn't appear in help/dir
    def _suggest(self) -> List[str]:
        self._ensure_loaded()
        return sorted(list(self._children_cache.keys()))


class _NodeList:
    """Lightweight sequence wrapper for node/property lists with `.names`.

    Provides iteration and index access to underlying items, plus a `.names`
    attribute returning the display names in the same order.
    """

    def __init__(self, items: List[Any], names: List[str]) -> None:
        self._items = list(items)
        self._names = list(names)

    def __iter__(self):  # pragma: no cover - trivial
        return iter(self._items)

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._items)

    def __getitem__(self, idx: int) -> Any:  # pragma: no cover - trivial
        return self._items[idx]

    @property
    def names(self) -> List[str]:
        return list(self._names)


class _PropWrapper:
    """Lightweight accessor for a property dict, exposing `.value` and `.raw`.

    Normalizes different property result shapes (union vs search) into `.value`.
    """

    def __init__(self, prop: Dict[str, Any], client: Any = None) -> None:
        """Initialize property wrapper.

        Args:
            prop: Property dictionary from GraphQL.
            client: Optional PoelisClient instance for change tracking.
        """
        self._raw = prop
        self._client = client

    def _get_property_value(self) -> Any:
        """Extract and parse the property value from raw data.

        Returns:
            Any: The parsed property value.
        """
        p = self._raw
        # Use parsedValue if available and not None (new backend feature)
        if "parsedValue" in p:
            parsed_val = p.get("parsedValue")
            if parsed_val is not None:
                # Recursively parse arrays/matrices that might contain string numbers
                return self._parse_nested_value(parsed_val)
        # Fallback to legacy parsing logic for backward compatibility
        # searchProperties shape
        if "numericValue" in p and p.get("numericValue") is not None:
            return p["numericValue"]
        if "textValue" in p and p.get("textValue") is not None:
            return p["textValue"]
        if "dateValue" in p and p.get("dateValue") is not None:
            return p["dateValue"]
        # union shape
        if "integerPart" in p:
            integer_part = p.get("integerPart")
            exponent = p.get("exponent", 0) or 0
            try:
                return (integer_part or 0) * (10 ** int(exponent))
            except Exception:
                return integer_part
        # If parsedValue was None or missing, try to parse the raw value for numeric/formula/matrix
        if "value" in p:
            raw_value = p.get("value")
            property_type = (p.get("__typename") or p.get("propertyType") or "").lower()
            is_numeric = property_type in ("numericproperty", "numeric", "formulaproperty", "formula", "matrixproperty", "matrix")
            if raw_value is None:
                return None  # invalid formula or missing value
            if isinstance(raw_value, str) and is_numeric:
                try:
                    # Try to parse as float first (handles decimals), then int
                    parsed = float(raw_value)
                    # Return int if it's a whole number, otherwise float
                    return int(parsed) if parsed.is_integer() else parsed
                except (ValueError, TypeError):
                    # If parsing fails, return the raw string
                    return raw_value
            return raw_value
        return None

    @property
    def value(self) -> Any:  # type: ignore[override]
        """Get the property value, with change detection if enabled.

        Returns:
            Any: The property value.
        """
        current_value = self._get_property_value()

        # Check for backend-side changes if client is available and change
        # detection is enabled. This compares the current value to the
        # persisted baseline across runs.
        if self._client is not None:
            try:
                change_tracker = getattr(self._client, "_change_tracker", None)
                if change_tracker is not None and change_tracker.is_enabled():
                    # Skip tracking for versioned properties (they're immutable)
                    # Versioned properties have productVersionNumber set
                    if self._raw.get("productVersionNumber") is not None:
                        return current_value

                    # Get property ID for tracking
                    property_id = self._raw.get("id")
                    if property_id:
                        # Get property name for warning message
                        prop_name = (
                            self._raw.get("readableId")
                            or self._raw.get("name")
                            or self._raw.get("id")
                        )
                        # Get updatedAt and updatedBy if available (from sdkProperties)
                        updated_at = self._raw.get("updatedAt")
                        updated_by = self._raw.get("updatedBy")
                        # Check and warn if changed; path will be inferred from
                        # previously recorded accessed_properties when possible.
                        change_tracker.warn_if_changed(
                            property_id=property_id,
                            current_value=current_value,
                            name=prop_name,
                            updated_at=updated_at,
                            updated_by=updated_by,
                        )
            except Exception:
                # Silently ignore errors in change tracking to avoid breaking property access
                pass

        return current_value

    @value.setter
    def value(self, new_value: Any) -> None:
        """Set the property value and emit a local change warning if enabled.

        This is primarily intended for notebook/script usage, e.g.::

            mass = ws.demo_product.draft.get_property("demo_property_mass")
            mass.value = 123.4

        The setter updates the in-memory value and asks the ``PropertyChangeTracker``
        to emit a warning and log entry for this local edit. It does not push the
        change back to the Poelis backend.
        """
        if self._raw.get("formulaExpression") is not None or self._raw.get("formulaDependencies"):
            raise ValueError(
                "Formula properties cannot be updated via the SDK. "
                "They are computed from their expression and dependencies."
            )
        old_value = self._get_property_value()

        # If the value did not actually change, do nothing.
        if old_value == new_value:
            return

        # Update the raw payload with the new value. We prefer the canonical
        # "value" field when present; for legacy shapes we still populate it so
        # subsequent reads see the edited value.
        try:
            self._raw["value"] = new_value
        except Exception:
            # If raw is not a standard dict-like, best-effort: ignore.
            pass

        # Emit a local edit warning through the change tracker when available.
        if self._client is not None:
            try:
                change_tracker = getattr(self._client, "_change_tracker", None)
                if change_tracker is not None and change_tracker.is_enabled():
                    property_id = self._raw.get("id")
                    prop_name = (
                        self._raw.get("readableId")
                        or self._raw.get("name")
                        or self._raw.get("id")
                    )
                    change_tracker.warn_on_local_edit(
                        property_id=property_id,
                        old_value=old_value,
                        new_value=new_value,
                        name=prop_name,
                    )
            except Exception:
                # Silently ignore tracking errors; setting the value itself should not fail.
                pass

    def _parse_nested_value(self, value: Any) -> Any:
        """Recursively parse nested lists/arrays that might contain string numbers."""
        if isinstance(value, list):
            return [self._parse_nested_value(item) for item in value]
        elif isinstance(value, str):
            # Try to parse string as number if it looks numeric
            if self._looks_like_number(value):
                try:
                    parsed = float(value)
                    return int(parsed) if parsed.is_integer() else parsed
                except (ValueError, TypeError):
                    return value
            return value
        else:
            # Already a number or other type, return as-is
            return value

    def _looks_like_number(self, value: str) -> bool:
        """Check if a string value looks like a numeric value."""
        if not isinstance(value, str):
            return False
        value = value.strip()
        if not value:
            return False
        # Allow optional leading sign, digits, optional decimal point, optional exponent
        # This matches patterns like: "123", "-45.67", "1.23e-4", "+100"
        try:
            float(value)
            return True
        except ValueError:
            return False

    def change_property(
        self,
        value: Any,
        title: Optional[str] = None,
        description: Optional[str] = None,
        changed_via: Optional[str] = None,
    ) -> None:
        """Update the property value via the backend.

        Updates the property value by calling the appropriate GraphQL mutation.
        Only draft properties can be updated. Requires EDITOR role for the workspace or product.

        Args:
            value: New value for the property. Format depends on property type:
                - Numeric: number or array (will be converted to JSON string)
                - Text: string
                - Date: string in ISO 8601 format (YYYY-MM-DD)
                - Status: string (DRAFT, UNDER_REVIEW, or DONE)
                - Formula: read-only
                - Matrix: 2D array (will be converted to JSON string)
            title: Optional title/reason for history tracking (mapped to 'reason' in mutation).
            description: Optional description for history tracking.

        Raises:
            ValueError: If property is versioned (not draft), or if value format is invalid.
            NotFoundError: If property doesn't exist.
            UnauthorizedError: If permission denied (requires EDITOR role; VIEWER role is read-only).
            RuntimeError: For other GraphQL errors.

        Note:
            Write permissions are enforced by the backend. Users with VIEWER role will receive
            an UnauthorizedError. Only users with EDITOR role for the workspace or product can
            update property values.

        Example:
            >>> item.prop.change_property(123.45, title='Updated mass', description='Changed mass value')
        """
        # Check if property is draft (only draft properties can be updated)
        if self._raw.get("productVersionNumber") is not None:
            raise ValueError(
                "Cannot update versioned property. Only draft properties can be updated. "
                "Use product.draft.get_property() to access the draft version."
            )

        # Get property ID
        property_id = self._raw.get("id")
        if not property_id:
            raise RuntimeError("Property ID not found in property data")

        # Get PropertiesClient from client
        if self._client is None:
            raise RuntimeError("Client not available. Cannot update property without client connection.")

        properties_client = getattr(self._client, "properties", None)
        if properties_client is None:
            raise RuntimeError("Properties client not available. Cannot update property.")

        if self._raw.get("formulaExpression") is not None or self._raw.get("formulaDependencies"):
            raise ValueError(
                "Formula properties cannot be updated via the SDK. "
                "They are computed from their expression and dependencies."
            )

        # Determine property type from _raw data
        property_type = self._get_property_type()
        if property_type == "formula":
            raise ValueError(
                "Formula properties cannot be updated via the SDK. "
                "They are computed from their expression and dependencies."
            )
        # Build mutation parameters
        mutation_params: Dict[str, Any] = {"id": property_id}

        # Convert value based on property type
        converted_value = self._convert_value_for_mutation(value, property_type)
        mutation_params["value"] = converted_value

        # Add reason (from title) and description if provided
        if title is not None:
            mutation_params["reason"] = title
        if description is not None:
            mutation_params["description"] = description

        # Add changed_via if provided (e.g., "MATLAB_SDK" from MATLAB, "PYTHON_SDK" from Python)
        if changed_via is not None:
            mutation_params["changed_via"] = changed_via

        # Call appropriate mutation based on property type
        try:
            if property_type == "numeric":
                updated_property = properties_client.update_numeric_property(**mutation_params)
            elif property_type == "matrix":
                updated_property = properties_client.update_numeric_property(**mutation_params)
            elif property_type == "text":
                updated_property = properties_client.update_text_property(**mutation_params)
            elif property_type == "date":
                updated_property = properties_client.update_date_property(**mutation_params)
            elif property_type == "status":
                updated_property = properties_client.update_status_property(**mutation_params)
            else:
                raise RuntimeError(f"Unknown property type: {property_type}")

            # Update _raw with response from backend
            self._raw.update(updated_property)

            # Update change tracking baseline after successful write
            if self._client is not None:
                try:
                    change_tracker = getattr(self._client, "_change_tracker", None)
                    if change_tracker is not None and change_tracker.is_enabled():
                        property_id = self._raw.get("id")
                        if property_id:
                            # Update baseline with new value
                            new_value = self._get_property_value()
                            change_tracker.record_accessed_property(
                                property_path=None,  # Path not needed for baseline update
                                property_name=self._raw.get("readableId") or self._raw.get("name") or property_id,
                                property_id=property_id,
                            )
                            # Update baseline directly
                            if hasattr(change_tracker, "_baselines"):
                                change_tracker._baselines[property_id] = {
                                    "value": new_value,
                                    "updated_at": self._raw.get("updatedAt"),
                                    "updated_by": self._raw.get("updatedBy"),
                                }
                except Exception:
                    # Silently ignore tracking errors
                    pass

        except (NotFoundError, UnauthorizedError, ValueError, RuntimeError):
            # Re-raise these exceptions as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            raise RuntimeError(f"Failed to update property: {str(e)}") from e

    def _get_property_type(self) -> str:
        """Determine property type from _raw data.

        Returns:
            str: Property type ('numeric', 'text', 'date', 'status', 'formula', 'matrix').

        Raises:
            RuntimeError: If property type cannot be determined.
        """
        # Try __typename first (from GraphQL union types)
        typename = self._raw.get("__typename", "").lower()
        if "numeric" in typename:
            return "numeric"
        elif "formula" in typename:
            return "formula"
        elif "matrix" in typename:
            return "matrix"
        elif "text" in typename:
            return "text"
        elif "date" in typename:
            return "date"
        elif "status" in typename:
            return "status"

        # Try propertyType field
        prop_type = self._raw.get("propertyType", "").lower()
        if prop_type in ("numeric", "numericproperty"):
            return "numeric"
        elif prop_type in ("formula", "formulaproperty"):
            return "formula"
        elif prop_type in ("matrix", "matrixproperty"):
            return "matrix"
        elif prop_type in ("text", "textproperty"):
            return "text"
        elif prop_type in ("date", "dateproperty"):
            return "date"
        elif prop_type in ("status", "statusproperty"):
            return "status"

        # Try type field
        type_field = self._raw.get("type", "").lower()
        if type_field in ("numeric", "text", "date", "status", "formula", "matrix"):
            return type_field

        raise RuntimeError(f"Could not determine property type from property data: {self._raw}")

    def _convert_value_for_mutation(self, value: Any, property_type: str) -> str:
        """Convert a value to the format expected by GraphQL mutations.

        Args:
            value: Value to convert.
            property_type: Property type ('numeric', 'text', 'date', 'status').

        Returns:
            str: Converted value as string.

        Raises:
            ValueError: If value format is invalid.
        """
        from ..properties import PropertiesClient

        if property_type == "numeric":
            # Convert to JSON string (handles numbers, arrays, matrices)
            return PropertiesClient._convert_numeric_value(value)
        elif property_type == "formula":
            raise ValueError(
                "Formula properties cannot be updated via the SDK. "
                "They are computed from their expression and dependencies."
            )
        elif property_type == "matrix":
            return PropertiesClient._convert_numeric_value(value)
        elif property_type == "text":
            # Text values are passed as strings directly
            if not isinstance(value, str):
                return str(value)
            return value
        elif property_type == "date":
            # Validate and return ISO 8601 date format
            if not isinstance(value, str):
                raise ValueError("Date value must be a string in ISO 8601 format: YYYY-MM-DD")
            return PropertiesClient._validate_date_format(value)
        elif property_type == "status":
            # Validate status enum
            if not isinstance(value, str):
                raise ValueError("Status value must be a string: DRAFT, UNDER_REVIEW, or DONE")
            return PropertiesClient._validate_status_value(value)
        else:
            raise ValueError(f"Unknown property type for value conversion: {property_type}")

    @property
    def category(self) -> Optional[str]:
        """Return the category for this property.

        Note: Category values are normalized/canonicalized by the backend.
        Values may be upper-cased and some previously distinct categories
        may have been merged into canonical forms.

        Returns:
            Optional[str]: The category string, or None if not available.
        """
        p = self._raw
        cat = p.get("category")
        return str(cat) if cat is not None else None

    @property
    def unit(self) -> Optional[str]:
        """Return the display unit for this property.

        Returns:
            Optional[str]: The unit string (e.g., "kg", "°C"), or None if not available.
        """
        p = self._raw
        unit = p.get("displayUnit") or p.get("display_unit")
        return str(unit) if unit is not None else None

    @property
    def name(self) -> Optional[str]:
        """Return the best-effort display name for this property.

        Falls back to name, id, or category when readableId is not present.
        """
        p = self._raw
        n = p.get("readableId") or p.get("name") or p.get("id") or p.get("category")
        return str(n) if n is not None else None

    def __dir__(self) -> List[str]:  # pragma: no cover - notebook UX
        # Expose only the minimal attributes for browsing
        return ["value", "category", "unit", "change_property"]

    def __repr__(self) -> str:  # pragma: no cover - notebook UX
        name = self._raw.get("readableId") or self._raw.get("name") or self._raw.get("id")
        return f"<property {name}: {self.value}>"

    def __str__(self) -> str:  # pragma: no cover - notebook UX
        """Return the display name for this property for string conversion.

        This allows printing a property object directly (e.g., ``print(prop)``)
        and seeing its human-friendly name instead of the full representation.

        Returns:
            str: The best-effort display name, or an empty string if unknown.
        """
        return self.name or ""


