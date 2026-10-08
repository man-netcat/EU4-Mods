"""EU4-specific parsing and generation utilities.

This module handles EU4-specific parsing tasks, condition building,
and event generation utilities.
"""

import pyradox


def build_conditions(tree) -> str:
    """Build a condition string from a parsed tree structure."""
    return " ".join(map(str.strip, str(tree).split("\n"))).strip()


def build_tags(tree) -> list[str]:
    """Extract tags from a parsed tree structure."""
    return list(tree["tags"].values()) if tree and "tags" in tree else []


def build_change_tag_if(limit: str, target_tag: str) -> str:
    """Build an EU4 if-block that switches to the given tag when limit holds."""
    return f"        if = {{ limit = {{ {limit} }} change_tag = {target_tag} }}"


def read_rule_file(path: str):
    """Parse an EU4 rule file using pyradox."""
    return pyradox.txt.parse_file(path=path, game="EU4", path_relative_to_game=False)
