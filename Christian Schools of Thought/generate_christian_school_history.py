#!/usr/bin/env python3
"""Regenerate Christian school history overrides from hardcoded culture rules.

Usage:
    python3 generate_christian_school_history.py --game-dir /path/to/EU4/root [--output-dir history/countries]

The script scans the base game's history/countries directory, determines each
country's starting religion and primary culture, and writes partial override
files inside the mod so every relevant Christian tag gets an explicit
`religious_school` assignment. The mapping logic mirrors the conditions in
`events/ChristianSchoolEvents.txt`, so updating those conditions only requires
editing the helper functions below.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# Hard-coded culture-group membership for every group referenced in the events and
# in the automatic school assignment timeline below.
CULTURE_GROUPS: Dict[str, Tuple[str, ...]] = {
    "french": (
        "cosmopolitan_french",
        "gascon",
        "normand",
        "aquitaine",
        "burgundian",
        "occitain",
        "wallonian",
        "louisianans",
        "quebecois",
        "anglois",
        "breton",
    ),
    "iberian": (
        "castillian",
        "mexican",
        "platinean",
        "leonese",
        "aragonese",
        "catalan",
        "galician",
        "andalucian",
        "portugese",
        "brazilian",
        "basque",
    ),
    "british": (
        "english",
        "american",
        "welsh",
        "cornish",
        "scottish",
    ),
    "gaelic": (
        "irish",
        "highland_scottish",
    ),
    "latin": (
        "lombard",
        "tuscan",
        "sardinian",
        "romagnan",
        "ligurian",
        "venetian",
        "dalmatian",
        "neapolitan",
        "piedmontese",
        "umbrian",
        "sicilian",
        "maltese",
    ),
    "germanic": (
        "pommeranian",
        "prussian",
        "baltic_german",
        "lower_saxon",
        "hannoverian",
        "hessian",
        "saxon",
        "franconian",
        "swabian",
        "swiss",
        "bavarian",
        "austrian",
        "dutch",
        "flemish",
        "frisian",
        "gothic_ger",
    ),
    "scandinavian": (
        "swedish",
        "danish",
        "norwegian",
        "finnish",
        "sapmi",
        "karelian",
        "icelandic",
        "norse",
    ),
    "byzantine": (
        "greek",
        "pontic_greek",
        "cappadocian_greek",
        "goths",
        "griko",
        "georgian_new",
    ),
    "caucasian": (
        "georgian",
        "circassian",
        "dagestani",
        "armenian",
    ),
    "east_slavic": (
        "russian",
        "novgorodian",
        "ryazanian",
        "byelorussian",
        "ruthenian",
    ),
    "turko_semitic": (
        "turkish",
        "al_misr_arabic",
        "al_suryah_arabic",
        "al_iraqiya_arabic",
        "gulf_arabic",
        "bedouin_arabic",
        "mahri_culture",
        "hejazi_culture",
        "omani_culture",
        "yemeni_culture",
    ),
}

# Reverse index for quick lookups.
CULTURE_TO_GROUP: Dict[str, str] = {
    culture: group for group, cultures in CULTURE_GROUPS.items() for culture in cultures
}


@dataclass
class CountryInfo:
    tag: str
    file_path: Path
    country_name: str
    religion: str
    primary_culture: str
    religion_events: List[Tuple[str, str]]


RELIGIONS = {
    "catholic",
    "protestant",
    "reformed",
    "orthodox",
    "coptic",
}


RELIGIOUS_SCHOOL_CHOOSERS = {}


def choose_catholic_school(culture: str, culture_group: Optional[str]) -> str:
    if culture_group in {"french", "iberian"}:
        return "thomist_school"
    if culture == "scottish" or culture_group == "gaelic":
        return "scotist_school"
    if culture_group == "british" and culture != "scottish":
        return "nominalist_school"
    if culture_group == "latin":
        return "augustinian_school"
    return "thomist_school"


def determine_catholic_school_flips(
    culture: str, culture_group: Optional[str], initial_school: str
) -> list[tuple[str, str]]:
    """Return time-ordered Catholic school shifts for cultures that historically pivot."""

    flips: list[tuple[str, str]] = []

    if culture_group == "iberian" and initial_school != "molinist_school":
        flips.append(("1600.1.1", "molinist_school"))

    if culture_group == "french" and initial_school != "jansenist_school":
        flips.append(("1640.1.1", "jansenist_school"))

    return flips


def choose_protestant_school(culture: str, culture_group: Optional[str]) -> str:
    if culture == "saxon":
        return "gnesiolutheran_school"
    if culture_group == "scandinavian":
        return "magdeburg_school"
    if culture_group == "british" and culture != "scottish":
        return "philippist_school"
    return "wittenberg_school"


def choose_reformed_school(culture: str, culture_group: Optional[str]) -> str:
    if culture == "swiss" or culture_group == "french":
        return "genevan_school"
    if culture == "scottish" or culture_group == "gaelic":
        return "covenanter_school"
    if culture in {"dutch", "flemish"}:
        return "collegiant_school"
    return "remonstrant_school"


def choose_orthodox_school(culture: str, culture_group: Optional[str]) -> str:
    if culture == "greek" or culture_group == "byzantine":
        return "palamite_school"
    if culture_group == "caucasian":
        return "hesychast_school"
    if culture == "russian":
        return "stoglav_school"
    return "kyivan_school"


def choose_coptic_school(culture: str, culture_group: Optional[str]) -> str:
    if culture == "armenian" or culture_group == "turko_semitic":
        return "alexandrian_school"
    if culture in {"amhara", "sidamo"}:
        return "debre_libanos_school"
    if culture == "tigray":
        return "lalibela_school"
    if culture == "nubian":
        return "nubian_school"
    return "alexandrian_school"


RELIGIOUS_SCHOOL_CHOOSERS = {
    "catholic": choose_catholic_school,
    "protestant": choose_protestant_school,
    "reformed": choose_reformed_school,
    "orthodox": choose_orthodox_school,
    "coptic": choose_coptic_school,
}


RELIGION_RE = re.compile(r"\breligion\s*=\s*(\w+)")
CULTURE_RE = re.compile(r"\bprimary_culture\s*=\s*(\w+)")
DATE_LINE_RE = re.compile(r"^\s*(\d{3,4}\.\d+\.\d+)\s*=\s*\{")


def parse_date_key(date_str: str) -> Tuple[int, int, int]:
    year, month, day = date_str.split(".")
    return (int(year), int(month), int(day))


def normalize_conversion_events(
    events: Iterable[Tuple[str, str]], starting_religion: str
) -> List[Tuple[str, str]]:
    """Filter to meaningful religion changes in chronological order."""

    filtered: List[Tuple[str, str]] = []
    current = starting_religion
    for date, religion in sorted(events, key=lambda item: parse_date_key(item[0])):
        if religion not in RELIGIONS:
            continue
        if religion == current:
            continue
        filtered.append((date, religion))
        current = religion
    return filtered


def parse_country_file(path: Path) -> Optional[CountryInfo]:
    """Extract country metadata and religion timeline from a base-game history file."""

    text = path.read_text(encoding="latin-1")
    lines = text.splitlines()

    primary_culture: Optional[str] = None
    base_religion: Optional[str] = None
    conversions: List[Tuple[str, str]] = []

    current_date: Optional[str] = None
    brace_depth = 0

    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if current_date is None:
            if primary_culture is None:
                culture_match = CULTURE_RE.search(line)
                if culture_match:
                    primary_culture = culture_match.group(1)
            if base_religion is None:
                religion_match = RELIGION_RE.search(line)
                if religion_match:
                    candidate = religion_match.group(1)
                    if candidate in RELIGIONS:
                        base_religion = candidate

            date_match = DATE_LINE_RE.match(line)
            if date_match:
                current_date = date_match.group(1)
                brace_depth = raw_line.count("{") - raw_line.count("}")
                religion_match = RELIGION_RE.search(line[date_match.end() :])
                if religion_match:
                    conversions.append((current_date, religion_match.group(1)))
                if brace_depth <= 0:
                    current_date = None
                    brace_depth = 0
            continue

        # Inside a dated block
        religion_match = RELIGION_RE.search(line)
        if religion_match:
            conversions.append((current_date, religion_match.group(1)))

        brace_depth += raw_line.count("{") - raw_line.count("}")
        if brace_depth <= 0:
            current_date = None
            brace_depth = 0

    if not base_religion or not primary_culture:
        return None
    if base_religion not in RELIGIONS:
        return None

    conversions = normalize_conversion_events(conversions, base_religion)

    tag = path.name.split(" ", 1)[0].split(".")[0]
    country_name = path.stem
    return CountryInfo(
        tag=tag,
        file_path=path,
        country_name=country_name,
        religion=base_religion,
        primary_culture=primary_culture,
        religion_events=conversions,
    )


def derive_output_name(info: CountryInfo) -> str:
    base = info.country_name
    if " - " in base:
        _, remainder = base.split(" - ", 1)
    else:
        remainder = base[4:]
    return f"{info.tag} - {remainder}ChristianSchools.txt"


def gather_countries(history_dir: Path) -> Iterable[CountryInfo]:
    for file_path in sorted(history_dir.glob("*.txt")):
        info = parse_country_file(file_path)
        if info:
            yield info


def determine_school(info: CountryInfo) -> tuple[str, list[tuple[str, str]]]:
    chooser = RELIGIOUS_SCHOOL_CHOOSERS[info.religion]
    culture_group = CULTURE_TO_GROUP.get(info.primary_culture)
    initial_school = chooser(info.primary_culture, culture_group)
    flips = build_school_timeline(info, culture_group, initial_school)
    return initial_school, flips


def build_school_timeline(
    info: CountryInfo,
    culture_group: Optional[str],
    initial_school: str,
) -> list[tuple[str, str]]:
    timeline: list[tuple[str, str]] = []
    events: list[tuple[str, str, str]] = []

    if info.religion == "catholic":
        for date, school in determine_catholic_school_flips(
            info.primary_culture, culture_group, initial_school
        ):
            events.append((date, "school", school))

    for date, religion in info.religion_events:
        events.append((date, "conversion", religion))

    if not events:
        return timeline

    current_school = initial_school
    current_religion = info.religion

    for date, kind, payload in sorted(events, key=lambda item: parse_date_key(item[0])):
        if kind == "school":
            new_school = payload
            if current_religion != "catholic":
                continue
            if new_school != current_school:
                timeline.append((date, new_school))
                current_school = new_school
            continue

        # Religion conversion
        new_religion = payload
        current_religion = new_religion
        chooser = RELIGIOUS_SCHOOL_CHOOSERS.get(new_religion)
        if chooser is None:
            continue
        new_school = chooser(info.primary_culture, culture_group)
        if new_school != current_school:
            timeline.append((date, new_school))
            current_school = new_school

    return timeline


def clean_output_dir(output_dir: Path) -> None:
    for leftover in output_dir.glob("*ChristianSchools.txt"):
        leftover.unlink()


def write_override(
    output_dir: Path, info: CountryInfo, school: str, flips: Iterable[tuple[str, str]]
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = derive_output_name(info)
    lines = [
        "# Christian Schools of Thought partial override\n",
        f"religious_school = {school}\n",
    ]

    for date, new_school in sorted(flips, key=lambda item: item[0]):
        lines.append(
            "\n{} = {{\n\treligious_school = {}\n}}\n".format(date, new_school)
        )

    (output_dir / filename).write_text("".join(lines), encoding="latin-1")


def run(game_dir: Path, output_dir: Path) -> None:
    history_dir = game_dir / "history" / "countries"
    if not history_dir.is_dir():
        raise SystemExit(f"History directory not found: {history_dir}")

    clean_output_dir(output_dir)

    total = 0
    per_religion: Dict[str, int] = {religion: 0 for religion in RELIGIONS}

    for info in gather_countries(history_dir):
        school, flips = determine_school(info)
        write_override(output_dir, info, school, flips)
        per_religion[info.religion] += 1
        total += 1

    print(f"Wrote {total} Christian school overrides to {output_dir}")
    for religion in sorted(per_religion):
        print(f"  {religion.title():<11}: {per_religion[religion]}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-dir",
        required=True,
        type=Path,
        help="Path to the Europa Universalis IV game directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent / "history" / "countries",
        help="Directory inside the mod where override files should be written",
    )
    args = parser.parse_args()

    run(args.game_dir.resolve(), args.output_dir.resolve())


if __name__ == "__main__":
    main()
