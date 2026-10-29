#!/usr/bin/env python3
"""Country definitions and files: the mod skeleton, every tag's country file, its colour, capital and rank."""

import os
import re
from checks.report import note
from checks.context import BY_TAG, CAPS, COUNTRY_OUT, GAME, GH, KEPT_REALMS, MOD, PDIR, RANK, TAGS, _REALMS, country_path
from paths import local_mod_path


def mod_skeleton() -> None:
    print("== mod skeleton ==")
    for p in [
        local_mod_path("/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/Charlemagne's Legacy.mod"),
        f"{MOD}/descriptor.mod",
        f"{MOD}/localisation/replace/countries_l_english.yml",
    ]:
        note(os.path.exists(p), f"exists {os.path.relpath(p, MOD)}")


def country_definitions() -> None:
    """Country definitions."""
    print("\n== country definitions ==")
    base = {fn.split(" ")[0] for fn in os.listdir(GH) if fn.endswith(".txt")}
    note("LUS" not in base, "no invented LUS tag is in use (base game Lusatia is SOR)")
    mine = set()
    MC = os.path.join(MOD, "common", "countries")
    if os.path.isdir(MC):
        for fn in os.listdir(MC):
            if fn.endswith(".txt"):
                p = os.path.join(MC, fn)
                t = open(p, encoding="utf-8", errors="replace").read()
                note(
                    t.count("{") == t.count("}"),
                    f"braces balanced in common/countries/{fn}",
                )
                mine.add(fn.split(" ")[0])
    CT = os.path.join(MOD, "common", "country_tags")
    if os.path.isdir(CT):
        for fn in os.listdir(CT):
            if not fn.endswith(".txt"):
                continue
            text = open(os.path.join(CT, fn), encoding="utf-8", errors="replace").read()
            for m in re.finditer(r'^([A-Z]{3})\s*=\s*"countries/([^"]+)"', text, re.M):
                tag, cfile = m.group(1), m.group(2)
                note(
                    os.path.exists(os.path.join(MC, cfile)),
                    f"{tag} registry entry {fn} -> countries/{cfile} resolves",
                )
                mine.add(tag)
    for t in TAGS:
        where = (
            "base game"
            if t in base
            else ("mod common/countries" if t in mine else "NOWHERE")
        )
        note(t in base or t in mine, f"{t} country definition resolvable ({where})")

    from ck3 import load_title_colors
    from steps.vanilla_countries import load_vanilla_countries

    vcountries = load_vanilla_countries()
    ck3_colors = load_title_colors()
    for t in _REALMS:
        if not t.ck3_title:
            continue
        vbase = vcountries.get(t.tag)
        if vbase is None:
            p = os.path.join(MC, t.country_file or f"{t.name}.txt")
        else:
            p = os.path.join(MC, vbase[0])
        want = ck3_colors.get(t.ck3_title)
        body = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^color = \{?\s*(\d+)\s+(\d+)\s+(\d+)", body)
        got = tuple(int(x) for x in m.groups()) if m else None
        if want is None:
            note(
                got == t.color,
                f"{t.tag} colour stays {t.color} (CK3 has no {t.ck3_title} colour)",
            )
        else:
            note(
                got == want,
                f"{t.tag} colour {got} lifted from CK3 {t.ck3_title} {want}",
            )
    landless = [t.tag for t in _REALMS if t.ck3_title and t.ck3_title.startswith("d_nf_")]
    note(not landless, "no tag sits on a landless noble-family duchy (d_nf_*); it takes the land duchy its "
         "holder holds" + (f" ({', '.join(landless)})" if landless else ""))
    # tags whose CK3 title gives no usable colour carry their own: it must be a real colour and
    # no other tag's
    own = [t for t in _REALMS if t.ck3_title and ck3_colors.get(t.ck3_title) is None]
    greys = [t.tag for t in own if max(t.color) - min(t.color) < 20]
    note(not greys, f"tags with their own colour are not grey ({', '.join(greys) or 'none'})")
    seen = {}
    for t in _REALMS:
        eff = t.color if t in own else (ck3_colors.get(t.ck3_title) or t.color)
        seen.setdefault(eff, []).append(t.tag)
    clash = {c: ts for c, ts in seen.items() if len(ts) > 1 and any(x in {o.tag for o in own} for x in ts)}
    note(not clash, "tags with their own colour share it with no other tag"
         + ("".join(f" {c}: {', '.join(ts)};" for c, ts in clash.items()) if clash else ""))
    for t in TAGS:
        if t not in base and t not in mine:
            continue
        g = [fn for fn in os.listdir(GH) if fn.startswith(t + " - ")]
        if g:
            body = open(
                os.path.join(GH, g[0]), encoding="utf-8", errors="replace"
            ).read()
            note(
                re.search(r"^\s*capital\s*=\s*(\d+)", body, re.M) is not None,
                f"{t} vanilla history declares a capital",
            )


def brace_balance() -> None:
    """Brace balance."""
    print("\n== brace balance ==")
    n = 0
    bad = []
    for d in (PDIR, COUNTRY_OUT):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".txt"):
                continue
            n += 1
            t = re.sub(
                r"#.*",
                "",
                open(
                    os.path.join(d, fn), encoding="utf-8", errors="surrogateescape"
                ).read(),
            )
            if t.count("{") != t.count("}"):
                bad.append(f"{fn} {t.count('{')}/{t.count('}')}")
    note(not bad, f"balanced braces in all {n} files")
    for b in bad[:10]:
        print("        " + b)


def check_867_only() -> None:
    """867 only."""
    print("\n== 867 only ==")
    n = 0
    bad = []
    for d in (PDIR, COUNTRY_OUT):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".txt"):
                continue
            n += 1
            t = open(
                os.path.join(d, fn), encoding="utf-8", errors="surrogateescape"
            ).read()
            for m in re.finditer(r"(?m)^\s*(\d+\.\d+\.\d+)\s*=", t):
                if m.group(1) != "867.1.1":
                    bad.append(f"{fn}: {m.group(1)}")
                    break
    note(not bad, f"no non-867 history in {n} files")
    for b in bad[:10]:
        print("        " + b)


def country_files() -> None:
    """Country files."""
    print("\n== country files ==")


    vanilla_hist = {
        fn.split(" - ")[0]
        for fn in os.listdir(os.path.join(GAME, "history", "countries"))
        if fn.endswith(".txt")
    }
    for t in TAGS:
        spec = BY_TAG.get(t)
        if spec is not None and not spec.country_file and t not in vanilla_hist:
            note(
                False,
                f"{t} needs country_file set (else its file is '{t} - {t}.txt')",
            )


    for t in TAGS:
        txt = open(
            country_path(t),
            encoding="utf-8",
            errors="surrogateescape",
        ).read()
        note(f"capital = {CAPS[t]}" in txt, f"{t} capital = {CAPS[t]}")
        note("monarch = {" in txt, f"{t} has an 867 monarch")


def kept_realm_has_a_deliberate_rank() -> None:
    """Every kept realm has a deliberate rank."""
    print("\n== every kept realm has a deliberate rank ==")
    unwritten = []
    for t in sorted(KEPT_REALMS):
        path = country_path(t)
        if not os.path.exists(path):
            unwritten.append(t)
            continue
        txt = open(path, encoding="utf-8", errors="surrogateescape").read()
        want = RANK[t]

        top = re.search(r"^government_rank\s*=\s*(\d+)", txt, re.M)
        got = int(top.group(1)) if top else None
        note(
            got == want,
            f"{t} government_rank = {want}"
            + ("" if got is None else f" (top-level, found {got})")
            + (" - ABSENT, so EU4 defaults it to a duchy" if top is None else ""),
        )

    note(
        not unwritten,
        f"every kept realm has a country file ({len(KEPT_REALMS)} realms)",
    )
    for t in unwritten:
        print(f"        {t}: holds land, has a rank, but no country file")


def run() -> None:
    mod_skeleton()
    country_definitions()
    brace_balance()
    check_867_only()
    country_files()
    kept_realm_has_a_deliberate_rank()
