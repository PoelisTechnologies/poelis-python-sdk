"""Tests for typed property values functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING

from poelis_sdk.browser import _PropWrapper
from poelis_sdk.models import DateProperty, NumericProperty, PropertySearchResult, TextProperty

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture  # noqa: F401
    from _pytest.fixtures import FixtureRequest  # noqa: F401
    from _pytest.logging import LogCaptureFixture  # noqa: F401
    from _pytest.monkeypatch import MonkeyPatch  # noqa: F401
    from pytest_mock.plugin import MockerFixture  # noqa: F401


class TestTypedPropertyModels:
    """Test Pydantic models for typed property values."""

    def test_numeric_property_with_parsed_value(self) -> None:
        """Test NumericProperty model with parsedValue field."""
        prop_data = {
            "id": "prop1",
            "itemId": "item1",
            "position": 1.0,
            "name": "Weight",
            "value": "42.5",
            "category": "Physical",
            "displayUnit": "kg",
            "owner": "user1",
            "type": "numeric",
            "parsedValue": 42.5
        }
        
        prop = NumericProperty(**prop_data)
        assert prop.typed_value == 42.5
        assert isinstance(prop.typed_value, float)
        assert prop.value == "42.5"  # Raw value remains string

    def test_numeric_property_without_parsed_value(self) -> None:
        """Test NumericProperty model without parsedValue field (fallback)."""
        prop_data = {
            "id": "prop1",
            "itemId": "item1",
            "position": 1.0,
            "name": "Weight",
            "value": "42.5",
            "category": "Physical",
            "displayUnit": "kg",
            "owner": "user1",
            "type": "numeric"
        }
        
        prop = NumericProperty(**prop_data)
        assert prop.typed_value == "42.5"  # Falls back to raw string
        assert prop.value == "42.5"

    def test_text_property_with_parsed_array(self) -> None:
        """Test TextProperty model with parsed array value."""
        prop_data = {
            "id": "prop2",
            "itemId": "item1",
            "position": 2.0,
            "name": "Tags",
            "value": '["tag1", "tag2", "tag3"]',
            "owner": "user1",
            "type": "text",
            "parsedValue": ["tag1", "tag2", "tag3"]
        }
        
        prop = TextProperty(**prop_data)
        assert prop.typed_value == ["tag1", "tag2", "tag3"]
        assert isinstance(prop.typed_value, list)
        assert prop.value == '["tag1", "tag2", "tag3"]'  # Raw value remains string

    def test_text_property_with_parsed_integer(self) -> None:
        """Test TextProperty model with parsed integer value."""
        prop_data = {
            "id": "prop3",
            "itemId": "item1",
            "position": 3.0,
            "name": "Count",
            "value": "100",
            "owner": "user1",
            "type": "text",
            "parsedValue": 100
        }
        
        prop = TextProperty(**prop_data)
        assert prop.typed_value == 100
        assert isinstance(prop.typed_value, int)
        assert prop.value == "100"  # Raw value remains string

    def test_date_property_with_parsed_value(self) -> None:
        """Test DateProperty model with parsedValue field."""
        prop_data = {
            "id": "prop4",
            "itemId": "item1",
            "position": 4.0,
            "name": "Created Date",
            "value": "2024-01-15",
            "owner": "user1",
            "type": "date",
            "parsedValue": "2024-01-15"
        }
        
        prop = DateProperty(**prop_data)
        assert prop.typed_value == "2024-01-15"
        assert isinstance(prop.typed_value, str)
        assert prop.value == "2024-01-15"

    def test_property_search_result_with_parsed_value(self) -> None:
        """Test PropertySearchResult model with parsedValue field."""
        result_data = {
            "id": "prop5",
            "workspaceId": "ws1",
            "productId": "prod1",
            "itemId": "item1",
            "propertyType": "numeric",
            "name": "Temperature",
            "category": "Environmental",
            "displayUnit": "°C",
            "value": "25.3",
            "parsedValue": 25.3,
            "owner": "user1",
            "createdBy": "user1",
            "createdAt": "2024-01-15T10:00:00Z",
            "updatedAt": "2024-01-15T10:00:00Z"
        }
        
        result = PropertySearchResult(**result_data)
        assert result.typed_value == 25.3
        assert isinstance(result.typed_value, float)
        assert result.value == "25.3"  # Raw value remains string


class TestPropWrapper:
    """Test _PropWrapper class with typed values."""

    def test_prop_wrapper_with_parsed_value(self) -> None:
        """Test _PropWrapper with parsedValue field."""
        prop_data = {
            "id": "prop1",
            "name": "Weight",
            "value": "42.5",
            "parsedValue": 42.5,
            "category": "Physical"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == 42.5
        assert isinstance(wrapper.value, float)
        assert wrapper.category == "Physical"

    def test_prop_wrapper_without_parsed_value_fallback(self) -> None:
        """Test _PropWrapper fallback when parsedValue is not available."""
        prop_data = {
            "id": "prop1",
            "name": "Weight",
            "value": "42.5",
            "category": "Physical"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == "42.5"  # Falls back to raw value
        assert isinstance(wrapper.value, str)
        assert wrapper.category == "Physical"

    def test_prop_wrapper_with_parsed_array(self) -> None:
        """Test _PropWrapper with parsed array value."""
        prop_data = {
            "id": "prop2",
            "name": "Tags",
            "value": '["tag1", "tag2"]',
            "parsedValue": ["tag1", "tag2"],
            "category": "Metadata"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == ["tag1", "tag2"]
        assert isinstance(wrapper.value, list)
        assert wrapper.category == "Metadata"

    def test_prop_wrapper_legacy_numeric_parsing(self) -> None:
        """Test _PropWrapper with legacy numeric parsing (integerPart/exponent)."""
        prop_data = {
            "id": "prop3",
            "name": "Legacy Numeric",
            "integerPart": 42,
            "exponent": 1,
            "category": "Legacy"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == 420  # 42 * 10^1
        assert isinstance(wrapper.value, int)
        assert wrapper.category == "Legacy"

    def test_prop_wrapper_legacy_search_properties(self) -> None:
        """Test _PropWrapper with legacy searchProperties format."""
        prop_data = {
            "id": "prop4",
            "name": "Search Numeric",
            "numericValue": 123.45,
            "category": "Search"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == 123.45
        assert isinstance(wrapper.value, float)
        assert wrapper.category == "Search"

    def test_prop_wrapper_with_unit(self) -> None:
        """Test _PropWrapper with displayUnit field."""
        prop_data = {
            "id": "prop5",
            "name": "Weight",
            "value": "42.5",
            "parsedValue": 42.5,
            "category": "Physical",
            "displayUnit": "kg"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == 42.5
        assert wrapper.category == "Physical"
        assert wrapper.unit == "kg"

    def test_prop_wrapper_without_unit(self) -> None:
        """Test _PropWrapper without displayUnit field."""
        prop_data = {
            "id": "prop6",
            "name": "Name",
            "value": "Test",
            "category": "Metadata"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == "Test"
        assert wrapper.category == "Metadata"
        assert wrapper.unit is None

    def test_prop_wrapper_with_display_unit_snake_case(self) -> None:
        """Test _PropWrapper with display_unit field (snake_case fallback)."""
        prop_data = {
            "id": "prop7",
            "name": "Temperature",
            "value": "25.3",
            "parsedValue": 25.3,
            "category": "Environmental",
            "display_unit": "°C"
        }
        
        wrapper = _PropWrapper(prop_data)
        assert wrapper.value == 25.3
        assert wrapper.category == "Environmental"
        assert wrapper.unit == "°C"
