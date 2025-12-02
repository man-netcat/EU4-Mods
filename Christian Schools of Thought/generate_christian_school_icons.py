#!/usr/bin/env python3
"""Generate resized, recolored Christian school icons from vanilla religion icons."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from dataclasses import dataclass
import re
from pathlib import Path
from typing import Iterable, Mapping, Optional


@dataclass(frozen=True)
class SchoolStyle:
    source: str
    brightness: int
    tint_amount: int
    saturation: int
    country_tag: str
    hue_shift: Optional[int] = None


SCHOOL_STYLES: Mapping[str, SchoolStyle] = {
    # Catholic-origin traditions
    "thomist_school": SchoolStyle(
        "catholic.dds", brightness=103, tint_amount=22, saturation=65, country_tag="PAP"
    ),  # Dominican Thomism rooted in Rome
    "scotist_school": SchoolStyle(
        "catholic.dds", brightness=103, tint_amount=26, saturation=65, country_tag="SCO"
    ),  # John Duns Scotus from the Scottish realm
    "nominalist_school": SchoolStyle(
        "catholic.dds", brightness=103, tint_amount=24, saturation=65, country_tag="ENG"
    ),  # William of Ockham's England
    "augustinian_school": SchoolStyle(
        "catholic.dds", brightness=102, tint_amount=22, saturation=65, country_tag="AUG"
    ),  # Augustinian reforms centered on the German city of Augsburg
    "molinist_school": SchoolStyle(
        "catholic.dds", brightness=103, tint_amount=22, saturation=65, country_tag="CAS"
    ),  # Jesuit debates in Castile/Spain
    "jansenist_school": SchoolStyle(
        "catholic.dds", brightness=103, tint_amount=24, saturation=65, country_tag="NED"
    ),  # Jansenism from the Low Countries
    # Protestant offshoots
    "wittenberg_school": SchoolStyle(
        "protestant.dds",
        brightness=103,
        tint_amount=23,
        saturation=55,
        country_tag="SAX",
    ),
    "magdeburg_school": SchoolStyle(
        "protestant.dds",
        brightness=103,
        tint_amount=25,
        saturation=55,
        country_tag="MAG",
    ),
    "philippist_school": SchoolStyle(
        "protestant.dds",
        brightness=103,
        tint_amount=23,
        saturation=55,
        country_tag="PAL",
    ),
    "gnesiolutheran_school": SchoolStyle(
        "protestant.dds",
        brightness=103,
        tint_amount=24,
        saturation=55,
        country_tag="WUR",
    ),
    # Reformed currents
    "genevan_school": SchoolStyle(
        "reformed.dds", brightness=103, tint_amount=21, saturation=60, country_tag="SWI"
    ),
    "covenanter_school": SchoolStyle(
        "reformed.dds", brightness=103, tint_amount=24, saturation=60, country_tag="HSC"
    ),
    "remonstrant_school": SchoolStyle(
        "reformed.dds", brightness=103, tint_amount=23, saturation=60, country_tag="HOL"
    ),
    "collegiant_school": SchoolStyle(
        "reformed.dds", brightness=103, tint_amount=25, saturation=60, country_tag="UTR"
    ),
    # Orthodox theological streams
    "palamite_school": SchoolStyle(
        "orthodox.dds", brightness=103, tint_amount=26, saturation=60, country_tag="BYZ"
    ),
    "hesychast_school": SchoolStyle(
        "orthodox.dds", brightness=103, tint_amount=27, saturation=58, country_tag="ATH"
    ),
    "kyivan_school": SchoolStyle(
        "orthodox.dds", brightness=103, tint_amount=24, saturation=60, country_tag="KIE"
    ),
    "stoglav_school": SchoolStyle(
        "orthodox.dds", brightness=103, tint_amount=23, saturation=60, country_tag="MOS"
    ),
    # Coptic and Ethiopian traditions
    "alexandrian_school": SchoolStyle(
        "coptic.dds", brightness=104, tint_amount=28, saturation=70, country_tag="MAM"
    ),
    "debre_libanos_school": SchoolStyle(
        "coptic.dds", brightness=104, tint_amount=26, saturation=70, country_tag="ETH"
    ),
    "lalibela_school": SchoolStyle(
        "coptic.dds",
        brightness=104,
        tint_amount=28,
        saturation=70,
        country_tag="DAM",
    ),  # Zagwe/Lasta pilgrimage center distinct from Debre Libanos
    "nubian_school": SchoolStyle(
        "coptic.dds", brightness=104, tint_amount=27, saturation=70, country_tag="MAK"
    ),
}


def load_country_colors(game_dir: Path) -> Mapping[str, tuple[int, int, int]]:
    tag_to_country_file = load_country_definition_paths(game_dir)
    if not tag_to_country_file:
        raise SystemExit(
            "Could not locate any country tag definitions under common/country_tags."
        )

    country_colors: dict[str, tuple[int, int, int]] = {}
    for tag, rel_path in tag_to_country_file.items():
        country_file = game_dir / rel_path
        if not country_file.is_file():
            continue
        color = extract_country_file_color(country_file)
        if color:
            country_colors[tag] = color

    return country_colors


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


COUNTRY_TAG_LINE_RE = re.compile(r"^\s*([A-Z0-9_]+)\s*=\s*\"(.+?)\"")
COUNTRY_DEF_COLOR_RE = re.compile(r"color\s*=\s*\{\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)")


def load_country_definition_paths(game_dir: Path) -> Mapping[str, Path]:
    tags_dir = game_dir / "common/country_tags"
    if not tags_dir.is_dir():
        return {}

    tag_map: dict[str, Path] = {}
    for tag_file in sorted(tags_dir.glob("*.txt")):
        with tag_file.open(encoding="utf-8-sig", errors="ignore") as handle:
            for line in handle:
                match = COUNTRY_TAG_LINE_RE.match(line)
                if match:
                    tag, rel_path = match.groups()
                    tag_map[tag] = Path("common") / Path(rel_path.strip())
    return tag_map


def extract_country_file_color(country_file: Path) -> Optional[tuple[int, int, int]]:
    with country_file.open(encoding="utf-8-sig", errors="ignore") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = COUNTRY_DEF_COLOR_RE.search(line)
            if match:
                return tuple(int(match.group(idx)) for idx in range(1, 4))
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--game-dir",
        required=True,
        type=Path,
        help="Path to the base Europa Universalis IV installation (expects gfx/interface/religion_icons).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent
        / "gfx/interface/christian_school_icons",
        help="Directory to write the generated DDS files (default: mod's gfx/interface/christian_school_icons)",
    )
    parser.add_argument(
        "--executable",
        default=shutil.which("magick") or "magick",
        help="ImageMagick executable to run (default: first 'magick' on PATH)",
    )
    return parser.parse_args()


def ensure_imagemagick(executable: str) -> None:
    if shutil.which(executable) is None:
        raise SystemExit(
            f"ImageMagick executable '{executable}' not found. Set --executable or install ImageMagick to continue."
        )


def build_command(
    executable: str, src: Path, dest: Path, style: SchoolStyle, tint_color: str
) -> Iterable[str]:
    cmd = [
        executable,
        str(src),
        "-filter",
        "Lanczos",
        "-resize",
        "52x52",
        "-modulate",
        f"{style.brightness},{style.saturation},{style.hue_shift or 100}",
        "-colorspace",
        "sRGB",
        "(",
        "+clone",
        "-fill",
        tint_color,
        "-colorize",
        "100",
        ")",
        "-compose",
        "colorize",
        "-define",
        f"compose:args={style.tint_amount}",
        "-composite",
        str(dest),
    ]
    return cmd


def generate_icons(game_dir: Path, output_dir: Path, executable: str) -> None:
    icons_dir = game_dir / "gfx/interface/religion_icons"
    if not icons_dir.is_dir():
        raise SystemExit(f"Could not find religion icons directory at {icons_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    country_colors = load_country_colors(game_dir)

    for school, style in SCHOOL_STYLES.items():
        src = icons_dir / style.source
        if not src.is_file():
            raise SystemExit(f"Missing source icon for {school}: {src}")
        dest = output_dir / f"icon_{school}.dds"
        if style.country_tag not in country_colors:
            raise SystemExit(
                f"No color1 entry found for country tag '{style.country_tag}'"
            )
        tint_color = rgb_to_hex(country_colors[style.country_tag])
        cmd = build_command(executable, src, dest, style, tint_color)
        subprocess.run(cmd, check=True)
        print(
            f"Generated {dest.relative_to(output_dir.parent.parent.parent)} using {src.name}"
        )


def main() -> None:
    args = parse_args()
    ensure_imagemagick(args.executable)
    generate_icons(args.game_dir, args.output_dir, args.executable)


if __name__ == "__main__":
    main()
