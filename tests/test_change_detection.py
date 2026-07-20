"""Tests for property change detection feature.

Tests ensure that property value changes are detected and warnings are emitted
when change detection is enabled.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any


from poelis_sdk import PoelisClient
from poelis_sdk.change_tracker import PropertyChangeTracker, PropertyValueChangedWarning

if TYPE_CHECKING:
    pass


def test_change_tracker_baseline_recording() -> None:
    """Test that baseline values are recorded on first access."""
    tracker = PropertyChangeTracker(enabled=True)
    
    # First access - should record baseline
    tracker.record_baseline("prop1", 100, "Price")
    assert "prop1" in tracker._baselines
    assert tracker._baselines["prop1"]["value"] == 100.0
    assert tracker._baselines["prop1"]["name"] == "Price"


def test_change_tracker_no_change() -> None:
    """Test that no warning is emitted when value hasn't changed."""
    tracker = PropertyChangeTracker(enabled=True)
    
    # Record baseline
    tracker.record_baseline("prop1", 100, "Price")
    
    # Check same value - should return None (no change)
    change_info = tracker.check_changed("prop1", 100, "Price")
    assert change_info is None


def test_change_tracker_detects_change() -> None:
    """Test that changes are detected correctly."""
    tracker = PropertyChangeTracker(enabled=True)
    
    # Record baseline
    tracker.record_baseline("prop1", 100, "Price")
    
    # Check changed value
    change_info = tracker.check_changed("prop1", 150, "Price")
    assert change_info is not None
    assert change_info["old_value"] == 100.0
    assert change_info["new_value"] == 150.0
    assert change_info["name"] == "Price"


def test_change_tracker_warning_emission() -> None:
    """Test that warnings are emitted when values change."""
    tracker = PropertyChangeTracker(enabled=True)
    
    # Record baseline
    tracker.record_baseline("prop1", 100, "Price")
    
    # Check changed value with warning
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        tracker.warn_if_changed("prop1", 150, "Price")
        
        assert len(w) == 1
        assert issubclass(w[0].category, PropertyValueChangedWarning)
        assert "Price" in str(w[0].message)
        assert "100" in str(w[0].message)
        assert "150" in str(w[0].message)


def test_change_tracker_disabled() -> None:
    """Test that change tracking does nothing when disabled."""
    tracker = PropertyChangeTracker(enabled=False)
    
    # Should not record baseline
    tracker.record_baseline("prop1", 100, "Price")
    assert "prop1" not in tracker._baselines
    
    # Should not detect changes
    change_info = tracker.check_changed("prop1", 150, "Price")
    assert change_info is None


def test_change_tracker_value_normalization() -> None:
    """Test that numeric values are normalized for comparison."""
    tracker = PropertyChangeTracker(enabled=True)
    
    # Record int baseline
    tracker.record_baseline("prop1", 100, "Price")
    
    # Check with float - should be considered equal
    change_info = tracker.check_changed("prop1", 100.0, "Price")
    assert change_info is None
    
    # Check with different float - should detect change
    change_info = tracker.check_changed("prop1", 100.1, "Price")
    assert change_info is not None


def test_change_tracker_list_values() -> None:
    """Test that list values are compared correctly."""
    tracker = PropertyChangeTracker(enabled=True)
    
    # Record list baseline
    tracker.record_baseline("prop1", [1, 2, 3], "Values")
    
    # Check same list - should be equal
    change_info = tracker.check_changed("prop1", [1, 2, 3], "Values")
    assert change_info is None
    
    # Check different list - should detect change
    change_info = tracker.check_changed("prop1", [1, 2, 4], "Values")
    assert change_info is not None


def test_client_enable_change_detection() -> None:
    """Test that change detection can be enabled on client."""
    client = PoelisClient(api_key="test_key", enable_change_detection=True)
    assert client.enable_change_detection is True
    
    # Can disable
    client.enable_change_detection = False
    assert client.enable_change_detection is False
    
    # Can enable
    client.enable_change_detection = True
    assert client.enable_change_detection is True


def test_client_auto_configures_files() -> None:
    """Test that baseline_file and log_file are auto-configured when enable_change_detection=True."""
    # When enable_change_detection=True, defaults should be set
    client = PoelisClient(api_key="test_key", enable_change_detection=True)
    assert client._change_tracker._baseline_file == ".poelis/baseline.json"
    assert client._change_tracker._log_file == "poelis_changes.log"
    
    # When explicitly provided, use those instead
    client2 = PoelisClient(
        api_key="test_key",
        enable_change_detection=True,
        baseline_file="custom_baseline.json",
        log_file="custom_log.log",
    )
    assert client2._change_tracker._baseline_file == "custom_baseline.json"
    assert client2._change_tracker._log_file == "custom_log.log"
    
    # When enable_change_detection=False, defaults should be None
    client3 = PoelisClient(api_key="test_key", enable_change_detection=False)
    assert client3._change_tracker._baseline_file is None
    assert client3._change_tracker._log_file is None


def test_client_clear_baselines() -> None:
    """Test that baselines can be cleared."""
    client = PoelisClient(api_key="test_key", enable_change_detection=True)
    
    # Record a baseline
    client._change_tracker.record_baseline("prop1", 100, "Price")
    assert "prop1" in client._change_tracker._baselines
    
    # Clear baselines
    client.clear_property_baselines()
    assert "prop1" not in client._change_tracker._baselines


def test_property_wrapper_change_detection() -> None:
    """Test that property wrapper detects changes when enabled."""
    from poelis_sdk.browser import _PropWrapper
    
    # Create a mock client with change tracking enabled
    client = PoelisClient(api_key="test_key", enable_change_detection=True)
    
    # Create property wrapper with client
    prop_data = {
        "id": "prop1",
        "readableId": "Price",
        "value": "100",
        "parsedValue": 100,
        "__typename": "NumericProperty",
    }
    wrapper = _PropWrapper(prop_data, client=client)
    
    # First access - should record baseline
    value1 = wrapper.value
    assert value1 == 100
    assert "prop1" in client._change_tracker._baselines
    
    # Simulate value change by updating the property data
    prop_data["value"] = "150"
    prop_data["parsedValue"] = 150
    
    # Second access - should detect change and warn
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        value2 = wrapper.value
        
        assert value2 == 150
        assert len(w) == 1
        assert issubclass(w[0].category, PropertyValueChangedWarning)


def test_property_wrapper_no_change_detection() -> None:
    """Test that property wrapper doesn't track when disabled."""
    from poelis_sdk.browser import _PropWrapper
    
    # Create client with change tracking disabled
    client = PoelisClient(api_key="test_key", enable_change_detection=False)
    
    # Create property wrapper
    prop_data = {
        "id": "prop1",
        "readableId": "Price",
        "value": "100",
        "parsedValue": 100,
        "__typename": "NumericProperty",
    }
    wrapper = _PropWrapper(prop_data, client=client)
    
    # Access property - should not record baseline
    value = wrapper.value
    assert value == 100
    assert "prop1" not in client._change_tracker._baselines


def test_property_wrapper_versioned_property_skipped(tmp_path: Any) -> None:
    """Test that versioned properties are not tracked (they're immutable)."""
    from poelis_sdk.browser import _PropWrapper
    
    # Use temporary baseline file to avoid persistence between tests
    baseline_file = str(tmp_path / "test_baseline.json")
    
    # Create client with change tracking enabled
    client = PoelisClient(
        api_key="test_key",
        enable_change_detection=True,
        baseline_file=baseline_file,
    )
    
    # Create versioned property (has productVersionNumber)
    prop_data = {
        "id": "prop1",
        "readableId": "Price",
        "value": "100",
        "parsedValue": 100,
        "productVersionNumber": 5,  # Versioned property
        "__typename": "NumericProperty",
    }
    wrapper = _PropWrapper(prop_data, client=client)
    
    # Access property - should not record baseline for versioned properties
    value = wrapper.value
    assert value == 100
    assert "prop1" not in client._change_tracker._baselines


def test_property_wrapper_missing_id(tmp_path: Any) -> None:
    """Test that properties without IDs are handled gracefully."""
    from poelis_sdk.browser import _PropWrapper
    
    # Use temporary baseline file to avoid persistence between tests
    baseline_file = str(tmp_path / "test_baseline.json")
    
    # Create client with change tracking enabled
    client = PoelisClient(
        api_key="test_key",
        enable_change_detection=True,
        baseline_file=baseline_file,
    )
    
    # Create property without ID
    prop_data = {
        "readableId": "Price",
        "value": "100",
        "parsedValue": 100,
        "__typename": "NumericProperty",
    }
    wrapper = _PropWrapper(prop_data, client=client)
    
    # Should not crash, just return value without tracking
    value = wrapper.value
    assert value == 100
    # No baseline should be recorded since there's no ID
    assert len(client._change_tracker._baselines) == 0


def test_persistent_baseline_storage(tmp_path: Any) -> None:
    """Test that baselines can be saved and loaded from a file."""
    
    baseline_file = str(tmp_path / "baselines.json")
    
    # Create tracker with baseline file
    tracker1 = PropertyChangeTracker(enabled=True, baseline_file=baseline_file)
    
    # Record a baseline
    tracker1.record_baseline("prop1", 100, "Price")
    assert "prop1" in tracker1._baselines
    
    # Create a new tracker and load from file
    tracker2 = PropertyChangeTracker(enabled=True, baseline_file=baseline_file)
    assert "prop1" in tracker2._baselines
    assert tracker2._baselines["prop1"]["value"] == 100.0
    assert tracker2._baselines["prop1"]["name"] == "Price"


def test_change_logging(tmp_path: Any) -> None:
    """Test that changes are logged to a file."""
    import os
    
    log_file = str(tmp_path / "changes.log")
    
    # Create tracker with log file
    tracker = PropertyChangeTracker(enabled=True, log_file=log_file)
    
    # Record baseline
    tracker.record_baseline("prop1", 100, "Price")
    
    # Detect change
    change_info = tracker.check_changed("prop1", 150, "Price")
    assert change_info is not None
    
    # Log the change
    tracker._log_change(change_info)
    
    # Check log file exists and contains change info
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Price" in content
        assert "100" in content
        assert "150" in content


def test_write_change_log(tmp_path: Any) -> None:
    """Test that write_change_log writes all session changes."""
    import os
    
    log_file = str(tmp_path / "changes.log")
    
    # Create tracker with log file
    tracker = PropertyChangeTracker(enabled=True, log_file=log_file)
    
    # Record baselines and detect changes
    tracker.record_baseline("prop1", 100, "Price")
    tracker.record_baseline("prop2", 200, "Weight")
    
    tracker.check_changed("prop1", 150, "Price")
    tracker.check_changed("prop2", 250, "Weight")
    
    # Write change log
    tracker.write_change_log()
    
    # Check log file
    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        content = f.read()
        assert "Price" in content
        assert "Weight" in content
        assert "100" in content
        assert "150" in content
        assert "200" in content
        assert "250" in content


def test_client_with_persistent_storage(tmp_path: Any) -> None:
    """Test that client can use persistent storage and logging."""
    baseline_file = str(tmp_path / "baselines.json")
    log_file = str(tmp_path / "changes.log")
    
    # Create client with persistent storage
    client1 = PoelisClient(
        api_key="test_key",
        enable_change_detection=True,
        baseline_file=baseline_file,
        log_file=log_file,
    )
    
    # Record a baseline
    client1._change_tracker.record_baseline("prop1", 100, "Price")
    
    # Create a new client and verify it loads baselines
    client2 = PoelisClient(
        api_key="test_key",
        enable_change_detection=True,
        baseline_file=baseline_file,
        log_file=log_file,
    )
    
    assert "prop1" in client2._change_tracker._baselines
    
    # Detect change and write log
    change_info = client2._change_tracker.check_changed("prop1", 150, "Price")
    assert change_info is not None
    
    client2.write_change_log()
    
    # Verify log file was created
    import os
    assert os.path.exists(log_file)

