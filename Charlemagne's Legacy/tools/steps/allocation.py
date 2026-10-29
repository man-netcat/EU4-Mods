#!/usr/bin/env python3
"""Which tag owns which province: the database's tags and areas turned into one owner per province."""

import re
from tagdb import AREA_OWNERS, PROVINCES, PROVINCE_OWNERS, TAGS
from steps.provdata import _pd


def apply_db_culture_religion(text, pid):
    """Write the province's 867 culture and religion from the database,
    leaving a line alone when the file already agrees (quoting included)."""
    p = PROVINCES[pid]
    for key, want in (("culture", p.culture), ("religion", p.religion)):
        if not want:
            continue
        m = re.search(rf'^(\s*){key}\s*=\s*"?(\w+)"?', text, re.M)
        if m and m.group(2) != want:
            text = text[: m.start()] + f"{m.group(1)}{key} = {want}" + text[m.end() :]
    return text


def build() -> dict:
    data = _pd()
    provs, AREAS = data["provs"], data["areas"]

    alloc: dict = {}
    owner_of: dict = {}
    overlaps = []

    for tag, areas in AREA_OWNERS.items():
        ids = []
        for area in areas:
            for pid in AREAS.get(area, ()):
                pr = provs.get(str(pid))
                if not (pr and pr.get("owner")):
                    continue
                ids.append(pid)
                if pid in owner_of:
                    overlaps.append((pid, owner_of[pid], tag))
                else:
                    owner_of[pid] = tag
        alloc[tag] = sorted(set(ids))
    if overlaps:
        raise SystemExit(
            "build.py: provinces claimed by two areas, fix AREA_OWNERS: "
            + ", ".join(f"{p} ({a} and {b})" for p, a, b in overlaps)
        )

    for pid, tag in PROVINCE_OWNERS.items():
        prev = owner_of.get(pid)
        owner_of[pid] = tag
        if prev in alloc:
            alloc[prev] = [p for p in alloc[prev] if p != pid]
        alloc.setdefault(tag, [])
        if pid not in alloc[tag]:
            alloc[tag] = sorted(alloc[tag] + [pid])

    for tag in alloc:
        alloc[tag] = sorted(set(alloc[tag]))

    return {s.tag: sorted(alloc[s.tag]) for s in TAGS if alloc.get(s.tag)}


#: EU4 areas of Iberia: Andalusi-held land here carries the Reconquista.
IBERIA_AREAS = frozenset(
    "alentejo_area aragon_area asturias_area baleares_area basque_country "
    "beieras_area castille_area catalonia_area extremadura_area galicia_area "
    "leon_area lower_andalucia_area toledo_area upper_andalucia_area "
    "valencia_area".split()
)


#: HUN requirement land: whoever holds it carries Magyar migration claims
#: (CK3 hungarian_migration_cb, translated as claims + the existing HUN
#: path — no timer, no custom CB).
HUN_AREAS = frozenset(
    "alfold_area southern_transylvania_area transdanubia_area "
    "transylvania_area".split()
)


#: Who carries conquest claims, and on whose land: exact (owner, areas)
#: matches. Whoever holds the Hungarian basin answers MGY instead (CK3's
#: migration CB as claims); MGY itself never claims its own cradle.
CLAIM_RULES = (
    # Andalusi Iberia feeds the Reconquista (ASU/NAV claims).
    ("ADU", IBERIA_AREAS, ("ASU", "NAV")),
    # Vimara's 868 targets (CK3 war_867_Vimara_conquest_Portucale).
    ("PRT", frozenset({"beieras_area"}), ("ASU",)),
)
