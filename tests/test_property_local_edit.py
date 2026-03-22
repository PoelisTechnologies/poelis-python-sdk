"""Tests for local in-session property edits and change tracking."""

from __future__ import annotations

from typing import Any

import pytest
from poelis_sdk.browser import _PropWrapper
from poelis_sdk.change_tracker import PropertyChangeTracker


class _FakeClient:
    """Lightweight fake client that only exposes a change tracker."""

    def __init__(self, tracker: PropertyChangeTracker) -> None:
        """Initialize fake client with a change tracker."""
        self._change_tracker: PropertyChangeTracker = tracker


def test_local_edit_raises_and_leaves_state_unchanged() -> None:
    """Setting `.value` should fail and direct callers to change_property()."""

    tracker = PropertyChangeTracker(enabled=True)
    prop_id = "prop-1"
    path = "ws.demo_product.draft.demo_property_mass"

    # Pretend this property was accessed through the browser so the tracker
    # knows a human-readable path for it.
    tracker.record_accessed_property(property_path=path, property_name="demo_property_mass", property_id=prop_id)

    raw: dict[str, Any] = {
        "id": prop_id,
        "readableId": "demo_property_mass",
        "value": 10,
    }
    client = _FakeClient(tracker)
    wrapper = _PropWrapper(raw, client=client)

    with pytest.raises(AttributeError, match="change_property\\(\\.\\.\\.\\)"):
        wrapper.value = 20

    # Raw payload should remain unchanged
    assert raw["value"] == 10
    # Getter should still return the original value
    assert wrapper.value == 10

    # The change tracker should not have recorded a local edit.
    assert not tracker._changes_this_session  # type: ignore[attr-defined]

