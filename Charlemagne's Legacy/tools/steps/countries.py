#!/usr/bin/env python3
"""Country definitions and history files for the mod's tags."""

import os
from ck3 import ck3_sync
from histgen import country_history
from tagdb import TAGS
from steps.layout import COUNTRY_OUT, VANILLA_CDIR
from steps.output import write_out
from steps.parsing import strip_non_867
from steps.vanilla_countries import _VANILLA_CTRY_FILES


def hist_name(t) -> str:
    # Name our file exactly like vanilla's when one exists for this tag, so
    # the engine skips the vanilla file instead of merging its OTL history
    # (rulers, idea groups, HRE/elector state, dated rank changes) into ours.
    if not _VANILLA_CTRY_FILES:
        for fn in os.listdir(VANILLA_CDIR):
            if fn.endswith(".txt"):
                _VANILLA_CTRY_FILES.setdefault(fn.split(" - ")[0], fn)
    hit = _VANILLA_CTRY_FILES.get(t.tag)
    if hit:
        return hit
    base = t.country_file or t.tag
    if base.endswith(".txt"):
        base = base[:-4]
    return f"{t.tag} - {base}.txt"


def step_countries():
    os.makedirs(COUNTRY_OUT, exist_ok=True)
    for t in TAGS:
        text = ck3_sync(t.tag, country_history(t))
        text = strip_non_867(text)
        name = hist_name(t)
        write_out(os.path.join(COUNTRY_OUT, name), text)
        stale = os.path.join(COUNTRY_OUT, f"{t.tag}.txt")
        if stale != os.path.join(COUNTRY_OUT, name) and os.path.exists(stale):
            os.remove(stale)
        print(f"wrote {name} (rank {t.rank}, capital {t.capital})")
    # HLR is formed in-game by kar_form_hre; neutralize vanilla's OTL file
    # (rank 3, Vienna capital, austrian/catholic defaults) so it never applies.
    # A comment alone does not register as a history file, so carry the same
    # neutral defaults the formation produces anyway (history is not
    # re-applied on change_tag).
    write_out(
        os.path.join(COUNTRY_OUT, "HLR - Holy Roman Empire.txt"),
        "# formed in-game by kar_form_hre; vanilla OTL history neutralized\n"
        "government = monarchy\n"
        "technology_group = western\n",
    )
    print("wrote HLR - Holy Roman Empire.txt (neutralized)")
