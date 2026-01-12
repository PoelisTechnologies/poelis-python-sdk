"""Tests for property write functionality via change_property method."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx
import pytest

from poelis_sdk.browser import _PropWrapper
from poelis_sdk.client import PoelisClient
from poelis_sdk.exceptions import NotFoundError, UnauthorizedError


class _MockTransport:
    """Mock transport that records requests and returns configurable responses."""

    def __init__(self) -> None:
        """Initialize mock transport."""
        self.requests: list[Dict[str, Any]] = []
        self._response_data: Optional[Dict[str, Any]] = None

    def set_response(self, data: Dict[str, Any]) -> None:
        """Set the response data for the next request."""
        self._response_data = data

    def graphql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> _MockResponse:
        """Mock graphql method that records requests and returns configured responses."""
        self.requests.append({"query": query, "variables": variables or {}})
        if self._response_data is None:
            # Default success response
            return _MockResponse(200, {"data": {"updateNumericProperty": {"id": "prop-1", "value": "123.45"}}})
        return _MockResponse(200, self._response_data)


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


@pytest.fixture
def mock_client() -> PoelisClient:
    """Create a mock PoelisClient with mocked transport."""
    client = PoelisClient(api_key="test-key", enable_change_detection=False)
    # Replace transport with mock
    mock_transport = _MockTransport()
    client._transport = mock_transport  # type: ignore[assignment]
    return client


def test_change_property_numeric_value(mock_client: PoelisClient) -> None:
    """Test updating numeric property value."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "parsedValue": 10.5,
        "category": "Mass",
        "displayUnit": "kg",
        "productVersionNumber": None,  # Draft property
    }

    # Set up mock response
    updated_prop = {
        "id": "prop-1",
        "readableId": "mass",
        "value": "123.45",
        "parsedValue": 123.45,
        "category": "Mass",
        "displayUnit": "kg",
        "type": "numeric",
    }
    mock_client._transport.set_response({"data": {"updateNumericProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)
    wrapper.change_property(123.45, title="Updated mass", description="Changed mass value")

    # Verify request was made
    assert len(mock_client._transport.requests) == 1  # type: ignore[attr-defined]
    request = mock_client._transport.requests[0]  # type: ignore[attr-defined]
    payload = json.loads(request.content.decode("utf-8"))
    variables = payload["variables"]

    assert variables["id"] == "prop-1"
    assert variables["value"] == "123.45"  # Should be JSON string
    assert variables["reason"] == "Updated mass"
    assert variables["description"] == "Changed mass value"

    # Verify _raw was updated
    assert wrapper._raw["value"] == "123.45"
    assert wrapper._raw["parsedValue"] == 123.45


def test_change_property_numeric_array(mock_client: PoelisClient) -> None:
    """Test updating numeric property with array value."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "values",
        "value": "[1, 2, 3]",
        "parsedValue": [1, 2, 3],
        "productVersionNumber": None,
    }

    updated_prop = {
        "id": "prop-1",
        "readableId": "values",
        "value": "[4, 5, 6]",
        "parsedValue": [4, 5, 6],
        "type": "numeric",
    }
    mock_client._transport.set_response({"data": {"updateNumericProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)
    wrapper.change_property([4, 5, 6])

    request = mock_client._transport.requests[0]  # type: ignore[attr-defined]
    payload = json.loads(request.content.decode("utf-8"))
    variables = payload["variables"]

    assert variables["value"] == "[4, 5, 6]"  # Should be JSON string


def test_change_property_text_value(mock_client: PoelisClient) -> None:
    """Test updating text property value."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-2",
        "__typename": "TextProperty",
        "readableId": "description",
        "value": "Old text",
        "parsedValue": "Old text",
        "productVersionNumber": None,
    }

    updated_prop = {
        "id": "prop-2",
        "readableId": "description",
        "value": "New text",
        "parsedValue": "New text",
        "type": "text",
    }
    mock_client._transport.set_response({"data": {"updateTextProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)
    wrapper.change_property("New text", title="Updated description")

    request = mock_client._transport.requests[0]  # type: ignore[attr-defined]
    payload = json.loads(request.content.decode("utf-8"))
    variables = payload["variables"]

    assert variables["id"] == "prop-2"
    assert variables["value"] == "New text"
    assert "updateTextProperty" in payload["query"]


def test_change_property_date_value(mock_client: PoelisClient) -> None:
    """Test updating date property value."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-3",
        "__typename": "DateProperty",
        "readableId": "date",
        "value": "2024-01-01",
        "productVersionNumber": None,
    }

    updated_prop = {
        "id": "prop-3",
        "readableId": "date",
        "value": "2025-12-31",
        "type": "date",
    }
    mock_client._transport.set_response({"data": {"updateDateProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)
    wrapper.change_property("2025-12-31")

    request = mock_client._transport.requests[0]  # type: ignore[attr-defined]
    payload = json.loads(request.content.decode("utf-8"))
    variables = payload["variables"]

    assert variables["value"] == "2025-12-31"
    assert "updateDateProperty" in payload["query"]


def test_change_property_date_invalid_format(mock_client: PoelisClient) -> None:
    """Test that invalid date format raises ValueError."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-3",
        "__typename": "DateProperty",
        "readableId": "date",
        "value": "2024-01-01",
        "productVersionNumber": None,
    }

    wrapper = _PropWrapper(raw_prop, client=mock_client)

    with pytest.raises(ValueError, match="Date must be in ISO 8601 format"):
        wrapper.change_property("invalid-date")


def test_change_property_status_value(mock_client: PoelisClient) -> None:
    """Test updating status property value."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-4",
        "__typename": "StatusProperty",
        "readableId": "status",
        "value": "DRAFT",
        "productVersionNumber": None,
    }

    updated_prop = {
        "id": "prop-4",
        "readableId": "status",
        "value": "DONE",
        "type": "status",
    }
    mock_client._transport.set_response({"data": {"updateStatusProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)
    wrapper.change_property("DONE")

    request = mock_client._transport.requests[0]  # type: ignore[attr-defined]
    payload = json.loads(request.content.decode("utf-8"))
    variables = payload["variables"]

    assert variables["value"] == "DONE"
    assert "updateStatusProperty" in payload["query"]


def test_change_property_status_invalid_value(mock_client: PoelisClient) -> None:
    """Test that invalid status value raises ValueError."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-4",
        "__typename": "StatusProperty",
        "readableId": "status",
        "value": "DRAFT",
        "productVersionNumber": None,
    }

    wrapper = _PropWrapper(raw_prop, client=mock_client)

    with pytest.raises(ValueError, match="Status must be one of"):
        wrapper.change_property("INVALID_STATUS")


def test_change_property_versioned_property(mock_client: PoelisClient) -> None:
    """Test that updating versioned property raises ValueError."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "productVersionNumber": 1,  # Versioned property
    }

    wrapper = _PropWrapper(raw_prop, client=mock_client)

    with pytest.raises(ValueError, match="Cannot update versioned property"):
        wrapper.change_property(123.45)


def test_change_property_value_only(mock_client: PoelisClient) -> None:
    """Test that change_property only updates the value field."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "category": "Mass",
        "displayUnit": "kg",
        "productVersionNumber": None,
    }

    updated_prop = {
        "id": "prop-1",
        "readableId": "mass",
        "value": "123.45",
        "category": "Mass",
        "displayUnit": "kg",
        "type": "numeric",
    }
    mock_client._transport.set_response({"data": {"updateNumericProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)
    wrapper.change_property(123.45)

    # Verify request was made
    assert len(mock_client._transport.requests) == 1  # type: ignore[attr-defined]

    # Check request
    request = mock_client._transport.requests[0]  # type: ignore[attr-defined]
    payload = json.loads(request.content.decode("utf-8"))
    assert payload["variables"]["value"] == "123.45"
    # Verify only value is being updated, not other fields
    assert "category" not in payload["variables"] or payload["variables"].get("category") is None


def test_change_property_not_found_error(mock_client: PoelisClient) -> None:
    """Test that property not found raises NotFoundError."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "productVersionNumber": None,
    }

    # Set up error response
    error_response = {
        "errors": [
            {
                "message": "Property not found",
                "extensions": {"code": "not_found"},
            }
        ]
    }
    mock_client._transport.set_response(error_response)  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)

    with pytest.raises(NotFoundError):
        wrapper.change_property(123.45)


def test_change_property_forbidden_error(mock_client: PoelisClient) -> None:
    """Test that permission denied raises UnauthorizedError."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "productVersionNumber": None,
    }

    # Set up error response
    error_response = {
        "errors": [
            {
                "message": "Permission denied",
                "extensions": {"code": "forbidden"},
            }
        ]
    }
    mock_client._transport.set_response(error_response)  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)

    with pytest.raises(UnauthorizedError):
        wrapper.change_property(123.45)


def test_change_property_invalid_date_error(mock_client: PoelisClient) -> None:
    """Test that invalid date format from backend raises ValueError."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-3",
        "__typename": "DateProperty",
        "readableId": "date",
        "value": "2024-01-01",
        "productVersionNumber": None,
    }

    # Set up error response
    error_response = {
        "errors": [
            {
                "message": "Invalid date format",
                "extensions": {"code": "invalid_date_format"},
            }
        ]
    }
    mock_client._transport.set_response(error_response)  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)

    with pytest.raises(ValueError, match="Date must be in ISO 8601 format"):
        wrapper.change_property("2024-13-45")  # Invalid date that passes client validation


def test_change_property_invalid_status_error(mock_client: PoelisClient) -> None:
    """Test that invalid status value from backend raises ValueError."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-4",
        "__typename": "StatusProperty",
        "readableId": "status",
        "value": "DRAFT",
        "productVersionNumber": None,
    }

    # Set up error response
    error_response = {
        "errors": [
            {
                "message": "Invalid status value",
                "extensions": {"code": "invalid_status_value"},
            }
        ]
    }
    mock_client._transport.set_response(error_response)  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)

    with pytest.raises(ValueError, match="Status must be one of"):
        wrapper.change_property("DONE")  # Valid client-side but backend rejects


def test_change_property_no_client() -> None:
    """Test that change_property raises error when client is not available."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "productVersionNumber": None,
    }

    wrapper = _PropWrapper(raw_prop, client=None)

    with pytest.raises(RuntimeError, match="Client not available"):
        wrapper.change_property(123.45)


def test_change_property_property_type_detection(mock_client: PoelisClient) -> None:
    """Test that property type is correctly detected from different field names."""
    # Test with __typename
    raw_prop1: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "productVersionNumber": None,
    }

    updated_prop = {
        "id": "prop-1",
        "readableId": "mass",
        "value": "123.45",
        "type": "numeric",
    }
    mock_client._transport.set_response({"data": {"updateNumericProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper1 = _PropWrapper(raw_prop1, client=mock_client)
    wrapper1.change_property(123.45)

    request = mock_client._transport.requests[0]  # type: ignore[attr-defined]
    payload = json.loads(request.content.decode("utf-8"))
    assert "updateNumericProperty" in payload["query"]

    # Test with propertyType field
    raw_prop2: Dict[str, Any] = {
        "id": "prop-2",
        "propertyType": "text",
        "readableId": "description",
        "value": "Old text",
        "productVersionNumber": None,
    }

    updated_prop2 = {
        "id": "prop-2",
        "readableId": "description",
        "value": "New text",
        "type": "text",
    }
    mock_client._transport.set_response({"data": {"updateTextProperty": updated_prop2}})  # type: ignore[attr-defined]

    wrapper2 = _PropWrapper(raw_prop2, client=mock_client)
    wrapper2.change_property("New text")

    request2 = mock_client._transport.requests[1]  # type: ignore[attr-defined]
    payload2 = json.loads(request2.content.decode("utf-8"))
    assert "updateTextProperty" in payload2["query"]


def test_change_property_updates_raw_data(mock_client: PoelisClient) -> None:
    """Test that _raw is updated after successful mutation."""
    raw_prop: Dict[str, Any] = {
        "id": "prop-1",
        "__typename": "NumericProperty",
        "readableId": "mass",
        "value": "10.5",
        "parsedValue": 10.5,
        "category": "Mass",
        "productVersionNumber": None,
    }

    updated_prop = {
        "id": "prop-1",
        "readableId": "mass",
        "value": "123.45",
        "parsedValue": 123.45,
        "category": "Mass",
        "displayUnit": "kg",
        "type": "numeric",
    }
    mock_client._transport.set_response({"data": {"updateNumericProperty": updated_prop}})  # type: ignore[attr-defined]

    wrapper = _PropWrapper(raw_prop, client=mock_client)
    original_raw = dict(wrapper._raw)

    wrapper.change_property(123.45)

    # Verify _raw was updated
    assert wrapper._raw["value"] == "123.45"
    assert wrapper._raw["parsedValue"] == 123.45
    assert wrapper._raw["displayUnit"] == "kg"
    # Verify original fields are preserved/updated
    assert wrapper._raw["id"] == original_raw["id"]
    assert wrapper._raw["readableId"] == original_raw["readableId"]

