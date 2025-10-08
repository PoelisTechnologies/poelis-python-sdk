from __future__ import annotations

from typing import Optional
import os

from pydantic import BaseModel, Field, HttpUrl
from ._transport import Transport
from .products import ProductsClient
from .items import ItemsClient
from .search import SearchClient
from .workspaces import WorkspacesClient
from .browser import Browser

"""Core client for the Poelis Python SDK.

This module exposes the `PoelisClient` which configures base URL, authentication,
tenant scoping, and provides accessors for resource clients. The initial
implementation is sync-first and keeps the transport layer swappable for
future async parity.
"""


class ClientConfig(BaseModel):
    """Configuration for `PoelisClient`.

    Attributes:
        base_url: Base URL of the Poelis API.
        api_key: API key used for authentication.
        org_id: Organization id for multi-tenancy scoping.
        timeout_seconds: Request timeout in seconds.
    """

    base_url: HttpUrl = Field(default="https://api.poelis.ai")
    api_key: str = Field(min_length=1)
    org_id: str = Field(min_length=1)
    timeout_seconds: float = 30.0


class PoelisClient:
    """Synchronous Poelis SDK client.

    Provides access to resource-specific clients (e.g., `products`, `items`).
    This prototype only validates configuration and exposes placeholders for
    resource accessors to unblock incremental development.
    """

    def __init__(self, api_key: str, org_id: str, base_url: str = "https://api.poelis.ai", timeout_seconds: float = 30.0) -> None:
        """Initialize the client with API endpoint and credentials.

        Args:
            api_key: API key for API authentication.
            org_id: Tenant organization id to scope requests.
            base_url: Base URL of the Poelis API. Defaults to production.
            timeout_seconds: Network timeout in seconds.
        """

        self._config = ClientConfig(
            base_url=base_url,
            api_key=api_key,
            org_id=org_id,
            timeout_seconds=timeout_seconds,
        )

        # Shared transport
        self._transport = Transport(
            base_url=str(self._config.base_url),
            api_key=self._config.api_key,
            org_id=self._config.org_id,
            timeout_seconds=self._config.timeout_seconds,
        )

        # Resource clients
        self.products = ProductsClient(self._transport)
        self.items = ItemsClient(self._transport)
        self.search = SearchClient(self._transport)
        self.workspaces = WorkspacesClient(self._transport)
        self.browser = Browser(self)

    @classmethod
    def from_env(cls) -> "PoelisClient":
        """Construct a client using environment variables.

        Expected variables:
        - POELIS_BASE_URL (optional, defaults to production)
        - POELIS_API_KEY
        - POELIS_ORG_ID
        """

        base_url = os.environ.get("POELIS_BASE_URL", "https://api.poelis.ai")
        api_key = os.environ.get("POELIS_API_KEY")
        org_id = os.environ.get("POELIS_ORG_ID")

        if not api_key:
            raise ValueError("POELIS_API_KEY must be set")
        if not org_id:
            raise ValueError("POELIS_ORG_ID must be set")

        return cls(api_key=api_key, org_id=org_id, base_url=base_url)

    @property
    def base_url(self) -> str:
        """Return the configured base URL as a string."""

        return str(self._config.base_url)

    @property
    def org_id(self) -> Optional[str]:
        """Return the configured organization id if any."""

        return self._config.org_id


class _Deprecated:  # pragma: no cover
    pass


