"""File operation utilities for the EU4 Dynamic Names Generator.

This module provides helper functions for file and directory operations,
including path building and file writing with automatic directory creation.
"""

import os
from ..defines.paths import MOD_PATH


def ensure_directory(path: str):
    """Utility function to ensure a directory exists."""
    os.makedirs(path, exist_ok=True)


def write_file_with_directory(file_path: str, content: str, encoding: str = "utf-8"):
    """Write content to a file, ensuring the directory exists first."""
    ensure_directory(os.path.dirname(file_path))
    with open(file_path, "w+", encoding=encoding) as f:
        f.write(content)


def build_mod_path(*path_components: str) -> str:
    """Build a path relative to MOD_PATH."""
    return os.path.join(MOD_PATH, *path_components)


def build_event_file_path(event_name: str) -> str:
    """Build the path for an event file."""
    return build_mod_path("events", f"{event_name}_events.txt")


def build_localisation_file_path(event_name: str) -> str:
    """Build the path for a localisation file."""
    return build_mod_path("localisation", f"{event_name}_localisation_l_english.yml")


def build_master_event_file_path(event_name: str) -> str:
    """Build the path for a master event file."""
    return build_mod_path("events", f"{event_name}_master_events.txt")


def build_on_actions_file_path(event_name: str) -> str:
    """Build the path for an on_actions file."""
    return build_mod_path("common", "on_actions", f"{event_name}_on_actions.txt")


def build_decisions_file_path(event_name: str) -> str:
    """Build the path for a decisions file."""
    return build_mod_path("decisions", f"{event_name}_decisions.txt")


def build_global_localisation_file_path(event_name: str) -> str:
    """Build the path for a global localisation file."""
    return build_mod_path("localisation", f"{event_name}_global_localisation_l_english.yml")