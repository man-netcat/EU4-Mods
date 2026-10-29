#!/usr/bin/env python3
"""What the checks share: where the base game and the mod live, and the mod's tags, read once."""

import os
import re
from pathlib import Path

from db import core_deny_map
from enc import encname
from paths import EU4_GAME
from steps.empire import empire_core, karling_realms
from steps.layout import CAPITAL
from steps.parsing import effective, parse
from tagdb import (
    BY_FORMABLE,
    BY_TAG,
    CTRY_DATE,
    DORMANT,
    FORMABLE_TAGS,
    KEPT_REALMS,
    PROVINCES,
    RANK,
    required_count,
)
from tagdb import TAGS as _REALMS

__all__ = [
    "BY_FORMABLE",
    "BY_TAG",
    "CACHE",
    "CAPS",
    "CONQUERED_BY_THE_ARABS",
    "COUNTRY_OUT",
    "CTRY_DATE",
    "DORMANT",
    "FORMABLE_TAGS",
    "GAME",
    "GH",
    "HERE",
    "KEPT_REALMS",
    "MOD",
    "MUSLIM_RELIGIONS_867",
    "PDIR",
    "PROVINCES",
    "RANK",
    "TAGS",
    "_REALMS",
    "core_deny_map",
    "country_path",
    "effective",
    "empire_core",
    "encname",
    "karling_realms",
    "parse",
    "province_files",
    "required_count",
]

HERE = Path(__file__).resolve().parent.parent  # tools/
CACHE = HERE / "cache"

GAME = EU4_GAME
MOD = str(HERE.parent)
PDIR = os.path.join(MOD, "history", "provinces")
COUNTRY_OUT = os.path.join(MOD, "history", "countries")
GH = os.path.join(GAME, "history", "countries")  # the base game's country histories

TAGS = sorted(t.tag for t in _REALMS if t.ck3_title)
CAPS = CAPITAL

# this mod's 867 culture/religion expectations, checked against the files the build writes
CONQUERED_BY_THE_ARABS = {327, 332, 2303, 4298, 4310, 124, 125, 4736, 4737}
MUSLIM_RELIGIONS_867 = ("sunni", "shia", "kharijite")


def country_path(t: str) -> str:
    """The mod's history file for a tag (`TAG - Name.txt`)."""
    for fn in os.listdir(COUNTRY_OUT):
        if fn.startswith(f"{t} - ") and fn.endswith(".txt"):
            return os.path.join(COUNTRY_OUT, fn)
    return os.path.join(COUNTRY_OUT, f"{t}.txt")


def province_files() -> dict:
    """{province id: path} of the mod's province history files."""
    out = {}
    for fn in sorted(os.listdir(PDIR)):
        out[int(re.match(r"^(\d+)", fn).group(1))] = os.path.join(PDIR, fn)
    return out
