from __future__ import annotations

import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, HttpUrl

from ._transport import Transport
from .browser import Browser
from .change_tracker import PropertyChangeTracker
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

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://poelis-be-py-753618215333.europe-west1.run.app",
        timeout_seconds: float = 30.0,
        org_id: Optional[str] = None,
        enable_change_detection: bool = True,
        baseline_file: Optional[str] = None,
        log_file: Optional[str] = None,
    ) -> None:
        """Initialize the client with API endpoint and credentials.

        Args:
            api_key: API key for API authentication.
            base_url: Base URL of the Poelis API. Defaults to production.
            timeout_seconds: Network timeout in seconds.
            org_id: Deprecated, ignored parameter kept for backwards compatibility.
            enable_change_detection: If True, enables automatic warnings when property
                values change between accesses. When True, defaults to using
                `.poelis/baseline.json` for baseline_file and `poelis_changes.log` for
                log_file if not explicitly provided. Defaults to False.
            baseline_file: Optional path to JSON file for persistent baseline storage.
                If provided, property baselines will be saved and loaded between script runs.
                If enable_change_detection is True and this is None, defaults to
                `.poelis/baseline.json`. Defaults to None (in-memory only).
            log_file: Optional path to log file for recording property changes.
                Changes will be appended to this file. If enable_change_detection is True
                and this is None, defaults to `poelis_changes.log`. Defaults to None
                (no file logging).
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

        # Auto-configure baseline_file and log_file if change detection is enabled
        if enable_change_detection:
            if baseline_file is None:
                baseline_file = ".poelis/baseline.json"
            if log_file is None:
                log_file = "poelis_changes.log"

        # Property change tracking
        self._change_tracker = PropertyChangeTracker(
            enabled=enable_change_detection,
            baseline_file=baseline_file,
            log_file=log_file,
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

    @property
    def enable_change_detection(self) -> bool:
        """Get whether property change detection is enabled.

        Returns:
            bool: True if change detection is enabled, False otherwise.
        """
        return self._change_tracker.is_enabled()

    @enable_change_detection.setter
    def enable_change_detection(self, value: bool) -> None:
        """Enable or disable property change detection.

        Args:
            value: True to enable, False to disable.
        """
        if value:
            self._change_tracker.enable()
        else:
            self._change_tracker.disable()

    def clear_property_baselines(self) -> None:
        """Clear all recorded property baseline values.

        This resets the change tracking state, so all properties will be
        treated as new on their next access.
        """
        self._change_tracker.clear_baselines()

    def get_changed_properties(self) -> Dict[str, Dict[str, Any]]:
        """Get information about properties that have changed.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping property_id to change info.
                Currently returns empty dict as change tracking is per-access.
        """
        return self._change_tracker.get_changed_properties()

    def write_change_log(self) -> None:
        """Write all changes detected in this session to the log file.
        
        This should be called at the end of a script run to ensure all changes
        are logged, even if warnings were suppressed. If no log file is configured,
        this method does nothing.
        """
        self._change_tracker.write_change_log()


class _Deprecated:  # pragma: no cover
    pass


