from __future__ import annotations

import json
import os
import time
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

"""Property change tracking for Poelis SDK.

This module provides utilities to track property values and warn users
when values change between script/notebook runs.
"""


class PropertyValueChangedWarning(UserWarning):
    """Warning emitted when a property value has changed since first access."""

    pass


class ItemOrPropertyDeletedWarning(UserWarning):
    """Warning emitted when an item or property that was previously accessed has been deleted."""

    pass


class PropertyChangeTracker:
    """Tracks property values and detects changes.

    Records baseline values when properties are first accessed, and compares
    subsequent accesses to detect changes. Emits warnings when changes are detected.
    Supports persistent storage via JSON files and change logging.
    """

    def __init__(
        self,
        enabled: bool = False,
        baseline_file: Optional[str] = None,
        log_file: Optional[str] = None,
    ) -> None:
        """Initialize the change tracker.

        Args:
            enabled: Whether change detection is enabled.
            baseline_file: Optional path to JSON file for persistent baseline storage.
                If None, baselines are only stored in memory. Defaults to None.
            log_file: Optional path to log file for recording changes.
                If None, changes are only logged via warnings. Defaults to None.
        """
        self._enabled = enabled
        self._baselines: Dict[str, Dict[str, Any]] = {}
        # Key: property_id, Value: {value, name, first_accessed_at}
        self._accessed_items: Dict[str, Dict[str, Any]] = {}
        # Key: item_path (e.g., "workspace.product.item"), Value: {name, first_accessed_at, item_id}
        self._accessed_properties: Dict[str, Dict[str, Any]] = {}
        # Key: property_path (e.g., "workspace.product.item.property"), Value: {name, property_id, first_accessed_at}
        self._baseline_file: Optional[str] = baseline_file
        self._log_file: Optional[str] = log_file
        self._changes_this_session: List[Dict[str, Any]] = []
        self._deletions_this_session: List[Dict[str, Any]] = []
        
        # Load baselines from file if it exists
        if self._baseline_file and os.path.exists(self._baseline_file):
            self._load_baselines()

    def is_enabled(self) -> bool:
        """Check if change detection is enabled.

        Returns:
            bool: True if change detection is enabled, False otherwise.
        """
        return self._enabled

    def enable(self) -> None:
        """Enable change detection."""
        self._enabled = True

    def disable(self) -> None:
        """Disable change detection."""
        self._enabled = False

    def clear_baselines(self) -> None:
        """Clear all recorded baseline values."""
        self._baselines.clear()
        self._accessed_items.clear()
        self._accessed_properties.clear()
        # Also delete the baseline file if it exists
        if self._baseline_file:
            baseline_path = Path(self._baseline_file)
            if not baseline_path.is_absolute():
                baseline_path = Path.cwd() / baseline_path
            if baseline_path.exists():
                try:
                    baseline_path.unlink()
                except Exception:
                    pass  # Silently ignore errors

    def record_baseline(
        self,
        property_id: str,
        value: Any,
        name: Optional[str] = None,
        updated_at: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> None:
        """Record a baseline value for a property.

        If the property has already been recorded, this does nothing (first access wins).

        Args:
            property_id: Unique identifier for the property.
            value: The property value to record as baseline.
            name: Optional display name for the property.
            updated_at: Optional ISO 8601 timestamp when the property was last updated.
            updated_by: Optional user ID of the last updater.
        """
        if not self._enabled:
            return

        if property_id not in self._baselines:
            self._baselines[property_id] = {
                "value": self._normalize_value(value),
                "name": name or property_id,
                "first_accessed_at": time.time(),
                "updated_at": updated_at,
                "updated_by": updated_by,
            }
            # Save baselines to file if persistent storage is enabled
            if self._baseline_file:
                self._save_baselines()

    def check_changed(
        self,
        property_id: str,
        current_value: Any,
        name: Optional[str] = None,
        updated_at: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Check if a property value has changed and return change info if so.

        Args:
            property_id: Unique identifier for the property.
            current_value: The current value to compare against baseline.
            name: Optional display name for the property (used if not in baseline).
            updated_at: Optional ISO 8601 timestamp when the property was last updated.
            updated_by: Optional user ID of the last updater.

        Returns:
            Optional[Dict[str, Any]]: Change information if changed, None otherwise.
            Contains: old_value, new_value, name, first_accessed_at, time_since_first_access,
            updated_at, updated_by.
        """
        if not self._enabled:
            return None

        if property_id not in self._baselines:
            # First access - record as baseline
            self.record_baseline(property_id, current_value, name, updated_at, updated_by)
            return None

        baseline = self._baselines[property_id]
        normalized_current = self._normalize_value(current_value)
        normalized_baseline = baseline["value"]

        if not self._values_equal(normalized_current, normalized_baseline):
            # Value has changed
            first_accessed_at = baseline["first_accessed_at"]
            time_since = time.time() - first_accessed_at
            change_info = {
                "property_id": property_id,
                "old_value": baseline["value"],
                "new_value": normalized_current,
                "name": baseline.get("name") or name or property_id,
                "first_accessed_at": first_accessed_at,
                "time_since_first_access": time_since,
                "detected_at": time.time(),
                "updated_at": updated_at,  # When it was changed in webapp
                "updated_by": updated_by,  # Who changed it
            }
            # Record change for logging
            self._changes_this_session.append(change_info)
            # Update baseline to new value for next run comparison
            self._baselines[property_id]["value"] = normalized_current
            self._baselines[property_id]["first_accessed_at"] = time.time()  # Reset timestamp
            self._baselines[property_id]["updated_at"] = updated_at
            self._baselines[property_id]["updated_by"] = updated_by
            if self._baseline_file:
                self._save_baselines()
            return change_info

        return None

    def get_changed_properties(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all properties that have changed.

        Note: This only returns properties that have been checked at least twice.
        Properties that were recorded but never checked again won't appear here.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping property_id to change info.
        """
        # This would require tracking which properties were checked, which we don't do yet.
        # For now, return empty dict. Can be enhanced later if needed.
        return {}

    def _normalize_value(self, value: Any) -> Any:
        """Normalize a value for comparison.

        Handles type conversions that should be considered equal (e.g., int vs float).

        Args:
            value: The value to normalize.

        Returns:
            Any: Normalized value.
        """
        # Handle None
        if value is None:
            return None

        # Handle numeric types - convert to float for comparison
        if isinstance(value, (int, float)):
            return float(value)

        # Handle lists/arrays - normalize recursively
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]

        # For other types (strings, etc.), return as-is
        return value

    def _values_equal(self, value1: Any, value2: Any) -> bool:
        """Check if two normalized values are equal.

        Args:
            value1: First value to compare.
            value2: Second value to compare.

        Returns:
            bool: True if values are equal, False otherwise.
        """
        # Handle None
        if value1 is None and value2 is None:
            return True
        if value1 is None or value2 is None:
            return False

        # Handle lists/arrays
        if isinstance(value1, list) and isinstance(value2, list):
            if len(value1) != len(value2):
                return False
            return all(self._values_equal(v1, v2) for v1, v2 in zip(value1, value2))

        # For numeric types, use approximate equality for floats
        if isinstance(value1, float) and isinstance(value2, float):
            # Use a small epsilon for float comparison
            return abs(value1 - value2) < 1e-10

        # For other types, use standard equality
        return value1 == value2

    def _format_time_delta(self, seconds: float) -> str:
        """Format a time delta in a human-readable way.

        Args:
            seconds: Time delta in seconds.

        Returns:
            str: Human-readable time delta (e.g., "2 days ago", "3 hours ago").
        """
        if seconds < 60:
            return f"{int(seconds)} seconds ago"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"

    def warn_if_changed(
        self,
        property_id: str,
        current_value: Any,
        name: Optional[str] = None,
        updated_at: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> None:
        """Check for changes and emit a warning if the value has changed.

        Args:
            property_id: Unique identifier for the property.
            current_value: The current value to check.
            name: Optional display name for the property.
            updated_at: Optional ISO 8601 timestamp when the property was last updated.
            updated_by: Optional user ID of the last updater.
        """
        if not self._enabled:
            return

        change_info = self.check_changed(property_id, current_value, name, updated_at, updated_by)
        if change_info:
            # Format warning message with update info
            message_parts = [
                f"Property '{change_info['name']}' changed: "
                f"{change_info['old_value']} → {change_info['new_value']}"
            ]
            
            # Add updated_by and updated_at if available
            if change_info.get("updated_by"):
                message_parts.append(f"(updated by {change_info['updated_by']}")
            if change_info.get("updated_at"):
                # Format the ISO timestamp to be more readable
                try:
                    dt = datetime.fromisoformat(change_info["updated_at"].replace("Z", "+00:00"))
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                    message_parts.append(f"at {formatted_time})")
                except Exception:
                    message_parts.append(f"at {change_info['updated_at']}")
            
            # Fallback to time since first access if updated_at not available
            if not change_info.get("updated_at"):
                time_str = self._format_time_delta(change_info["time_since_first_access"])
                message_parts.append(f"(first accessed {time_str})")
            
            # Hint user to check the change log file (with resolved path) if configured
            if self._log_file:
                try:
                    log_path = Path(self._log_file)
                    if not log_path.is_absolute():
                        log_path = Path.cwd() / log_path
                    # Show a short path like `/poelis-python-sdk/poelis_changes.log`
                    project_dir = log_path.parent.name
                    display_path = f"/{project_dir}/{log_path.name}"
                    message_parts.append(f"[see change log: {display_path}]")
                except Exception:
                    # If path resolution fails, skip the hint rather than breaking the warning
                    pass
            
            message = " ".join(message_parts)
            
            # Use a custom format that only shows the message (no file path/line number)
            original_format = warnings.formatwarning
            def simple_format(message, category, filename, lineno, line=None):
                return f"{category.__name__}: {message}\n"
            
            warnings.formatwarning = simple_format
            try:
                warnings.warn(message, PropertyValueChangedWarning, stacklevel=3)
            finally:
                warnings.formatwarning = original_format
            
            # Log to file if enabled
            if self._log_file:
                self._log_change(change_info)
    
    def write_change_log(self) -> None:
        """Write all changes detected in this session to the log file.
        
        This should be called at the end of a script run to ensure all changes
        are logged, even if warnings were suppressed.
        """
        if not self._log_file or not self._changes_this_session:
            return
        
        # Resolve log file path (relative paths are relative to current working directory)
        log_path = Path(self._log_file)
        # If it's a relative path, resolve it relative to current working directory
        if not log_path.is_absolute():
            log_path = Path.cwd() / log_path
        
        # Ensure log directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append to log file
        with open(log_path, "a", encoding="utf-8") as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n{'='*80}\n")
            f.write(f"Session: {timestamp}\n")
            f.write(f"{'='*80}\n")
            
            if self._changes_this_session:
                f.write(f"Detected {len(self._changes_this_session)} property change(s):\n\n")
                for change in self._changes_this_session:
                    f.write(f"  Property: {change['name']} (ID: {change['property_id']})\n")
                    f.write(f"    Old value: {change['old_value']}\n")
                    f.write(f"    New value: {change['new_value']}\n")
                    if change.get("updated_by"):
                        f.write(f"    Updated by: {change['updated_by']}\n")
                    if change.get("updated_at"):
                        f.write(f"    Updated at: {change['updated_at']}\n")
                    time_str = self._format_time_delta(change["time_since_first_access"])
                    f.write(f"    First accessed: {time_str}\n")
                    f.write(f"    Detected at: {datetime.fromtimestamp(change['detected_at']).isoformat()}\n")
                    f.write("\n")
            if self._deletions_this_session:
                f.write(f"\nDetected {len(self._deletions_this_session)} deletion(s):\n\n")
                for deletion in self._deletions_this_session:
                    f.write(f"  {deletion['type'].title()}: {deletion['name']} (Path: {deletion['path']})\n")
                    f.write(f"    Detected at: {datetime.fromtimestamp(deletion['detected_at']).isoformat()}\n")
                    f.write("\n")
            
            if not self._changes_this_session and not self._deletions_this_session:
                f.write("No property changes or deletions detected.\n")
    
    def record_accessed_item(self, item_path: str, item_name: str, item_id: Optional[str] = None) -> None:
        """Record that an item was accessed.
        
        Args:
            item_path: Path to the item (e.g., "workspace.product.item").
            item_name: Display name of the item.
            item_id: Optional item ID.
        """
        if not self._enabled:
            return
        
        if item_path not in self._accessed_items:
            self._accessed_items[item_path] = {
                "name": item_name,
                "item_id": item_id,
                "first_accessed_at": time.time(),
            }
            if self._baseline_file:
                self._save_baselines()
    
    def record_accessed_property(self, property_path: str, property_name: str, property_id: Optional[str] = None) -> None:
        """Record that a property was accessed.
        
        Args:
            property_path: Path to the property (e.g., "workspace.product.item.property").
            property_name: Display name of the property.
            property_id: Optional property ID.
        """
        if not self._enabled:
            return
        
        if property_path not in self._accessed_properties:
            self._accessed_properties[property_path] = {
                "name": property_name,
                "property_id": property_id,
                "first_accessed_at": time.time(),
            }
            if self._baseline_file:
                self._save_baselines()
    
    def check_item_deleted(self, item_path: str) -> Optional[Dict[str, Any]]:
        """Check if an item that was previously accessed has been deleted.
        
        Args:
            item_path: Path to the item (e.g., "workspace.product.item").
        
        Returns:
            Optional[Dict[str, Any]]: Deletion information if the item was deleted, None otherwise.
        """
        if not self._enabled:
            return None
        
        if item_path in self._accessed_items:
            # Item was accessed before but doesn't exist now - it was deleted
            item_info = self._accessed_items[item_path]
            deletion_info = {
                "type": "item",
                "path": item_path,
                "name": item_info.get("name", item_path),
                "item_id": item_info.get("item_id"),
                "first_accessed_at": item_info.get("first_accessed_at", time.time()),
                "detected_at": time.time(),
            }
            self._deletions_this_session.append(deletion_info)
            # Remove from accessed_items since it's been deleted
            del self._accessed_items[item_path]
            if self._baseline_file:
                self._save_baselines()
            return deletion_info
        
        # Fallback: Check if any property path contains this item path
        # This handles cases where the item was accessed via a property but not tracked as an item
        for prop_path, prop_info in list(self._accessed_properties.items()):
            # Check if property path starts with item_path (e.g., "workspace.product.item.property" starts with "workspace.product.item")
            if prop_path.startswith(item_path + "."):
                # Extract item name from property path or use the last part of item_path
                item_name = item_path.split(".")[-1] if "." in item_path else item_path
                deletion_info = {
                    "type": "item",
                    "path": item_path,
                    "name": item_name,
                    "item_id": None,
                    "first_accessed_at": prop_info.get("first_accessed_at", time.time()),
                    "detected_at": time.time(),
                }
                self._deletions_this_session.append(deletion_info)
                # Remove all properties under this item path
                properties_to_remove = [
                    p for p in self._accessed_properties.keys()
                    if p.startswith(item_path + ".")
                ]
                for prop_to_remove in properties_to_remove:
                    del self._accessed_properties[prop_to_remove]
                if self._baseline_file:
                    self._save_baselines()
                return deletion_info
        
        return None
    
    def check_property_deleted(self, property_path: str) -> Optional[Dict[str, Any]]:
        """Check if a property that was previously accessed has been deleted.
        
        Args:
            property_path: Path to the property (e.g., "workspace.product.item.property").
        
        Returns:
            Optional[Dict[str, Any]]: Deletion information if the property was deleted, None otherwise.
        """
        if not self._enabled:
            return None
        
        if property_path in self._accessed_properties:
            # Property was accessed before but doesn't exist now - it was deleted
            prop_info = self._accessed_properties[property_path]
            deletion_info = {
                "type": "property",
                "path": property_path,
                "name": prop_info.get("name", property_path),
                "property_id": prop_info.get("property_id"),
                "first_accessed_at": prop_info.get("first_accessed_at", time.time()),
                "detected_at": time.time(),
            }
            self._deletions_this_session.append(deletion_info)
            # Remove from accessed_properties since it's been deleted
            del self._accessed_properties[property_path]
            # Also remove from baselines if it exists
            if deletion_info.get("property_id") and deletion_info["property_id"] in self._baselines:
                del self._baselines[deletion_info["property_id"]]
            if self._baseline_file:
                self._save_baselines()
            return deletion_info
        
        return None
    
    def warn_if_deleted(self, item_path: Optional[str] = None, property_path: Optional[str] = None) -> None:
        """Check for deletions and emit warnings if items or properties have been deleted.
        
        Args:
            item_path: Optional path to an item that doesn't exist.
            property_path: Optional path to a property that doesn't exist.
        """
        if not self._enabled:
            return
        
        deletion_info = None
        if property_path:
            deletion_info = self.check_property_deleted(property_path)
        elif item_path:
            deletion_info = self.check_item_deleted(item_path)
        
        if deletion_info:
            # Format warning message
            message = (
                f"{deletion_info['type'].title()} '{deletion_info['name']}' has been deleted or moved"
            )
            
            # Add log file hint if available
            if self._log_file:
                try:
                    log_path = Path(self._log_file)
                    if not log_path.is_absolute():
                        log_path = Path.cwd() / log_path
                    # Show path from project root
                    try:
                        cwd_parts = Path.cwd().parts
                        log_parts = log_path.parts
                        # Find common prefix and show relative path
                        common_len = 0
                        for i in range(min(len(cwd_parts), len(log_parts))):
                            if cwd_parts[i] == log_parts[i]:
                                common_len = i + 1
                            else:
                                break
                        if common_len > 0:
                            rel_parts = log_parts[common_len:]
                            if rel_parts:
                                display_path = "/" + "/".join(rel_parts)
                            else:
                                display_path = str(log_path.name)
                        else:
                            display_path = str(log_path)
                    except Exception:
                        display_path = str(log_path)
                    message += f" [see change log: {display_path}]"
                except Exception:
                    pass  # Skip log path hint if it fails
            
            # Use a custom format that only shows the message (no file path/line number)
            original_format = warnings.formatwarning
            def simple_format(message, category, filename, lineno, line=None):
                return f"{category.__name__}: {message}\n"
            
            warnings.formatwarning = simple_format
            try:
                warnings.warn(message, ItemOrPropertyDeletedWarning, stacklevel=4)
            finally:
                warnings.formatwarning = original_format
            
            # Log to file if enabled
            if self._log_file:
                self._log_deletion(deletion_info)
    
    def _log_deletion(self, deletion_info: Dict[str, Any]) -> None:
        """Log a deletion to the log file.
        
        Args:
            deletion_info: Dictionary containing deletion information.
        """
        if not self._log_file:
            return
        
        try:
            # Resolve log file path
            log_path = Path(self._log_file)
            if not log_path.is_absolute():
                log_path = Path.cwd() / log_path
            
            # Ensure log directory exists
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to log file
            with open(log_path, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(
                    f"[{timestamp}] {deletion_info['type'].title()} '{deletion_info['name']}' "
                    f"(Path: {deletion_info['path']}) has been deleted or moved\n"
                )
        except Exception:
            # Silently ignore log errors to avoid breaking property access
            pass
    
    def _load_baselines(self) -> None:
        """Load baselines from the baseline file."""
        if not self._baseline_file:
            return
        
        # Resolve baseline file path (relative paths are relative to current working directory)
        baseline_path = Path(self._baseline_file)
        if not baseline_path.is_absolute():
            baseline_path = Path.cwd() / baseline_path
        
        if not baseline_path.exists():
            return
        
        try:
            with open(baseline_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._baselines = data.get("baselines", {})
                self._accessed_items = data.get("accessed_items", {})
                self._accessed_properties = data.get("accessed_properties", {})
        except Exception:
            # If loading fails, start with empty baselines
            self._baselines = {}
            self._accessed_items = {}
            self._accessed_properties = {}
    
    def _save_baselines(self) -> None:
        """Save baselines to the baseline file.
        
        Only saves baselines for properties that are currently being tracked,
        keeping the baseline file clean and containing only relevant data.
        """
        if not self._baseline_file:
            return
        
        try:
            # Resolve baseline file path (relative paths are relative to current working directory)
            baseline_path = Path(self._baseline_file)
            if not baseline_path.is_absolute():
                baseline_path = Path.cwd() / baseline_path
            
            # Ensure directory exists
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Only keep baselines for properties that are currently being tracked
            # This keeps the baseline file clean and removes old/stale data
            # Note: We keep all baselines that exist, but we'll clean up deleted ones
            # The filtering happens when items/properties are deleted, not here
            filtered_baselines = self._baselines.copy()
            
            # Save to file
            with open(baseline_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "baselines": filtered_baselines,
                        "accessed_items": self._accessed_items,
                        "accessed_properties": self._accessed_properties,
                        "last_updated": time.time(),
                    },
                    f,
                    indent=2,
                )
        except Exception:
            # Silently ignore save errors to avoid breaking property access
            pass
    
    def _log_change(self, change_info: Dict[str, Any]) -> None:
        """Log a single change to the log file.
        
        Args:
            change_info: Dictionary containing change information.
        """
        if not self._log_file:
            return
        
        try:
            # Resolve log file path (relative paths are relative to current working directory)
            log_path = Path(self._log_file)
            # If it's a relative path, resolve it relative to current working directory
            if not log_path.is_absolute():
                log_path = Path.cwd() / log_path
            
            # Ensure log directory exists
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Append to log file
            with open(log_path, "a", encoding="utf-8") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message_parts = [
                    f"[{timestamp}] Property '{change_info['name']}' "
                    f"changed: {change_info['old_value']} → {change_info['new_value']}"
                ]
                
                # Add updated_by and updated_at if available
                if change_info.get("updated_by"):
                    message_parts.append(f"(updated by {change_info['updated_by']}")
                if change_info.get("updated_at"):
                    # Format updated_at in the same style as the log prefix
                    try:
                        dt = datetime.fromisoformat(
                            change_info["updated_at"].replace("Z", "+00:00")
                        )
                        formatted_updated_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        formatted_updated_at = change_info["updated_at"]
                    message_parts.append(f"at {formatted_updated_at})")
                
                # Fallback to time since first access if updated_at not available
                if not change_info.get("updated_at"):
                    time_str = self._format_time_delta(change_info["time_since_first_access"])
                    message_parts.append(f"(first accessed {time_str})")
                
                f.write(" ".join(message_parts) + "\n")
        except Exception:
            # Silently ignore log errors to avoid breaking property access
            pass