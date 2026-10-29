#!/usr/bin/env python3
"""The Magyars: their reform, starting army, migration war and settlement script."""

import os
import shutil
from histgen import country_definition, formation_decision, requirement_provinces
from paths import local_mod_path
from tagdb import BY_FORMABLE, TAGS
from steps.layout import GAME, MOD
from steps.output import write_out
from steps.vanilla_countries import load_vanilla_countries
from steps.vanilla_scripts import VANILLA_FORMATION_FILES


def step_custom() -> None:
    vanilla = load_vanilla_countries()
    customs = [t for t in TAGS if t.tag not in vanilla]
    if not customs:
        return

    os.makedirs(os.path.join(MOD, "common", "country_tags"), exist_ok=True)
    os.makedirs(os.path.join(MOD, "common", "countries"), exist_ok=True)
    os.makedirs(os.path.join(MOD, "gfx", "flags"), exist_ok=True)

    reg = os.path.join(MOD, "common", "country_tags", "00_karolingian_custom.txt")
    reg_lines = []

    for t in customs:
        cname = t.country_file or f"{t.name}.txt"
        reg_lines.append(f'{t.tag} = "countries/{cname}"')

        cfile = os.path.join(MOD, "common", "countries", cname)
        write_out(cfile, country_definition(t))
        print(f"wrote {cfile}")

        if t.flag_from:
            raise SystemExit(f"{t.tag}: flag_from {t.flag_from} - base-game flags are never reused; "
                             "give the tag its own flag (or leave it visibly missing)")
        if t.flag_source:
            flag = local_mod_path(t.flag_source)
            assert not os.path.abspath(flag).startswith(os.path.abspath(GAME)), \
                f"{t.tag}: flag_source {flag} is inside the base game - vanilla flags are never reused"
            assert os.path.exists(flag), f"no flag for {t.tag} at {flag}"
            dest = os.path.join(MOD, "gfx", "flags", f"{t.tag}.tga")
            if os.path.exists(dest):
                print(f"kept gfx/flags/{t.tag}.tga (custom, not overwritten)")
            else:
                shutil.copy2(flag, dest)
                print(f"copied gfx/flags/{t.tag}.tga")
        else:
            print(f"no flag for {t.tag} (needs one)")

        if not t.forms:
            print(f"  {t.tag} has no formable tag")
            continue

    by_formable: dict[str, list] = {}
    for t in TAGS:
        if t.forms:
            by_formable.setdefault(t.forms, []).append(t)
    for fcode, starters in sorted(by_formable.items()):
        if fcode == "ROM":
            # Rome restores via decisions/FormROM.txt (handwritten, vanilla
            # behaviour); nothing to generate here.
            continue
        fb = BY_FORMABLE[fcode]
        req = requirement_provinces(fcode)
        txt = formation_decision(fcode, starters)
        os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
        p = os.path.join(MOD, "decisions", f"Form{fcode}.txt")
        write_out(p, txt)
        print(f"wrote {p}")
        print(
            f"  formed tag            : {', '.join(s.tag for s in starters)}"
            f" -> {fcode}, rank {fb.rank}"
        )
        print(f"  required provinces    : {len(req)}")
        print(f"  areas covered         : {', '.join(fb.areas) or 'none'}")
        print(
            "  suppressed decisions  : "
            + ", ".join(sorted({k for s in starters for k in s.suppress}))
        )

    # Vanilla formation decisions are neutralized by same-filename dummy
    # files: duplicate keys coexist across files, so stubs in our own files
    # never win. Each dummy carries only the always-no stubs.
    stubbed = sorted({k for t in TAGS if t.forms for k in t.suppress})
    for fn, keys in VANILLA_FORMATION_FILES.items():
        kill = [k for k in keys if k in stubbed]
        if not kill:
            continue
        stubs = "\n".join(
            f"\t{k} = {{\n"
            f"\t\tpotential = {{\n"
            f"\t\t\talways = no\n"
            f"\t\t}}\n"
            f"\t\tallow = {{\n"
            f"\t\t}}\n"
            f"\t\teffect = {{\n"
            f"\t\t}}\n"
            f"\t}}"
            for k in kill
        )
        sp = os.path.join(MOD, "decisions", fn)
        write_out(
            sp,
            f"# dummy: vanilla formations neutralized, use our kar_form_* instead\n"
            f"country_decisions = {{\n{stubs}\n}}\n",
        )
        print(f"wrote {sp} (dummy, neutralized {len(kill)})")

    write_out(reg, "\n".join(reg_lines) + "\n")
    print(f"wrote {reg}")
