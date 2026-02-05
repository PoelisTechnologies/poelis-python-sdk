from __future__ import annotations

from typing import Any, List, Literal, Optional, Union

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

"""Pydantic models for SDK resources."""


class ChangedByUser(BaseModel):
    """User information for reviewers and change tracking.
    
    Attributes:
        id: User identifier.
        user_name: Username or display name.
        image_url: Optional URL to user's profile image.
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(min_length=1)
    user_name: str = Field(alias="userName", min_length=1)
    image_url: Optional[str] = Field(alias="imageUrl", default=None)


class Product(BaseModel):
    """Product resource representation.
    
    Attributes:
        id: Product identifier.
        name: Product name.
        readableId: Optional human-readable identifier.
        workspaceId: Identifier of the workspace containing this product.
        baseline_version_number: Optional baseline version number for this product.
        code: Optional product code.
        description: Optional product description.
        reviewers: List of users who are reviewers for this product.
        approval_mode: Optional approval mode (sequential, any, all, or None).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    readableId: Optional[str] = None
    workspaceId: Optional[str] = None
    baseline_version_number: Optional[int] = Field(
        alias="baselineVersionNumber",
        default=None,
    )
    code: Optional[str] = None
    description: Optional[str] = None
    reviewers: List[ChangedByUser] = Field(default_factory=list)
    approval_mode: Optional[Literal["sequential", "any", "all"]] = Field(
        alias="approvalMode",
        default=None,
    )


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

    model_config = ConfigDict(populate_by_name=True)

    product_id: str = Field(alias="productId", min_length=1)
    version_number: int = Field(alias="versionNumber")
    title: Optional[str] = Field(default=None)
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

    model_config = ConfigDict(populate_by_name=True)
    
    raw_value: str = Field(alias="value")
    parsed_value: Optional[Any] = Field(alias="parsedValue", default=None)
    
    @property
    def value(self) -> Any:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.raw_value


class NumericProperty(BaseModel):
    """Numeric property representation.

    Note: The `category` field contains normalized/canonicalized values when set.
    Categories are normalized server-side (upper-cased, deduplicated) and
    may differ from the original input values. For formula properties,
    `category` and `display_unit` are always unset; `value` is null when the
    formula is invalid.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(min_length=1)
    product_id: Optional[str] = Field(alias="productId", default=None)
    product_version_number: Optional[int] = Field(alias="productVersionNumber", default=None)
    item_id: str = Field(alias="itemId", min_length=1)
    position: float
    name: str = Field(min_length=1)
    value: Optional[str] = None
    category: Optional[str] = None
    display_unit: Optional[str] = Field(alias="displayUnit", default=None)
    type: str = Field(min_length=1)
    parsed_value: Optional[Union[int, float, List[Any], str]] = Field(alias="parsedValue", default=None)

    @property
    def typed_value(self) -> Union[int, float, List[Any], str, None]:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class TextProperty(BaseModel):
    """Text property representation."""

    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(min_length=1)
    product_id: Optional[str] = Field(alias="productId", default=None)
    product_version_number: Optional[int] = Field(alias="productVersionNumber", default=None)
    item_id: str = Field(alias="itemId", min_length=1)
    position: float
    name: str = Field(min_length=1)
    value: str
    type: str = Field(min_length=1)
    parsed_value: Optional[Union[int, float, List[Any], str]] = Field(alias="parsedValue", default=None)
    
    @property
    def typed_value(self) -> Union[int, float, List[Any], str]:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class DateProperty(BaseModel):
    """Date property representation."""

    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(min_length=1)
    product_id: Optional[str] = Field(alias="productId", default=None)
    product_version_number: Optional[int] = Field(alias="productVersionNumber", default=None)
    item_id: str = Field(alias="itemId", min_length=1)
    position: float
    name: str = Field(min_length=1)
    value: str
    type: str = Field(min_length=1)
    parsed_value: Optional[str] = Field(alias="parsedValue", default=None)
    
    @property
    def typed_value(self) -> str:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class PropertySearchResult(BaseModel):
    """Property search result with unified fields across all property types."""

    model_config = ConfigDict(populate_by_name=True)
    
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
    created_by: str = Field(alias="createdBy", min_length=1)
    created_at: str = Field(alias="createdAt", min_length=1)
    updated_at: str = Field(alias="updatedAt", min_length=1)
    
    @property
    def typed_value(self) -> Union[int, float, List[Any], str]:
        """Get the properly typed value, falling back to raw string if parsing failed."""
        return self.parsed_value if self.parsed_value is not None else self.value


class PropertySearchResponse(BaseModel):
    """Response for property search queries."""

    model_config = ConfigDict(populate_by_name=True)
    
    query: str
    hits: List[PropertySearchResult]
    total: int
    limit: int
    offset: int
    processing_time_ms: int = Field(alias="processingTimeMs")


class ProductAccess(BaseModel):
    """Product access information with role.
    
    Attributes:
        id: Product identifier.
        name: Product name.
        readable_id: Optional human-readable identifier.
        role: User's role for this product (product-level role or inherited workspace role).
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    readable_id: Optional[str] = Field(alias="readableId", default=None)
    role: str = Field(min_length=1)  # Role enum: EDITOR, VIEWER, NO_ACCESS, etc.


class WorkspaceWithProducts(BaseModel):
    """Workspace with its accessible products and role information.
    
    Attributes:
        id: Workspace identifier.
        name: Workspace name.
        readable_id: Optional human-readable identifier.
        role: User's role for this workspace.
        products: List of products accessible in this workspace with their roles.
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    readable_id: Optional[str] = Field(alias="readableId", default=None)
    role: str = Field(min_length=1)  # Role enum: EDITOR, VIEWER, etc.
    products: List[ProductAccess] = Field(default_factory=list)


class UserAccessibleResources(BaseModel):
    """User's accessible resources (workspaces and products) with role information.
    
    Attributes:
        workspaces: List of workspaces the user can access with their roles and products.
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    workspaces: List[WorkspaceWithProducts] = Field(default_factory=list)


