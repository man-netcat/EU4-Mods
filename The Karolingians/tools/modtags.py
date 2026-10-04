#!/usr/bin/env python3
"""Which tags this mod gives land to.

One list. Every tag in it is assigned land the same way, by the same three
statements in gen_provinces.py (AREA_OWNERS, PROVINCE_OWNERS, TRANSFERS). There
is no tier of tag in the allocation and none here: a tag is either in this list
or it is not a tag this mod touches.

Why the list exists at all
--------------------------
It used to be spelled out separately in gen_provinces.py, check_start.py,
validate.py and gen_countries.py. Four copies of the same fact is three ways to
be wrong, and the copies had already drifted: gen_countries.py still treated
Lusatia as a partition kingdom while the mod's own localisation had always
described a five-kingdom empire with Lusatia outside it.

What is deliberately NOT here
-----------------------------
Any split between "realms" and "gifts". Whether the mod also writes a country
file for a tag is not a second opinion about the map - it is answered by
gen_countries.RULERS, which is the mod's own per-tag data and the only place a
ruler is defined. A tag missing from that dict keeps vanilla's file and vanilla's
1444 ruler, and nothing else has to agree about it.

EMPIRE_KINGDOMS is the five realms the "Restore the Holy Roman Empire" decision
counts. It belongs to that decision's text and to the balance report, and is not
used to decide who owns a province: Lusatia is a realm here on exactly the same
terms as Bavaria, and simply is not one of the five the empire can be restored
from.
"""
from __future__ import annotations

# Every tag the allocation may hand a province to.
ALL_TAGS = [
    # Realms this mod writes a country file for.
    "FRA", "LOT", "GER", "BAV", "ITA", "SOR",
    # Tags handed land whose own country file the mod leaves alone.
    "NAV", "SIL", "GMA", "BYZ", "BUL", "CRT", "HUN", "CRI", "MON",
    "DAL", "ARB", "EGY", "ADU", "ASU",
]

# The five kingdoms the empire decision counts. Lusatia is not one of them.
EMPIRE_KINGDOMS = ["FRA", "LOT", "GER", "BAV", "ITA"]
