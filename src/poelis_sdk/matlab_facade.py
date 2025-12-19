from __future__ import annotations

from typing import Any

from .client import PoelisClient


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
                # Check if get_property is available on this node
                if not hasattr(obj, "get_property"):
                    raise RuntimeError(
                        f"Path '{path}' failed: node '{parts[i-1] if i > 0 else 'root'}' "
                        f"does not support property access. get_property() is only available "
                        f"on product, version, or item nodes."
                    )
                
                # Get the property
                try:
                    prop = obj.get_property(name)
                    value = prop.value
                    # Ensure the value is MATLAB-compatible
                    return _ensure_matlab_compatible(value)
                except RuntimeError as e:
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
                if not hasattr(obj, "get_property"):
                    raise RuntimeError(
                        f"Path '{path}' failed: node '{parts[i-1] if i > 0 else 'root'}' "
                        f"does not support property access. get_property() is only available "
                        f"on product, version, or item nodes."
                    )
                
                # Get the property
                try:
                    prop = obj.get_property(name)
                    # Extract all property information
                    info: dict[str, Any] = {
                        "value": _ensure_matlab_compatible(prop.value),
                        "unit": _ensure_matlab_compatible(prop.unit) if hasattr(prop, "unit") else None,
                        "category": _ensure_matlab_compatible(prop.category) if hasattr(prop, "category") else None,
                        "name": _ensure_matlab_compatible(prop.name) if hasattr(prop, "name") else None,
                    }
                    return info
                except RuntimeError as e:
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
                    # Provide helpful error message
                    partial_path = ".".join(parts[:i+1])
                    raise AttributeError(
                        f"Path '{path}' failed: node '{name}' not found at '{partial_path}'. "
                        f"Available nodes can be listed using list_children() method."
                    ) from None
    
    def get_many(self, paths: Any) -> dict[str, Any]:
        """Get multiple property values by their paths.
        
        Args:
            paths: List or tuple of dot-separated paths to properties.
                Can be a Python list/tuple. For MATLAB cell arrays, convert first:
                paths = py.list({'path1', 'path2', 'path3'});
        
        Returns:
            Dictionary mapping each path to its value. If a path fails, the error
            is raised immediately (fail-fast behavior).
        
        Raises:
            ValueError: If paths list is empty or contains invalid paths.
            AttributeError: If an intermediate node doesn't exist.
            RuntimeError: If a property cannot be found.
        
        Example (Python):
            >>> pm = PoelisMatlab(api_key="test")
            >>> values = pm.get_many([
            ...     "workspace.product.property1",
            ...     "workspace.product.property2"
            ... ])
            >>> print(values)  # {'workspace.product.property1': 10.5, ...}
        
        Example (MATLAB):
            paths = {'path1', 'path2', 'path3'};
            paths_py = py.list(paths);
            values = pm.get_many(paths_py);
        """
        # Handle MATLAB cell arrays and Python iterables - convert to Python list
        path_list: list[str] = []
        
        # Convert to list of strings
        try:
            # Try direct iteration first (works for Python lists/tuples and py.list objects)
            for item in paths:
                # Convert item to string (handles MATLAB char arrays and Python strings)
                if isinstance(item, str):
                    path_str = item
                elif hasattr(item, 'char'):
                    # MATLAB char array - convert to string
                    try:
                        path_str = str(item.char())
                    except Exception:
                        path_str = str(item)
                else:
                    path_str = str(item)
                path_list.append(path_str)
        except (TypeError, AttributeError) as e:
            raise ValueError(
                f"Paths must be a list, tuple, or iterable of strings. "
                f"Got: {type(paths)}. Error: {str(e)}. "
                f"In MATLAB, convert cell array to Python list first: "
                f"paths_py = py.list({{'path1', 'path2'}}); pm.get_many(paths_py);"
            ) from e
        
        if not path_list:
            raise ValueError("Paths list cannot be empty")
        
        result: dict[str, Any] = {}
        for path_str in path_list:
            result[path_str] = self.get_value(path_str)
        return result
    
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

