#!/usr/bin/env python3
"""Verify the generated mod: run every check module in order and end with ALL CHECKS PASSED or the failure count.

Each module under `checks/` owns one area (realms, provinces, tags, rulers, decisions, diplomacy, scripts,
localisation, interface, religion, cultures, filenames) and prints its own sections; `checks/report.py` collects
the failures and `checks/context.py` holds what they share.

    python3 tools/validate.py
"""
import sys

from checks import (
    cultures,
    decisions,
    diplomacy,
    filenames,
    interface,
    localisation,
    provinces,
    realms,
    religion,
    report,
    rulers,
    scripts,
    tags,
)

CHECKS = [
    realms,
    provinces,
    tags,
    rulers,
    decisions,
    diplomacy,
    scripts,
    localisation,
    interface,
    religion,
    cultures,
    filenames,
]


def run() -> int:
    report.reset()
    for module in CHECKS:
        module.run()
    return report.summary()


if __name__ == "__main__":
    sys.exit(run())
