"""File parsing utilities for the EU4 Dynamic Tags Generator.

This module handles parsing of various data files including rules,
tag lists and configuration files.
"""

import os
from ..classes.Rule import Rule
from ..core.logging_utils import log_warning
from .eu4_parsing import build_conditions, build_tags, read_rule_file


def read_lines(path: str) -> list[str]:
    """Read lines from a file, filtering out empty lines and comments."""
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def read_modules_config(config_path: str) -> list[str]:
    """Read module names from modules.conf, filtering out comments and empty lines."""
    if not os.path.exists(config_path):
        # Fallback to directory listing if config doesn't exist
        modules_dir = os.path.dirname(config_path)
        modules_root = os.path.join(modules_dir, "modules")
        if os.path.exists(modules_root):
            return sorted(os.listdir(modules_root))
        return []

    return read_lines(config_path)


def read_conf_paths(config_path: str) -> list[str]:
    """Read an ordered list of root directories from a config file.

    Supports comments, `~` expansion and paths relative to the working
    directory. Missing directories are reported and skipped.
    """
    paths = []
    for line in read_lines(config_path):
        path = os.path.expandvars(os.path.expanduser(line))
        if not os.path.isabs(path):
            path = os.path.abspath(path)
        if not os.path.isdir(path):
            log_warning("config", f"{config_path}: skipping missing root '{line}'")
            continue
        paths.append(path)
    return paths


def read_tags_list(path: str) -> list[str]:
    """Read the list of base tags for a module."""
    return read_lines(path)


def parse_rule_data(key: str, rule_data: dict, parent_tags=None, parent_conditions="") -> list[Rule]:
    """Recursively parse rule data (grouped or regular)."""
    if parent_tags is None:
        parent_tags = []

    rules: list[Rule] = []

    group_tags = parent_tags + build_tags(rule_data)
    group_conditions = parent_conditions
    if "conditions" in rule_data:
        if parent_conditions:
            group_conditions = (
                f"{parent_conditions} {build_conditions(rule_data['conditions'])}"
            )
        else:
            group_conditions = build_conditions(rule_data["conditions"])

    # Handle grouped rules
    if "group" in rule_data:
        for sub_key in rule_data["group"]:
            sub_rule = rule_data["group"][sub_key]
            rules.extend(
                parse_rule_data(f"{key}_{sub_key}", sub_rule, group_tags, group_conditions)
            )
        return rules

    rules.append(
        Rule(
            id=key,
            tags=group_tags,
            conditions=group_conditions,
        )
    )
    return rules


def parse_rule_file(file_path: str) -> list[Rule]:
    """Parse a single rule file and return a list of rules."""
    data = read_rule_file(file_path)
    all_rules: list[Rule] = []

    for key in data:
        all_rules.extend(parse_rule_data(key, data[key]))

    return all_rules


def parse_rules_dir(dir_path: str) -> list[Rule]:
    """Parse all rule files in a directory and return a combined list of rules."""
    if not dir_path or not os.path.exists(dir_path):
        return []

    all_rules: list[Rule] = []
    for filename in sorted(os.listdir(dir_path)):
        file_path = os.path.join(dir_path, filename)
        if os.path.isfile(file_path):
            all_rules.extend(parse_rule_file(file_path))

    return all_rules
