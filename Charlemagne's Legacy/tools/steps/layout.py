#!/usr/bin/env python3
"""Where things live: the base game's and the mod's folders, and the tag capitals."""

from pathlib import Path
from paths import EU4_GAME
from tagdb import BY_TAG, CTRY_DATE


HERE = Path(__file__).resolve().parent.parent  # tools/

CACHE = HERE / "cache"

PROVDATA = CACHE / "provdata.json"

GAME = EU4_GAME

MOD = HERE.parent

VANILLA_HISTORY = Path(GAME) / "history"


VDIR = VANILLA_PDIR = Path(GAME) / "history" / "provinces"

VANILLA_CDIR = Path(GAME) / "history" / "countries"

PDIR = PROV_OUT = MOD / "history" / "provinces"

COUNTRY_OUT = MOD / "history" / "countries"


CAPITAL = {t.tag: t.capital for t in BY_TAG.values() if t.capital}


START_DT = tuple(int(x) for x in CTRY_DATE.split("."))


T = "\t"
