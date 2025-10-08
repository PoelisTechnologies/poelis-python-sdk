from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

"""Pydantic models for SDK resources."""


class Product(BaseModel):
    """Product resource representation."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    workspace_id: Optional[str] = None


class PaginatedProducts(BaseModel):
    """Paginated response for products list."""

    data: list[Product]
    limit: int
    offset: int


