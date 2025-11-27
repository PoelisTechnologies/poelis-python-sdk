from __future__ import annotations

from typing import Any, List, Optional, Union

from datetime import datetime

from pydantic import BaseModel, Field

"""Pydantic models for SDK resources."""


class Product(BaseModel):
    """Product resource representation."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    readableId: Optional[str] = None
    workspaceId: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class ProductVersion(BaseModel):
    """Product version resource representation.

    Represents a frozen snapshot of a product at a specific version number.

    Attributes:
        product_id: Identifier of the parent product.
        version_number: Monotonic version number for the product.
        title: Human-friendly title for this version.
        description: Optional free-text description of the version.
        created_by: Optional identifier of the user who created the version (not currently queried from GraphQL).
        created_at: Timestamp when the version was created.
        updated_at: Optional timestamp of the last update to the version (not in GraphQL schema yet).
        org_id: Optional identifier of the owning organization (not in GraphQL schema yet).
    """

    product_id: str = Field(alias="productId", min_length=1)
    version_number: int = Field(alias="versionNumber")
    title: str = Field(min_length=1)
    description: Optional[str] = None
    created_by: Optional[str] = Field(alias="createdBy", default=None)
    created_at: datetime = Field(alias="createdAt")
    updated_at: Optional[datetime] = Field(alias="updatedAt", default=None)
    org_id: Optional[str] = Field(alias="orgId", default=None)


class PaginatedProducts(BaseModel):
    """Paginated response for products list."""

    data: list[Product]
    limit: int
    offset: int


class PaginatedProductVersions(BaseModel):
    """Paginated response for product versions list."""

    data: list[ProductVersion]
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
    """Numeric property representation.
    
    Note: The `category` field contains normalized/canonicalized values.
    Categories are normalized server-side (upper-cased, deduplicated) and
    may differ from the original input values.
    """
    
    id: str = Field(min_length=1)
    product_id: Optional[str] = Field(alias="productId", default=None)
    product_version_number: Optional[int] = Field(alias="productVersionNumber", default=None)
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
    product_id: Optional[str] = Field(alias="productId", default=None)
    product_version_number: Optional[int] = Field(alias="productVersionNumber", default=None)
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
    product_id: Optional[str] = Field(alias="productId", default=None)
    product_version_number: Optional[int] = Field(alias="productVersionNumber", default=None)
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
    product_version_number: Optional[int] = Field(alias="productVersionNumber", default=None)
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


