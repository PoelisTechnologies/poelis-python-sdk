"""Poelis Python SDK public exports.

Exposes the primary client and resolves the package version from installed
metadata so it stays in sync with ``pyproject.toml`` without manual edits.
"""

from importlib import metadata

from .client import PoelisClient
from .logging import configure_logging, debug_logging, get_logger, quiet_logging, verbose_logging

__all__ = ["PoelisClient", "__version__", "configure_logging", "quiet_logging", "verbose_logging", "debug_logging", "get_logger"]

def _resolve_version() -> str:
    """Return installed package version or a dev fallback.

    Returns:
        str: Version string from package metadata, or ``"0.0.0-dev"`` when
        metadata is unavailable (e.g., editable installs without built metadata).
    """

    try:
        return metadata.version("poelis-sdk")
    except metadata.PackageNotFoundError:
        return "0.0.0-dev"


__version__: str = _resolve_version()


