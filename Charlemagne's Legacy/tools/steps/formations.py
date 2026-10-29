#!/usr/bin/env python3
"""The province triggers that back every formation decision."""

import os
from histgen import formation_capital_trigger_block, formation_trigger_block, requirement_provinces
from tagdb import BY_FORMABLE, TAGS
from steps.empire import empire_core
from steps.layout import MOD
from steps.output import write_out
from steps.provdata import _pd


#: Decisions with no formables row that still need province triggers:
#: decision key -> requirement areas. Finland crowns in place through its
#: custom kingdom file (like Denmark/Norway/Sweden it wants the capital
#: in the homeland), so its land lives here instead of the database.
CUSTOM_TRIGGERS = {
    "kar_form_finland": ("finland_area", "bothnia_area"),
    "kar_form_ue": ("tsang_area",),
}


def step_formation_triggers() -> None:
    specs = [("kar_form_hre", empire_core(), False)]
    done = set()
    for t in TAGS:
        if t.forms and t.forms not in done:
            done.add(t.forms)
            req = requirement_provinces(t.forms)
            specs.append((t.decision, req, BY_FORMABLE[t.forms].home_capital))
    for decision, areas in CUSTOM_TRIGGERS.items():
        req = sorted({int(p) for a in areas for p in _pd()["areas"].get(a, ())})
        specs.append((decision, req, True))

    body = "\n\n".join(
        formation_trigger_block(f"{k}_provinces_trigger", p) for k, p, _ in specs
    )
    if any(cap for _, _, cap in specs):
        body += "\n\n" + "\n\n".join(
            formation_capital_trigger_block(f"{k}_capital_trigger", p)
            for k, p, cap in specs
            if cap
        )
    sdir = os.path.join(MOD, "common", "scripted_triggers")
    os.makedirs(sdir, exist_ok=True)
    spath = os.path.join(sdir, "KarolingianFormations.txt")
    write_out(spath, "# province triggers backing the formation decisions\n" + body + "\n")
    print(f"wrote {spath}  ({len(specs)} triggers)")

    old = os.path.join(
        MOD, "common", "trigger_localisation", "KarolingianFormations_l_english.yml"
    )
    if os.path.exists(old):
        os.remove(old)
