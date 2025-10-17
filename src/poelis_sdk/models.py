from __future__ import annotations

from typing import Optional, Any, Union, List

from pydantic import BaseModel, Field

"""Pydantic models for SDK resources."""


class Product(BaseModel):
    """Product resource representation."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    workspaceId: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class PaginatedProducts(BaseModel):
    """Paginated response for products list."""

    data: list[Product]
    limit: int
    offset: int


class PropertyValue(BaseModel):
    """Base class for property values with typed access."""
    
    raw_value: str = Field(alias="value")
    parsed_value: Optional[Any] = Field(alias="parsedValue", default=None)
    
    @property
    def value(self) -> Any:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.raw_value


class NumericProperty(BaseModel):
    """Numeric property representation."""
    
    id: str = Field(min_length=1)
    item_id: str = Field(alias="itemId", min_length=1)
    position: float
    name: str = Field(min_length=1)
    value: str
    category: str
    display_unit: Optional[str] = Field(alias="displayUnit", default=None)
    owner: str = Field(min_length=1)
    type: str = Field(min_length=1)
    parsed_value: Optional[Union[int, float, List[Any], str]] = Field(alias="parsedValue", default=None)
    
    @property
    def typed_value(self) -> Union[int, float, List[Any], str]:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class TextProperty(BaseModel):
    """Text property representation."""
    
    id: str = Field(min_length=1)
    item_id: str = Field(alias="itemId", min_length=1)
    position: float
    name: str = Field(min_length=1)
    value: str
    owner: str = Field(min_length=1)
    type: str = Field(min_length=1)
    parsed_value: Optional[Union[int, float, List[Any], str]] = Field(alias="parsedValue", default=None)
    
    @property
    def typed_value(self) -> Union[int, float, List[Any], str]:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class DateProperty(BaseModel):
    """Date property representation."""
    
    id: str = Field(min_length=1)
    item_id: str = Field(alias="itemId", min_length=1)
    position: float
    name: str = Field(min_length=1)
    value: str
    owner: str = Field(min_length=1)
    type: str = Field(min_length=1)
    parsed_value: Optional[str] = Field(alias="parsedValue", default=None)
    
    @property
    def typed_value(self) -> str:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class PropertySearchResult(BaseModel):
    """Property search result with unified fields across all property types."""
    
    id: str = Field(min_length=1)
    workspace_id: str = Field(alias="workspaceId", min_length=1)
    product_id: str = Field(alias="productId", min_length=1)
    item_id: str = Field(alias="itemId", min_length=1)
    property_type: str = Field(alias="propertyType", min_length=1)
    name: str = Field(min_length=1)
    category: Optional[str] = None
    display_unit: Optional[str] = Field(alias="displayUnit", default=None)
    value: Any  # Raw value from GraphQL
    parsed_value: Optional[Union[int, float, List[Any], str]] = Field(alias="parsedValue", default=None)
    owner: str = Field(min_length=1)
    created_by: str = Field(alias="createdBy", min_length=1)
    created_at: str = Field(alias="createdAt", min_length=1)
    updated_at: str = Field(alias="updatedAt", min_length=1)
    
    @property
    def typed_value(self) -> Union[int, float, List[Any], str]:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class PropertySearchResponse(BaseModel):
    """Response for property search queries."""
    
    query: str
    hits: List[PropertySearchResult]
    total: int
    limit: int
    offset: int
    processing_time_ms: int = Field(alias="processingTimeMs")


