"""Tests for local in-session property edits and change tracking."""

from __future__ import annotations

from typing import Any, Optional

import warnings

from poelis_sdk.browser import _PropWrapper
from poelis_sdk.change_tracker import PropertyChangeTracker, PropertyValueChangedWarning


class _FakeClient:
    """Lightweight fake client that only exposes a change tracker."""

    def __init__(self, tracker: PropertyChangeTracker) -> None:
        """Initialize fake client with a change tracker."""
        self._change_tracker: PropertyChangeTracker = tracker


def test_local_edit_emits_warning_and_updates_value() -> None:
    """Setting `.value` on a property wrapper should warn and update raw value."""

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

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", PropertyValueChangedWarning)
        wrapper.value = 20

    # Raw payload should reflect the new value
    assert raw["value"] == 20
    # Getter should now return the new value
    assert wrapper.value == 20

    # A warning should have been emitted
    local_warnings = [w for w in caught if issubclass(w.category, PropertyValueChangedWarning)]
    assert len(local_warnings) == 1

    # The change tracker should have recorded the change with a path.
    assert tracker._changes_this_session  # type: ignore[attr-defined]
    change: Optional[dict[str, Any]] = tracker._changes_this_session[-1]  # type: ignore[attr-defined]
    assert change is not None
    assert change.get("property_id") == prop_id
    assert change.get("property_path") == path


