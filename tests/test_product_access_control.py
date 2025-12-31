"""Tests for product-level access control functionality.

Tests cover:
- Product model with reviewers and approvalMode fields
- userAccessibleResources query
- Access control behavior (filtering, None results)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch

from poelis_sdk import PoelisClient
from poelis_sdk.models import (
    ChangedByUser,
    Product,
    UserAccessibleResources,
)


def test_product_model_with_reviewers_and_approval_mode() -> None:
    """Test that Product model correctly handles reviewers and approvalMode fields."""
    # Test with all fields
    product_data = {
        "id": "prod-123",
        "name": "Test Product",
        "readableId": "test-product",
        "workspaceId": "ws-123",
        "baselineVersionNumber": 5,
        "reviewers": [
            {"id": "user-1", "userName": "Alice", "imageUrl": "https://example.com/alice.jpg"},
            {"id": "user-2", "userName": "Bob", "imageUrl": None},
        ],
        "approvalMode": "sequential",
    }
    
    product = Product(**product_data)
    
    assert product.id == "prod-123"
    assert product.name == "Test Product"
    assert len(product.reviewers) == 2
    assert product.reviewers[0].id == "user-1"
    assert product.reviewers[0].user_name == "Alice"
    assert product.reviewers[0].image_url == "https://example.com/alice.jpg"
    assert product.reviewers[1].id == "user-2"
    assert product.reviewers[1].user_name == "Bob"
    assert product.reviewers[1].image_url is None
    assert product.approval_mode == "sequential"


def test_product_model_without_reviewers_and_approval_mode() -> None:
    """Test that Product model handles missing reviewers and approvalMode gracefully."""
    # Test with minimal fields (backward compatibility)
    product_data = {
        "id": "prod-123",
        "name": "Test Product",
    }
    
    product = Product(**product_data)
    
    assert product.id == "prod-123"
    assert product.name == "Test Product"
    assert product.reviewers == []  # Default empty list
    assert product.approval_mode is None  # Default None


def test_product_model_approval_mode_values() -> None:
    """Test that Product model accepts all valid approvalMode values."""
    valid_modes = ["sequential", "any", "all", None]
    
    for mode in valid_modes:
        product_data = {
            "id": "prod-123",
            "name": "Test Product",
            "approvalMode": mode,
        }
        product = Product(**product_data)
        assert product.approval_mode == mode


def test_changed_by_user_model() -> None:
    """Test ChangedByUser model for reviewers."""
    user_data = {
        "id": "user-1",
        "userName": "Alice",
        "imageUrl": "https://example.com/alice.jpg",
    }
    
    user = ChangedByUser(**user_data)
    
    assert user.id == "user-1"
    assert user.user_name == "Alice"
    assert user.image_url == "https://example.com/alice.jpg"


def test_changed_by_user_without_image() -> None:
    """Test ChangedByUser model without imageUrl."""
    user_data = {
        "id": "user-1",
        "userName": "Alice",
    }
    
    user = ChangedByUser(**user_data)
    
    assert user.id == "user-1"
    assert user.user_name == "Alice"
    assert user.image_url is None


def test_user_accessible_resources_model() -> None:
    """Test UserAccessibleResources model structure."""
    resources_data = {
        "workspaces": [
            {
                "id": "ws-1",
                "name": "Workspace 1",
                "readableId": "workspace-1",
                "role": "EDITOR",
                "products": [
                    {
                        "id": "prod-1",
                        "name": "Product 1",
                        "readableId": "product-1",
                        "role": "VIEWER",
                    },
                    {
                        "id": "prod-2",
                        "name": "Product 2",
                        "readableId": None,
                        "role": "EDITOR",
                    },
                ],
            },
            {
                "id": "ws-2",
                "name": "Workspace 2",
                "readableId": None,
                "role": "VIEWER",
                "products": [],
            },
        ],
    }
    
    resources = UserAccessibleResources(**resources_data)
    
    assert len(resources.workspaces) == 2
    assert resources.workspaces[0].id == "ws-1"
    assert resources.workspaces[0].name == "Workspace 1"
    assert resources.workspaces[0].role == "EDITOR"
    assert len(resources.workspaces[0].products) == 2
    assert resources.workspaces[0].products[0].id == "prod-1"
    assert resources.workspaces[0].products[0].role == "VIEWER"
    assert resources.workspaces[0].products[1].role == "EDITOR"
    assert resources.workspaces[1].role == "VIEWER"
    assert len(resources.workspaces[1].products) == 0


def test_user_accessible_resources_empty() -> None:
    """Test UserAccessibleResources with empty workspaces list."""
    resources_data = {"workspaces": []}
    
    resources = UserAccessibleResources(**resources_data)
    
    assert len(resources.workspaces) == 0


def test_get_user_accessible_resources_mock(monkeypatch: "MonkeyPatch") -> None:
    """Test get_user_accessible_resources method with mocked transport."""
    # Mock response data
    mock_response_data = {
        "data": {
            "userAccessibleResources": {
                "workspaces": [
                    {
                        "id": "ws-1",
                        "name": "Workspace 1",
                        "readableId": "workspace-1",
                        "role": "EDITOR",
                        "products": [
                            {
                                "id": "prod-1",
                                "name": "Product 1",
                                "readableId": "product-1",
                                "role": "VIEWER",
                            },
                        ],
                    },
                ],
            },
        },
    }
    
    # Track calls
    call_args_list: list[tuple[Any, ...]] = []
    
    class MockResponse:
        """Mock response that mimics httpx.Response behavior."""
        
        def __init__(self, json_data: dict[str, Any]) -> None:
            self._json_data = json_data
            self.status_code = 200
        
        def json(self) -> dict[str, Any]:
            return self._json_data
        
        def raise_for_status(self) -> None:
            # No-op for successful responses
            pass
    
    def mock_graphql(query: str, variables: dict[str, Any] | None = None) -> MockResponse:
        call_args_list.append((query, variables))
        return MockResponse(mock_response_data)
    
    # Create client and patch transport
    client = PoelisClient(api_key="test-key")
    monkeypatch.setattr(client.workspaces._t, "graphql", mock_graphql)
    
    # Call method
    resources = client.workspaces.get_user_accessible_resources(user_id="user-123")
    
    # Verify
    assert len(resources.workspaces) == 1
    assert resources.workspaces[0].id == "ws-1"
    assert resources.workspaces[0].role == "EDITOR"
    assert len(resources.workspaces[0].products) == 1
    assert resources.workspaces[0].products[0].role == "VIEWER"
    
    # Verify GraphQL query was called correctly
    assert len(call_args_list) == 1
    query, variables = call_args_list[0]
    assert "userAccessibleResources" in query
    assert variables is not None
    assert variables["userId"] == "user-123"


def test_get_user_accessible_resources_error_handling(monkeypatch: "MonkeyPatch") -> None:
    """Test get_user_accessible_resources handles GraphQL errors."""
    # Mock response with errors
    mock_response_data = {
        "errors": [{"message": "User not found"}],
    }
    
    class MockResponse:
        """Mock response that mimics httpx.Response behavior."""
        
        def __init__(self, json_data: dict[str, Any]) -> None:
            self._json_data = json_data
            self.status_code = 200
        
        def json(self) -> dict[str, Any]:
            return self._json_data
        
        def raise_for_status(self) -> None:
            # No-op for successful responses
            pass
    
    def mock_graphql(query: str, variables: dict[str, Any] | None = None) -> MockResponse:
        return MockResponse(mock_response_data)
    
    client = PoelisClient(api_key="test-key")
    monkeypatch.setattr(client.workspaces._t, "graphql", mock_graphql)
    
    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="User not found"):
        client.workspaces.get_user_accessible_resources(user_id="user-123")


def test_get_user_accessible_resources_malformed_response(monkeypatch: "MonkeyPatch") -> None:
    """Test get_user_accessible_resources handles malformed responses."""
    # Mock response without userAccessibleResources field
    mock_response_data = {
        "data": {},
    }
    
    class MockResponse:
        """Mock response that mimics httpx.Response behavior."""
        
        def __init__(self, json_data: dict[str, Any]) -> None:
            self._json_data = json_data
            self.status_code = 200
        
        def json(self) -> dict[str, Any]:
            return self._json_data
        
        def raise_for_status(self) -> None:
            # No-op for successful responses
            pass
    
    def mock_graphql(query: str, variables: dict[str, Any] | None = None) -> MockResponse:
        return MockResponse(mock_response_data)
    
    client = PoelisClient(api_key="test-key")
    monkeypatch.setattr(client.workspaces._t, "graphql", mock_graphql)
    
    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Malformed GraphQL response"):
        client.workspaces.get_user_accessible_resources(user_id="user-123")

