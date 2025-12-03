#!/usr/bin/env python3
"""Report dated Christian school changes per country history file."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterator, List, Tuple

SCHOOL_LINE = re.compile(r"^religious_school\s*=\s*([A-Za-z0-9_]+)")
DATE_HEADER = re.compile(r"^(\d{1,4}\.\d{1,2}\.\d{1,2})\s*=\s*\{")

@dataclass
class Assignment:
    date: str | None  # None for initial
    school: str


def infer_tag(path: Path) -> str:
    base = path.stem
    candidate = base.split(" ", 1)[0]
    if len(candidate) == 3 and candidate.isalpha():
        return candidate.upper()
    return base[:3].upper()


def slug_to_title(slug: str) -> str:
    return slug.replace("_", " ").title()


def iter_lines(path: Path) -> Iterator[str]:
    try:
        with path.open("r", encoding="utf-8-sig") as fh:
            yield from fh
    except UnicodeDecodeError:
        with path.open("r", encoding="windows-1252", errors="ignore") as fh:
            yield from fh


def parse_assignments(path: Path) -> List[Assignment]:
    assignments: List[Assignment] = []
    current_date: str | None = None
    brace_depth = 0
    inside_block = False

    for raw_line in iter_lines(path):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        date_match = DATE_HEADER.match(line)
        if date_match:
            current_date = date_match.group(1)
            inside_block = True
            brace_depth = line.count("{") - line.count("}")
            # Continue to next line so we don't parse school on header line
            continue

        if inside_block:
            brace_depth += line.count("{") - line.count("}")
            school_match = SCHOOL_LINE.match(line)
            if school_match and current_date:
                assignments.append(Assignment(current_date, school_match.group(1)))
            if brace_depth <= 0:
                inside_block = False
                current_date = None
            continue

        # top-level
        school_match = SCHOOL_LINE.match(line)
        if school_match:
            assignments.append(Assignment(None, school_match.group(1)))

    return assignments


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "List dated religious_school changes for every country history file."
        )
    )
    parser.add_argument(
        "history_dir",
        nargs="?",
        default="history/countries",
        help="Path to history/countries directory (default: %(default)s)",
    )
    parser.add_argument(
        "--only-flips",
        action="store_true",
        help="Hide countries that never change schools (no dated entries).",
    )
    args = parser.parse_args()

    history_path = Path(args.history_dir).expanduser().resolve()
    if not history_path.exists():
        raise SystemExit(f"History directory not found: {history_path}")

    files = sorted(history_path.glob("*.txt"))
    if not files:
        raise SystemExit("No history files found.")

    total_flips = 0
    for file_path in files:
        assignments = parse_assignments(file_path)
        dated = [a for a in assignments if a.date is not None]
        if args.only_flips and not dated:
            continue
        if not assignments:
            continue

        tag = infer_tag(file_path)
        print(f"{tag} ({file_path.name})")
        initial = next((a for a in assignments if a.date is None), None)
        if initial:
            print(f"  START -> {slug_to_title(initial.school)}")
        for entry in dated:
            print(f"  {entry.date} -> {slug_to_title(entry.school)}")
        print()
        total_flips += len(dated)

    print(f"Total dated flips recorded: {total_flips}")


if __name__ == "__main__":
    main()
