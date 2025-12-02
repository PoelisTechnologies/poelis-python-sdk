from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from ._transport import Transport
from .browser import Browser
from .items import ItemsClient
from .logging import quiet_logging
from .products import ProductsClient
from .search import SearchClient
from .workspaces import WorkspacesClient
from .versions import VersionsClient

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
        timeout_seconds: Request timeout in seconds.
    """

    base_url: HttpUrl = Field(default="https://poelis-be-py-753618215333.europe-west1.run.app")
    api_key: str = Field(min_length=1)
    timeout_seconds: float = 30.0


class PoelisClient:
    """Synchronous Poelis SDK client.

    Provides access to resource-specific clients (e.g., `products`, `items`).
    This prototype only validates configuration and exposes placeholders for
    resource accessors to unblock incremental development.
    """

    def __init__(self, api_key: str, base_url: str = "https://poelis-be-py-753618215333.europe-west1.run.app", timeout_seconds: float = 30.0, org_id: Optional[str] = None) -> None:
        """Initialize the client with API endpoint and credentials.

        Args:
            api_key: API key for API authentication.
            base_url: Base URL of the Poelis API. Defaults to production.
            timeout_seconds: Network timeout in seconds.
            org_id: Deprecated, ignored parameter kept for backwards compatibility.
        """

        # Configure quiet logging by default for production use
        quiet_logging()

        self._config = ClientConfig(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

        # Shared transport
        self._transport = Transport(
            base_url=str(self._config.base_url),
            api_key=self._config.api_key,
            timeout_seconds=self._config.timeout_seconds,
        )

        # Resource clients
        self.workspaces = WorkspacesClient(self._transport)
        self.products = ProductsClient(self._transport, self.workspaces)
        self.items = ItemsClient(self._transport)
        self.versions = VersionsClient(self._transport)
        self.search = SearchClient(self._transport)
        self.browser = Browser(self)

    @classmethod
    def from_env(cls) -> "PoelisClient":
        """Construct a client using environment variables.

        Expected variables:
        - POELIS_BASE_URL (optional, defaults to managed GCP endpoint)
        - POELIS_API_KEY
        """

        base_url = os.environ.get("POELIS_BASE_URL", "https://poelis-be-py-753618215333.europe-west1.run.app")
        api_key = os.environ.get("POELIS_API_KEY")

        if not api_key:
            raise ValueError("POELIS_API_KEY must be set")

        return cls(api_key=api_key, base_url=base_url)

    @property
    def base_url(self) -> str:
        """Return the configured base URL as a string."""

        return str(self._config.base_url)

    @property
    def org_id(self) -> Optional[str]:
        """Return the configured organization id if any.
        
        Note:
            This property is deprecated and always returns ``None``. The backend
            now derives organization and workspace access from the API key
            itself, so explicit org selection on the client is no longer used.
        """

        return None


class _Deprecated:  # pragma: no cover
    pass


