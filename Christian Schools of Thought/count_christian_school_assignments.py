#!/usr/bin/env python3
"""Summarise Christian school assignments from history country files."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import re
from typing import Dict, List

SCHOOL_LINE = re.compile(r"^religious_school\s*=\s*([A-Za-z0-9_]+)")


def infer_tag(path: Path) -> str:
    """Derive the three-letter country tag from the filename."""
    base = path.stem  # e.g. "AAC - AachenChristianSchools"
    candidate = base.split(" ", 1)[0]
    if len(candidate) == 3 and candidate.isalpha():
        return candidate.upper()
    return base[:3].upper()


def slug_to_title(slug: str) -> str:
    """Convert thomist_school -> Thomist School."""
    return slug.replace("_", " ").title()


def extract_school(path: Path) -> str | None:
    """Return the religious school set within the file, if present."""
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            for raw_line in fh:
                line = raw_line.split("#", 1)[0].strip()
                if not line:
                    continue
                match = SCHOOL_LINE.match(line)
                if match:
                    return match.group(1)
    except UnicodeDecodeError:
        with path.open("r", encoding="windows-1252", errors="ignore") as fh:
            for raw_line in fh:
                line = raw_line.split("#", 1)[0].strip()
                if not line:
                    continue
                match = SCHOOL_LINE.match(line)
                if match:
                    return match.group(1)
    return None


def scan_history(history_dir: Path) -> Dict[str, List[str]]:
    """Walk the history directory and map school slug -> country tags."""
    results: Dict[str, List[str]] = defaultdict(list)
    for file_path in sorted(history_dir.glob("*.txt")):
        school = extract_school(file_path)
        if not school:
            continue
        tag = infer_tag(file_path)
        results[school].append(tag)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Count how many countries start with each Christian school "
            "in the provided history/countries directory."
        )
    )
    parser.add_argument(
        "history_dir",
        nargs="?",
        default="history/countries",
        help="Path to the history/countries directory (default: %(default)s)",
    )
    args = parser.parse_args()

    history_path = Path(args.history_dir).expanduser().resolve()
    if not history_path.exists():
        raise SystemExit(f"History directory not found: {history_path}")

    school_map = scan_history(history_path)
    if not school_map:
        raise SystemExit("No religious_school entries found.")

    print(f"Scanned {history_path}")
    print()

    grand_total = 0
    for school_slug in sorted(school_map.keys()):
        tags = sorted(school_map[school_slug])
        grand_total += len(tags)
        print(f"{slug_to_title(school_slug)} ({len(tags)}):")
        print("  " + ", ".join(tags))
        print()

    print(f"Total tagged countries: {grand_total}")


if __name__ == "__main__":
    main()
