from __future__ import annotations

from typing import Any, Optional

from .client import PoelisClient
from .exceptions import NotFoundError, UnauthorizedError


def _ensure_matlab_compatible(value: Any) -> Any:
    """Convert a value to a MATLAB-compatible type.
    
    Ensures the value is a native Python type (float, int, str, bool, dict, list)
    that MATLAB can handle directly. Recursively converts nested structures.
    
    Args:
        value: The value to convert.
    
    Returns:
        A MATLAB-compatible value (native Python type).
    """
    # Handle None
    if value is None:
        return None
    
    # Handle native numeric types
    if isinstance(value, (int, float, bool, str)):
        return value
    
    # Handle lists - convert to plain Python list
    if isinstance(value, (list, tuple)):
        return [_ensure_matlab_compatible(item) for item in value]
    
    # Handle dicts - convert to plain Python dict
    if isinstance(value, dict):
        return {str(k): _ensure_matlab_compatible(v) for k, v in value.items()}
    
    # For any other type, try to convert to a basic type
    # This handles edge cases where custom objects might slip through
    if hasattr(value, '__dict__'):
        # Convert custom objects to dict representation
        return {str(k): _ensure_matlab_compatible(v) for k, v in value.__dict__.items()}
    
    # Last resort: convert to string
    return str(value)


def _resolve_property_from_node(node: Any, property_name: str) -> Any:
    """Resolve a property from a node, avoiding product-level get_property.
    
    This function ensures MATLAB never calls get_property() directly on product nodes.
    Instead, it routes through baseline/draft or uses item-level property access.
    
    Args:
        node: The node to resolve the property from (product, version, or item).
        property_name: The name/readableId of the property to resolve.
    
    Returns:
        A _PropWrapper object for the property.
    
    Raises:
        RuntimeError: If the property cannot be found.
        AttributeError: If the node doesn't support property access.
    """
    # Check node level
    node_level = getattr(node, "_level", None)
    
    # If we're at a product node, route through baseline (for reads)
    if node_level == "product":
        baseline = getattr(node, "baseline")
        # Recursively resolve from baseline (which is a version node)
        return _resolve_property_from_node(baseline, property_name)
    
    # If we're at a version node, we can't call get_property directly
    # We need to search through items in the version
    if node_level == "version":
        # Load children (items) for this version
        if hasattr(node, "_load_children"):
            node._load_children()
        # Try to find the property by searching through all items
        for item_key, item_node in getattr(node, "_children_cache", {}).items():
            try:
                # Try to get the property from this item
                return _resolve_property_from_node(item_node, property_name)
            except (RuntimeError, AttributeError):
                # Property not found in this item, try next
                continue
        # If we get here, property wasn't found in any item
        raise RuntimeError(
            f"Property '{property_name}' not found in any item of version '{getattr(node, '_name', 'unknown')}'. "
            f"Specify the item in your path, e.g., 'workspace.product.baseline.<item>.{property_name}'"
        )
    
    # For item nodes, try to resolve the property
    if node_level == "item":
        # Try direct attribute access (item.prop_name)
        try:
            prop_wrapper = getattr(node, property_name)
            # Verify it's actually a property wrapper (has .value attribute)
            if hasattr(prop_wrapper, "value"):
                return prop_wrapper
        except AttributeError:
            pass
        
        # Try via props node (item.props.prop_name)
        try:
            props_node = getattr(node, "props")
            prop_wrapper = getattr(props_node, property_name)
            if hasattr(prop_wrapper, "value"):
                return prop_wrapper
        except AttributeError:
            pass
    
    # Fallback: use get_property on item nodes only
    if node_level == "item":
        if hasattr(node, "get_property"):
            return node.get_property(property_name)
    
    # If we get here, the node doesn't support property access
    raise RuntimeError(
        f"Property '{property_name}' cannot be resolved from node level '{node_level}'. "
        f"Property access is only available on item nodes."
    )


def _resolve_property_for_write(node: Any, property_name: str, path: str) -> Any:
    """Resolve a property for writing, ensuring we route through draft and prevent frozen version writes.
    
    This function ensures MATLAB never calls get_property() directly on product nodes for writes.
    It also prevents writes to frozen versions (v1, v2, etc.) and routes through draft.
    
    Args:
        node: The node to resolve the property from (product, version, or item).
        property_name: The name/readableId of the property to resolve.
        path: The full path for error messages.
    
    Returns:
        A _PropWrapper object for the property (must be from draft).
    
    Raises:
        ValueError: If trying to write to a frozen version.
        RuntimeError: If the property cannot be found.
        AttributeError: If the node doesn't support property access.
    """
    # Check node level
    node_level = getattr(node, "_level", None)
    
    # If we're at a product node, route through draft (for writes)
    if node_level == "product":
        draft = getattr(node, "draft")
        # Recursively resolve from draft (which is a version node)
        return _resolve_property_for_write(draft, property_name, path)
    
    # If we're at a version node, check if it's draft and search through items
    if node_level == "version":
        version_name = getattr(node, "_name", None)
        # Check if this is a frozen version (v1, v2, etc.) or baseline
        if version_name and version_name != "draft":
            if version_name == "baseline" or (version_name.startswith("v") and len(version_name) > 1 and version_name[1:].isdigit()):
                raise ValueError(
                    f"Cannot write to frozen version '{version_name}' at path '{path}'. "
                    f"Only draft properties can be updated. Use 'draft' in your path, e.g., "
                    f"'{path.replace(version_name, 'draft')}'"
                )
        # If it's draft, search through items to find the property
        if hasattr(node, "_load_children"):
            node._load_children()
        # Try to find the property by searching through all items
        for item_key, item_node in getattr(node, "_children_cache", {}).items():
            try:
                # Try to get the property from this item
                return _resolve_property_for_write(item_node, property_name, path)
            except (RuntimeError, AttributeError, ValueError):
                # Property not found in this item or write blocked, try next
                continue
        # If we get here, property wasn't found in any item
        raise RuntimeError(
            f"Property '{property_name}' not found in any item of draft version. "
            f"Specify the item in your path, e.g., 'workspace.product.draft.<item>.{property_name}'"
        )
    
    # For item nodes, try to resolve the property
    # First, check if we're at an item node under a frozen version
    if node_level == "item":
        # Check parent version to see if it's frozen
        parent = getattr(node, "_parent", None)
        if parent is not None:
            parent_level = getattr(parent, "_level", None)
            if parent_level == "version":
                version_name = getattr(parent, "_name", None)
                if version_name and version_name != "draft":
                    if version_name == "baseline" or (version_name.startswith("v") and len(version_name) > 1 and version_name[1:].isdigit()):
                        raise ValueError(
                            f"Cannot write to frozen version '{version_name}' at path '{path}'. "
                            f"Only draft properties can be updated. Use 'draft' in your path, e.g., "
                            f"'{path.replace(version_name, 'draft')}'"
                        )
        
        # Try direct attribute access (item.prop_name)
        try:
            prop_wrapper = getattr(node, property_name)
            # Verify it's actually a property wrapper (has .value attribute)
            if hasattr(prop_wrapper, "value"):
                return prop_wrapper
        except AttributeError:
            pass
        
        # Try via props node (item.props.prop_name)
        try:
            props_node = getattr(node, "props")
            prop_wrapper = getattr(props_node, property_name)
            if hasattr(prop_wrapper, "value"):
                return prop_wrapper
        except AttributeError:
            pass
    
    # Fallback: use get_property on item nodes only
    if node_level == "item":
        if hasattr(node, "get_property"):
            return node.get_property(property_name)
    
    # If we get here, the node doesn't support property access
    raise RuntimeError(
        f"Property '{property_name}' cannot be resolved from node level '{node_level}'. "
        f"Property access is only available on item nodes."
    )

"""MATLAB-friendly facade for Poelis Python SDK.

This module provides a simplified, deterministic API that is easy to use from MATLAB.
It abstracts away the dynamic attribute access patterns of the main SDK and provides
a simple path-based interface that returns only MATLAB-compatible types.
"""


class PoelisMatlab:
    """MATLAB-friendly facade for accessing Poelis data.
    
    This class provides a simple, deterministic API for accessing Poelis workspace,
    product, and property data from MATLAB. It wraps the PoelisClient and provides
    a path-based interface that returns only native Python types (float, int, str, bool, dict).
    
    Example usage from Python:
        pm = PoelisMatlab(api_key="your-api-key")
        value = pm.get_value("workspace.product.property")
    
    Example usage from MATLAB:
        pm = py.poelis_sdk.PoelisMatlab('your-api-key');
        value = double(pm.get_value('workspace.product.property'));
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://poelis-be-py-753618215333.europe-west1.run.app",
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialize the MATLAB facade with API credentials.
        
        Args:
            api_key: API key for Poelis API authentication.
            base_url: Base URL of the Poelis API. Defaults to production.
            timeout_seconds: Network timeout in seconds. Defaults to 30.0.
        """
        self.client = PoelisClient(
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
    
    def get_value(self, path: str) -> Any:
        """Get a property value by dot-separated path.
        
        Resolves a path starting from the browser root, navigating through
        workspace → product → (optional version) → item nodes, and finally
        accessing a property. Returns only the property value (not the wrapper object).
        
        Args:
            path: Dot-separated path to the property, e.g., 
                "workspace.product.property" or "workspace.product.v4.property"
        
        Returns:
            The property value as a native Python type (float, int, str, bool, dict, list).
            This is compatible with MATLAB's Python interface.
        
        Raises:
            ValueError: If path is empty or invalid.
            AttributeError: If an intermediate node in the path doesn't exist.
            RuntimeError: If the property cannot be found or if get_property is not
                available on the final node.
        
        Example:
            >>> pm = PoelisMatlab(api_key="test")
            >>> value = pm.get_value("demo_workspace.demo_product.demo_property_mass")
            >>> print(value)  # e.g., 10.5
        """
        if not path or not path.strip():
            raise ValueError("Path cannot be empty")
        
        # Split path into components
        parts = [p.strip() for p in path.split(".") if p.strip()]
        if not parts:
            raise ValueError(f"Invalid path: '{path}' (no valid components after splitting)")
        
        # Start from browser root
        obj = self.client.browser
        
        # Navigate through intermediate nodes
        for i, name in enumerate(parts):
            is_last = i == len(parts) - 1
            
            if is_last:
                # Last element: must be a property
                # Use helper function that avoids calling get_property on product nodes
                try:
                    prop = _resolve_property_from_node(obj, name)
                    value = prop.value
                    # Ensure the value is MATLAB-compatible
                    return _ensure_matlab_compatible(value)
                except (NotFoundError, UnauthorizedError):
                    # Re-raise permission/access errors as-is
                    raise
                except (RuntimeError, AttributeError) as e:
                    # Re-raise with more context
                    raise RuntimeError(
                        f"Property '{name}' not found at path '{path}'. "
                        f"Original error: {str(e)}"
                    ) from e
            else:
                # Intermediate node: try getattr first for version nodes (v1, v2, baseline, draft),
                # then try __getitem__ (handles display names with spaces),
                # then fall back to getattr again (for safe keys)
                try:
                    # Version nodes and special nodes (baseline, draft) are accessed via __getattr__
                    # Check if this looks like a version node or special node
                    is_version_like = (
                        name in ("baseline", "draft") or
                        (name.startswith("v") and len(name) > 1 and name[1:].isdigit())
                    )
                    
                    if is_version_like:
                        # Try getattr first for version nodes
                        obj = getattr(obj, name)
                    elif hasattr(obj, "__getitem__"):
                        # Try __getitem__ for display names with spaces
                        obj = obj[name]
                    else:
                        # Fall back to getattr
                        obj = getattr(obj, name)
                except (KeyError, AttributeError):
                    # If we're at a product node and access failed, try through baseline automatically
                    # This allows paths like "workspace.product.item" to work without specifying "baseline"
                    if hasattr(obj, "_level") and obj._level == "product" and not is_version_like:
                        try:
                            # Try accessing through baseline version (for reads)
                            baseline = getattr(obj, "baseline")
                            # Now try to access the item from baseline
                            if hasattr(baseline, "__getitem__"):
                                obj = baseline[name]
                            else:
                                obj = getattr(baseline, name)
                        except (KeyError, AttributeError):
                            # If baseline access also fails, raise the original error
                            partial_path = ".".join(parts[:i+1])
                            raise AttributeError(
                                f"Path '{path}' failed: node '{name}' not found at '{partial_path}'. "
                                f"Available nodes can be listed using list_children() method."
                            ) from None
                    else:
                        # Provide helpful error message
                        partial_path = ".".join(parts[:i+1])
                        raise AttributeError(
                            f"Path '{path}' failed: node '{name}' not found at '{partial_path}'. "
                            f"Available nodes can be listed using list_children() method."
                        ) from None
    
    def get_property(self, path: str) -> dict[str, Any]:
        """Get property information including value, unit, category, and name.
        
        Args:
            path: Dot-separated path to the property, e.g., 
                "workspace.product.item.property"
        
        Returns:
            Dictionary with keys: 'value', 'unit', 'category', 'name'.
            All values are MATLAB-compatible types.
        
        Raises:
            ValueError: If path is empty or invalid.
            AttributeError: If an intermediate node doesn't exist.
            RuntimeError: If the property cannot be found.
        
        Example:
            >>> pm = PoelisMatlab(api_key="test")
            >>> info = pm.get_property("workspace.product.item.property")
            >>> print(info)  # {'value': 10.5, 'unit': 'kg', 'category': 'Mass', 'name': 'mass_property'}
        """
        if not path or not path.strip():
            raise ValueError("Path cannot be empty")
        
        # Split path into components
        parts = [p.strip() for p in path.split(".") if p.strip()]
        if not parts:
            raise ValueError(f"Invalid path: '{path}' (no valid components after splitting)")
        
        # Start from browser root
        obj = self.client.browser
        
        # Navigate through intermediate nodes
        for i, name in enumerate(parts):
            is_last = i == len(parts) - 1
            
            if is_last:
                # Last element: must be a property
                # Use helper function that avoids calling get_property on product nodes
                try:
                    prop = _resolve_property_from_node(obj, name)
                    # Extract all property information
                    info: dict[str, Any] = {
                        "value": _ensure_matlab_compatible(prop.value),
                        "unit": _ensure_matlab_compatible(prop.unit) if hasattr(prop, "unit") else None,
                        "category": _ensure_matlab_compatible(prop.category) if hasattr(prop, "category") else None,
                        "name": _ensure_matlab_compatible(prop.name) if hasattr(prop, "name") else None,
                    }
                    return info
                except (NotFoundError, UnauthorizedError):
                    # Re-raise permission/access errors as-is
                    raise
                except (RuntimeError, AttributeError) as e:
                    raise RuntimeError(
                        f"Property '{name}' not found at path '{path}'. "
                        f"Original error: {str(e)}"
                    ) from e
            else:
                # Intermediate node: try getattr first for version nodes (v1, v2, baseline, draft),
                # then try __getitem__ (handles display names with spaces),
                # then fall back to getattr again (for safe keys)
                try:
                    # Version nodes and special nodes (baseline, draft) are accessed via __getattr__
                    # Check if this looks like a version node or special node
                    is_version_like = (
                        name in ("baseline", "draft") or
                        (name.startswith("v") and len(name) > 1 and name[1:].isdigit())
                    )
                    
                    if is_version_like:
                        # Try getattr first for version nodes
                        obj = getattr(obj, name)
                    elif hasattr(obj, "__getitem__"):
                        # Try __getitem__ for display names with spaces
                        obj = obj[name]
                    else:
                        # Fall back to getattr
                        obj = getattr(obj, name)
                except (KeyError, AttributeError):
                    # If we're at a product node and access failed, try through baseline automatically
                    if hasattr(obj, "_level") and obj._level == "product" and not is_version_like:
                        try:
                            baseline = getattr(obj, "baseline")
                            if hasattr(baseline, "__getitem__"):
                                obj = baseline[name]
                            else:
                                obj = getattr(baseline, name)
                        except (KeyError, AttributeError):
                            partial_path = ".".join(parts[:i+1])
                            raise AttributeError(
                                f"Path '{path}' failed: node '{name}' not found at '{partial_path}'. "
                                f"Available nodes can be listed using list_children() method."
                            ) from None
                    else:
                        # Provide helpful error message
                        partial_path = ".".join(parts[:i+1])
                        raise AttributeError(
                            f"Path '{path}' failed: node '{name}' not found at '{partial_path}'. "
                            f"Available nodes can be listed using list_children() method."
                        ) from None
    
    def list_children(self, path: str = "") -> list[str]:
        """List child node names at the given path.
        
        Args:
            path: Dot-separated path to the node whose children to list.
                If empty, lists workspaces at the root level.
        
        Returns:
            List of child node names (as strings).
            In MATLAB, access using Python indexing: children = pm.list_children();
            then use children{i} for i = 0:length(children)-1, or convert with:
            cellArray = cell(children); strArray = string(cellArray);
        
        Raises:
            AttributeError: If the path doesn't exist.
        
        Example:
            >>> pm = PoelisMatlab(api_key="test")
            >>> workspaces = pm.list_children()  # Returns list
            >>> # In MATLAB: 
            >>> #   children = pm.list_children();
            >>> #   for i = 0:length(children)-1
            >>> #       name = char(children{i});
            >>> #   end
        """
        # Start from browser root
        obj = self.client.browser
        
        # Navigate to the target node if path is provided
        if path and path.strip():
            parts = [p.strip() for p in path.split(".") if p.strip()]
            for name in parts:
                try:
                    # Version nodes and special nodes are accessed via __getattr__
                    is_version_like = (
                        name in ("baseline", "draft") or
                        (name.startswith("v") and len(name) > 1 and name[1:].isdigit())
                    )
                    
                    if is_version_like:
                        obj = getattr(obj, name)
                    elif hasattr(obj, "__getitem__"):
                        obj = obj[name]
                    else:
                        obj = getattr(obj, name)
                except (KeyError, AttributeError):
                    # If we're at a product node and access failed, try through baseline automatically
                    if hasattr(obj, "_level") and obj._level == "product" and not is_version_like:
                        try:
                            baseline = getattr(obj, "baseline")
                            if hasattr(baseline, "__getitem__"):
                                obj = baseline[name]
                            else:
                                obj = getattr(baseline, name)
                        except (KeyError, AttributeError):
                            raise AttributeError(
                                f"Path '{path}' failed: node '{name}' not found. "
                                f"Cannot list children of non-existent node."
                            ) from None
                    else:
                        raise AttributeError(
                            f"Path '{path}' failed: node '{name}' not found. "
                            f"Cannot list children of non-existent node."
                        ) from None
        
        # Get children using _suggest() if available, otherwise use __dir__()
        if hasattr(obj, "_suggest"):
            suggestions = obj._suggest()
            # Filter out method names, keep only child nodes
            # Methods typically have parentheses or are known method names
            method_names = {
                "list_items", "list_properties", "list_workspaces", "list_products",
                "list_product_versions", "get_property", "get_version", "props"
            }
            children = sorted([s for s in suggestions if s not in method_names])
        else:
            # Fallback to __dir__() and filter out private attributes
            all_attrs = dir(obj)
            children = sorted([attr for attr in all_attrs if not attr.startswith("_")])
        
        # Return as list - MATLAB users should use Python indexing or string() conversion
        return children
    
    def list_properties(self, path: str) -> list[str]:
        """List property names available at the given path.
        
        Args:
            path: Dot-separated path to an item, version, or product node.
                The path should end at a node that supports properties.
        
        Returns:
            List of property names (readableIds) available at this path.
            In MATLAB, access using Python indexing or convert with:
            cellArray = cell(properties); strArray = string(cellArray);
        
        Raises:
            AttributeError: If the path doesn't exist.
            RuntimeError: If the node at the path doesn't support property listing.
        
        Example:
            >>> pm = PoelisMatlab(api_key="test")
            >>> props = pm.list_properties("workspace.product.item")
            >>> # In MATLAB: 
            >>> #   props = pm.list_properties(path);
            >>> #   strArray = string(cell(props));
        """
        if not path or not path.strip():
            raise ValueError("Path cannot be empty for list_properties")
        
        # Navigate to the target node
        parts = [p.strip() for p in path.split(".") if p.strip()]
        obj = self.client.browser
        
        for name in parts:
            try:
                # Version nodes and special nodes are accessed via __getattr__
                is_version_like = (
                    name in ("baseline", "draft") or
                    (name.startswith("v") and len(name) > 1 and name[1:].isdigit())
                )
                
                if is_version_like:
                    obj = getattr(obj, name)
                elif hasattr(obj, "__getitem__"):
                    obj = obj[name]
                else:
                    obj = getattr(obj, name)
            except (KeyError, AttributeError):
                # If we're at a product node and access failed, try through baseline automatically
                if hasattr(obj, "_level") and obj._level == "product" and not is_version_like:
                    try:
                        baseline = getattr(obj, "baseline")
                        if hasattr(baseline, "__getitem__"):
                            obj = baseline[name]
                        else:
                            obj = getattr(baseline, name)
                    except (KeyError, AttributeError):
                        raise AttributeError(
                            f"Path '{path}' failed: node '{name}' not found. "
                            f"Cannot list properties of non-existent node."
                        ) from None
                else:
                    raise AttributeError(
                        f"Path '{path}' failed: node '{name}' not found. "
                        f"Cannot list properties of non-existent node."
                    ) from None
        
        # Check if list_properties method is available
        if not hasattr(obj, "list_properties"):
            raise RuntimeError(
                f"Path '{path}' does not support property listing. "
                f"list_properties() is only available on item, version, or product nodes."
            )
        
        # Call list_properties and extract names
        try:
            prop_list = obj.list_properties()
            # prop_list is a _NodeList with a .names property
            if hasattr(prop_list, "names"):
                properties = list(prop_list.names)
            else:
                # Fallback: try to iterate and extract names
                properties = [str(item) for item in prop_list]
            
            # Return as list - MATLAB users should use string() conversion
            return properties
        except Exception as e:
            raise RuntimeError(
                f"Error listing properties at path '{path}': {str(e)}"
            ) from e
    
    def change_property(
        self,
        path: str,
        value: Any,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """Update a property value by dot-separated path.
        
        Resolves a path starting from the browser root, navigating through
        workspace → product → (optional version) → item nodes, and finally
        accessing a property to update its value. Only draft properties can be updated.
        Requires EDITOR role for the workspace or product.
        
        Args:
            path: Dot-separated path to the property, e.g., 
                "workspace.product.item.property" or "workspace.product.draft.item.property"
            value: New value for the property. Format depends on property type:
                - Numeric: number or 1D array (will be converted to JSON string)
                - Text: string
                - Date: string in ISO 8601 format (YYYY-MM-DD)
                - Status: string (DRAFT, UNDER_REVIEW, or DONE)
                - Formula: read-only
                - Matrix: 2D array (will be converted to JSON string)
            title: Optional title/reason for history tracking.
            description: Optional description for history tracking.
        
        Raises:
            ValueError: If path is empty, invalid, or property is versioned (not draft).
            AttributeError: If an intermediate node in the path doesn't exist.
            RuntimeError: If the property cannot be found or cannot be updated.
            UnauthorizedError: If permission denied (requires EDITOR role; VIEWER role is read-only).
        
        Note:
            Write permissions are enforced by the backend. Users with VIEWER role will receive
            an UnauthorizedError. Only users with EDITOR role for the workspace or product can
            update property values.
        
        Example:
            >>> pm = PoelisMatlab(api_key="test")
            >>> pm.change_property("demo_workspace.demo_product.draft.item.mass", 123.45, title="Updated mass")
            
            In MATLAB:
                pm = py.poelis_sdk.PoelisMatlab('your-api-key');
                pm.change_property('workspace.product.draft.item.property', 123.45, 'title', pyargs('title', 'Updated mass'));
        """
        if not path or not path.strip():
            raise ValueError("Path cannot be empty")
        
        # Split path into components
        parts = [p.strip() for p in path.split(".") if p.strip()]
        if not parts:
            raise ValueError(f"Invalid path: '{path}' (no valid components after splitting)")
        
        # Start from browser root
        obj = self.client.browser
        
        # Navigate through intermediate nodes
        for i, name in enumerate(parts):
            is_last = i == len(parts) - 1
            
            if is_last:
                # Last element: must be a property
                # Use helper function that routes through draft and prevents frozen version writes
                try:
                    prop = _resolve_property_for_write(obj, name, path)
                    # Call change_property on the property wrapper with changed_via='MATLAB_SDK'
                    prop.change_property(value, title=title, description=description, changed_via="MATLAB_SDK")
                except (NotFoundError, UnauthorizedError):
                    # Re-raise permission/access errors as-is
                    raise
                except RuntimeError as e:
                    # Re-raise with more context
                    raise RuntimeError(
                        f"Property '{name}' not found at path '{path}'. "
                        f"Original error: {str(e)}"
                    ) from e
                except ValueError as e:
                    # Re-raise ValueError (e.g., versioned property, invalid format, frozen version)
                    raise ValueError(
                        f"Cannot update property '{name}' at path '{path}': {str(e)}"
                    ) from e
            else:
                # Intermediate node: try getattr first for version nodes (v1, v2, baseline, draft),
                # then try __getitem__ (handles display names with spaces),
                # then fall back to getattr again (for safe keys)
                try:
                    # Version nodes and special nodes (baseline, draft) are accessed via __getattr__
                    # Check if this looks like a version node or special node
                    is_version_like = (
                        name in ("baseline", "draft") or
                        (name.startswith("v") and len(name) > 1 and name[1:].isdigit())
                    )
                    
                    if is_version_like:
                        # Try getattr first for version nodes
                        obj = getattr(obj, name)
                    elif hasattr(obj, "__getitem__"):
                        # Try __getitem__ for display names with spaces
                        obj = obj[name]
                    else:
                        # Fall back to getattr
                        obj = getattr(obj, name)
                except (KeyError, AttributeError):
                    # If we're at a product node and access failed, try through draft automatically
                    # This allows paths like "workspace.product.item" to work for writes without specifying "draft"
                    # For writes, we always route through draft (not baseline)
                    if hasattr(obj, "_level") and obj._level == "product" and not is_version_like:
                        try:
                            # Try accessing through draft version (for writes)
                            draft = getattr(obj, "draft")
                            # Now try to access the item from draft
                            if hasattr(draft, "__getitem__"):
                                obj = draft[name]
                            else:
                                obj = getattr(draft, name)
                        except (KeyError, AttributeError):
                            # If draft access also fails, raise the original error
                            partial_path = ".".join(parts[:i+1])
                            raise AttributeError(
                                f"Path '{path}' failed: node '{name}' not found at '{partial_path}'. "
                                f"Available nodes can be listed using list_children() method."
                            ) from None
                    else:
                        # Provide helpful error message
                        partial_path = ".".join(parts[:i+1])
                        raise AttributeError(
                            f"Path '{path}' failed: node '{name}' not found at '{partial_path}'. "
                            f"Available nodes can be listed using list_children() method."
                        ) from None

