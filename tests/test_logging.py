"""Tests for public logging helpers."""

from __future__ import annotations

import logging

from poelis_sdk.logging import (
    configure_logging,
    debug_logging,
    get_logger,
    quiet_logging,
    verbose_logging,
)


def test_get_logger_namespaced() -> None:
    logger = get_logger("demo")
    assert logger.name == "poelis_sdk.demo"


def test_quiet_logging_sets_warning() -> None:
    quiet_logging()
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("poelis_sdk").level == logging.WARNING


def test_verbose_and_debug_enable_sdk_logs() -> None:
    verbose_logging()
    assert logging.getLogger("poelis_sdk").level == logging.DEBUG
    debug_logging()
    assert logging.getLogger("poelis_sdk").level == logging.DEBUG
    configure_logging(level="ERROR", enable_sdk_logs=False)
    assert logging.getLogger("poelis_sdk").level == logging.WARNING
