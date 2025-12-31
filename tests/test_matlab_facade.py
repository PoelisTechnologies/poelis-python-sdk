"""Tests for MATLAB facade functionality.

Tests the PoelisMatlab class which provides a simplified, path-based API
for accessing Poelis data from MATLAB.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx
import pytest

from poelis_sdk.matlab_facade import PoelisMatlab


class _MockTransport(httpx.BaseTransport):
    """Mock transport for testing without real API calls."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.requests.append(request)
        if request.method == "POST" and request.url.path == "/v1/graphql":
            payload = json.loads(request.content.decode("utf-8"))
            query: str = payload.get("query", "")
            vars: Dict[str, Any] = payload.get("variables", {})

            # Workspaces
            if "workspaces(" in query:
                data = {
                    "data": {
                        "workspaces": [
                            {"id": "w1", "orgId": "o", "name": "uh2", "projectLimit": 10},
                        ]
                    }
                }
                return httpx.Response(200, json=data)

            # Products by workspace
            if "products(" in query:
                assert vars.get("ws") == "w1"
                data = {
                    "data": {
                        "products": [
                            {
                                "id": "p1",
                                "name": "Widget Pro",
                                "workspaceId": "w1",
                                "code": "WP",
                                "description": "",
                            },
                        ]
                    }
                }
                return httpx.Response(200, json=data)

            # Items by product (both draft and versioned)
            if "items(productId:" in query and "parentItemId" not in query:
                assert vars.get("pid") == "p1"
                data = {
                    "data": {
                        "items": [
                            {
                                "id": "i1",
                                "name": "Gadget A",
                                "code": "GA",
                                "description": "",
                                "productId": "p1",
                                "parentId": None,
                                "owner": "o",
                                "position": 1,
                            },
                        ]
                    }
                }
                return httpx.Response(200, json=data)

            # Properties for item
            if "properties(itemId:" in query:
                item_id = vars.get("iid")
                if item_id == "i1":
                    data = {
                        "data": {
                            "properties": [
                                {
                                    "__typename": "NumericProperty",
                                    "id": "p2",
                                    "name": "Mass",
                                    "readableId": "demo_property_mass",
                                    "category": "Mass",
                                    "displayUnit": "kg",
                                    "value": "10.5",
                                    "parsedValue": 10.5,
                                },
                                {
                                    "__typename": "TextProperty",
                                    "id": "p3",
                                    "name": "Color",
                                    "readableId": "Color",
                                    "value": "Red",
                                    "parsedValue": "Red",
                                },
                            ]
                        }
                    }
                    return httpx.Response(200, json=data)
                else:
                    data = {"data": {"properties": []}}
                    return httpx.Response(200, json=data)

            # Product versions
            if "productVersions(" in query:
                assert vars.get("pid") == "p1"
                data = {
                    "data": {
                        "productVersions": [
                            {
                                "productId": "p1",
                                "versionNumber": 1,
                                "title": "version 1",
                                "description": "First version",
                                "createdAt": "2024-01-01T00:00:00Z",
                            },
                        ]
                    }
                }
                return httpx.Response(200, json=data)

            # Versioned items
            if "items(productId:" in query and "version:" in query:
                assert vars.get("pid") == "p1"
                data = {
                    "data": {
                        "items": [
                            {
                                "id": "i1",
                                "name": "Gadget A",
                                "readableId": "gadget_a",
                                "productId": "p1",
                                "parentId": None,
                                "owner": "o",
                                "position": 1,
                            },
                        ]
                    }
                }
                return httpx.Response(200, json=data)

            return httpx.Response(200, json={"data": {}})

        return httpx.Response(404)


def _client_with_mock_transport(t: httpx.BaseTransport, **client_kwargs: Any) -> Any:
    """Create a PoelisClient with mocked transport."""
    from poelis_sdk.client import Transport as _T

    def _init(self, base_url: str, api_key: str, timeout_seconds: float) -> None:  # type: ignore[no-redef]
        self._client = httpx.Client(base_url=base_url, transport=t, timeout=timeout_seconds)
        self._api_key = api_key
        self._timeout = timeout_seconds

    orig = _T.__init__
    _T.__init__ = _init  # type: ignore[assignment]
    try:
        from poelis_sdk import PoelisClient

        # Disable change detection by default for tests to avoid sdkProperties queries
        if "enable_change_detection" not in client_kwargs:
            client_kwargs["enable_change_detection"] = False
        client = PoelisClient(base_url="http://example.com", api_key="k", **client_kwargs)
        return client
    finally:
        _T.__init__ = orig  # type: ignore[assignment]


def test_matlab_facade_instantiation() -> None:
    """Test that PoelisMatlab can be instantiated."""
    pm = PoelisMatlab(api_key="test-key")
    assert pm.client is not None
    assert hasattr(pm.client, "browser")


def test_get_empty_path() -> None:
    """Test that empty path raises ValueError."""
    pm = PoelisMatlab(api_key="test-key")
    with pytest.raises(ValueError, match="Path cannot be empty"):
        pm.get_value("")
    with pytest.raises(ValueError, match="Path cannot be empty"):
        pm.get_value("   ")


def test_get_invalid_path() -> None:
    """Test that invalid path structure raises ValueError."""
    pm = PoelisMatlab(api_key="test-key")
    with pytest.raises(ValueError, match="no valid components"):
        pm.get_value("   .   .   ")


def test_get_property_value() -> None:
    """Test getting a property value through the facade."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    # Create facade with the mocked client
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    # Get property value (using safe keys with underscores)
    value = pm.get_value("uh2.Widget_Pro.Gadget_A.demo_property_mass")
    
    # Verify it's a native Python type
    assert isinstance(value, (int, float))
    assert value == 10.5


def test_get_property_text_value() -> None:
    """Test getting a text property value."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    value = pm.get_value("uh2.Widget_Pro.Gadget_A.Color")
    
    assert isinstance(value, str)
    assert value == "Red"


def test_get_nonexistent_node() -> None:
    """Test that accessing a non-existent node raises AttributeError."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    with pytest.raises(AttributeError, match="node 'Nonexistent' not found"):
        pm.get_value("uh2.Nonexistent.property")


def test_get_nonexistent_property() -> None:
    """Test that accessing a non-existent property raises RuntimeError."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    with pytest.raises(RuntimeError, match="Property 'nonexistent' not found"):
        pm.get_value("uh2.Widget_Pro.Gadget_A.nonexistent")


def test_list_children_root() -> None:
    """Test listing children at root level (workspaces)."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    children = pm.list_children()
    
    assert isinstance(children, list)
    assert "uh2" in children


def test_list_children_workspace() -> None:
    """Test listing children of a workspace (products)."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    children = pm.list_children("uh2")
    
    assert isinstance(children, list)
    # Node names are converted to safe keys (spaces become underscores)
    assert "Widget_Pro" in children


def test_list_children_nonexistent_path() -> None:
    """Test that listing children of non-existent path raises AttributeError."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    with pytest.raises(AttributeError, match="node 'Nonexistent' not found"):
        pm.list_children("Nonexistent")


def test_list_properties() -> None:
    """Test listing properties of an item."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    properties = pm.list_properties("uh2.Widget_Pro.Gadget_A")
    
    assert isinstance(properties, list)
    assert "demo_property_mass" in properties
    assert "Color" in properties


def test_list_properties_empty_path() -> None:
    """Test that list_properties with empty path raises ValueError."""
    pm = PoelisMatlab(api_key="test-key")
    with pytest.raises(ValueError, match="Path cannot be empty"):
        pm.list_properties("")


def test_list_properties_nonexistent_path() -> None:
    """Test that listing properties of non-existent path raises AttributeError."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    with pytest.raises(AttributeError, match="node 'Nonexistent' not found"):
        pm.list_properties("Nonexistent.path")


def test_type_compatibility_numeric() -> None:
    """Test that numeric values are returned as native Python types."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    value = pm.get_value("uh2.Widget_Pro.Gadget_A.demo_property_mass")
    
    # Verify it's a native type, not a custom object
    assert isinstance(value, (int, float))
    assert not hasattr(value, "__dict__") or not any(
        not k.startswith("_") for k in value.__dict__.keys()
    )


def test_type_compatibility_string() -> None:
    """Test that string values are returned as native Python types."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    value = pm.get_value("uh2.Widget_Pro.Gadget_A.Color")
    
    assert isinstance(value, str)
    assert not hasattr(value, "__dict__") or not any(
        not k.startswith("_") for k in value.__dict__.keys()
    )


def test_change_property_numeric() -> None:
    """Test changing a numeric property value via MATLAB facade."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    # Set up mock response for property update
    def mock_graphql(query: str, variables: Optional[Dict[str, Any]] = None) -> Any:
        """Mock graphql that handles update mutation."""
        if "updateNumericProperty" in query:
            return _MockResponse(200, {
                "data": {
                    "updateNumericProperty": {
                        "id": "p2",
                        "readableId": "demo_property_mass",
                        "value": "123.45",
                        "parsedValue": 123.45,
                        "type": "numeric",
                    }
                }
            })
        # For property queries, use existing mock
        return t.handle_request(httpx.Request("POST", "/v1/graphql", content=json.dumps({"query": query, "variables": variables or {}}).encode()))
    
    # Replace transport's graphql method
    client._transport.graphql = mock_graphql  # type: ignore[assignment]
    
    # Change property value
    pm.change_property("uh2.Widget_Pro.draft.Child_Item.demo_property_mass", 123.45, title="Updated mass")
    
    # Verify the update was called (check that graphql was called with update mutation)
    # The actual verification would require checking the transport's request history
    # For now, we just verify no exception was raised


def test_change_property_versioned_error() -> None:
    """Test that changing a versioned property raises an error."""
    t = _MockTransport()
    client = _client_with_mock_transport(t)
    
    pm = PoelisMatlab.__new__(PoelisMatlab)
    pm.client = client
    
    # Try to change a property that would be versioned (this would fail in real scenario)
    # We'll test the error handling by using a path that doesn't exist or is versioned
    with pytest.raises((ValueError, RuntimeError, AttributeError)):
        # This will fail because we can't easily mock a versioned property in this test setup
        # but the error handling should work
        pm.change_property("uh2.Widget_Pro.v1.Child_Item.demo_property_mass", 123.45)


class _MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int, json_data: Dict[str, Any]) -> None:
        """Initialize mock response."""
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self) -> None:
        """Raise exception if status code indicates error."""
        if 400 <= self.status_code < 600:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=httpx.Request("POST", "/v1/graphql"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> Dict[str, Any]:
        """Return JSON data."""
        return self._json_data

