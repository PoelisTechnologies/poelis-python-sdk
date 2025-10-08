"""Logging configuration for the Poelis SDK.

This module provides utilities to configure logging levels for the SDK and its dependencies.
"""

from __future__ import annotations

import logging


def configure_logging(
    level: str = "WARNING",
    disable_httpx_logs: bool = True,
    disable_urllib3_logs: bool = True,
    enable_sdk_logs: bool = False,
) -> None:
    """Configure logging for the Poelis SDK and its dependencies.
    
    Args:
        level: Logging level for the root logger (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        disable_httpx_logs: Whether to disable httpx HTTP request logs.
        disable_urllib3_logs: Whether to disable urllib3 logs.
        enable_sdk_logs: Whether to enable SDK-specific debug logs.
    """
    # Set root logger level
    numeric_level = getattr(logging, level.upper(), logging.WARNING)
    logging.basicConfig(level=numeric_level)
    
    # Configure httpx logging
    if disable_httpx_logs:
        logging.getLogger("httpx").setLevel(logging.WARNING)
    else:
        logging.getLogger("httpx").setLevel(logging.INFO)
    
    # Configure urllib3 logging
    if disable_urllib3_logs:
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    
    # Configure SDK logging
    sdk_logger = logging.getLogger("poelis_sdk")
    if enable_sdk_logs:
        sdk_logger.setLevel(logging.DEBUG)
    else:
        sdk_logger.setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given name.
    
    Args:
        name: Logger name, typically __name__.
        
    Returns:
        Logger instance.
    """
    return logging.getLogger(f"poelis_sdk.{name}")


# Convenience functions for common logging configurations
def quiet_logging() -> None:
    """Configure quiet logging - only show warnings and errors."""
    configure_logging(level="WARNING", disable_httpx_logs=True, disable_urllib3_logs=True)


def verbose_logging() -> None:
    """Configure verbose logging - show all logs including HTTP requests."""
    configure_logging(level="INFO", disable_httpx_logs=False, disable_urllib3_logs=False, enable_sdk_logs=True)


def debug_logging() -> None:
    """Configure debug logging - show everything including SDK debug logs."""
    configure_logging(level="DEBUG", disable_httpx_logs=False, disable_urllib3_logs=False, enable_sdk_logs=True)
