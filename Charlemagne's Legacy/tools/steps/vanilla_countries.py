#!/usr/bin/env python3
"""The base game's own countries: read their definitions, recolour them from CK3, and the restore-colours decision."""

import os
import re
from ck3 import load_title_colors
from functools import lru_cache
from tagdb import BY_TAG, FORMABLES, TAGS
from steps.layout import GAME, MOD
from steps.output import write_loc, write_out


@lru_cache(maxsize=1)
def load_vanilla_countries() -> dict[str, tuple[str, str]]:
    """{tag: (filename, text)} for every vanilla country definition."""
    out = {}
    cd = os.path.join(GAME, "common", "countries")
    for fn in os.listdir(os.path.join(GAME, "common", "country_tags")):
        if not fn.endswith(".txt"):
            continue
        text = open(
            os.path.join(GAME, "common", "country_tags", fn),
            encoding="cp1252",
            errors="replace",
        ).read()
        for m in re.finditer(r'^([A-Z]{3})\s*=\s*"countries/([^"]+)"', text, re.M):
            p = os.path.join(cd, m.group(2))
            if os.path.exists(p):
                base = open(p, encoding="cp1252", errors="replace").read()
                out.setdefault(m.group(1), (m.group(2), base))
    return out


def step_vanilla_countries() -> None:
    """Rewrite the vanilla realms' country definitions under the mod, copying
    the vanilla data verbatim and swapping in the colour lifted from CK3, so
    every tag covered by the mod matches its CK3 title's map colour."""
    colors = load_title_colors()
    vanilla = load_vanilla_countries()
    os.makedirs(os.path.join(MOD, "common", "countries"), exist_ok=True)
    written = 0
    pairs = [(t.tag, t.ck3_title) for t in TAGS]
    pairs += [(fb.tag, fb.ck3_title) for fb in FORMABLES]
    for code, title in pairs:
        want = colors.get(title) if title else None
        if want is None:
            # Dormant tags with no CK3 title colour (Galicia) carry their
            # own declared colour instead.
            row = BY_TAG.get(code)
            want = row.color if row and row.color[0] is not None else None
        base = vanilla.get(code)
        if not want or not base:
            continue
        fn, text = base
        body = re.sub(
            r"(?m)^color = \{.*?\}",
            f"color = {{ {want[0]}  {want[1]}  {want[2]} }}",
            text,
            count=1,
        )
        if body == text:
            print(f"  {code}: {title} colour {want} already {fn}?")
        p = os.path.join(MOD, "common", "countries", fn)
        write_out(p, body)
        print(f"wrote {p}  (colour from {title} = {want})")
        written += 1
    print(f" {written} vanilla realm definitions rewritten under the mod")


_VANILLA_CTRY_FILES: dict = {}


@lru_cache(maxsize=1)
def vanilla_colours() -> dict[str, tuple[int, int, int]]:
    """{tag: (r,g,b)} straight from the base game's country files."""
    out = {}
    for tag, (fn, text) in load_vanilla_countries().items():
        m = re.search(r"(?m)^\s*color\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)", text)
        if not m:
            raise ValueError(f"vanilla country file {fn} ({tag}) has no colour line")
        out[tag] = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return out


def step_restore_colours() -> None:
    """One singular decision: any tag the mod reuses from the base game may
    put the base game's own colours back (our files carry the CK3 palette;
    this is the player's way home). The map of every basegame tag in the mod
    against its vanilla colour is written as one if-branch per tag inside
    the decision, so it stays singular and always matches the current tag.
    """
    os.makedirs(os.path.join(MOD, "decisions"), exist_ok=True)
    colors = vanilla_colours()
    targets = sorted({t.tag for t in TAGS if t.tag in colors})
    key = "kar_restore_base_game_colours"
    ors = "\n".join(f"\t\t\t\ttag = {tag}" for tag in targets)
    branches = "\n".join(
        f"\t\tif = {{\n"
        f"\t\t\tlimit = {{ tag = {tag} }}\n"
        f"\t\t\tchange_country_color = {{\n"
        f"\t\t\t\tcolor = {{ {r} {g} {b} }}\n"
        f"\t\t\t}}\n"
        f"\t\t}}"
        for tag, (r, g, b) in sorted(colors.items()) if tag in set(targets)
    )
    txt = (
        "# The CK3 palette stands in the country files; this one decision lets\n"
        "# any tag the mod reuses from the base game restore the base game's\n"
        "# own colours. One generated branch per basegame tag in the mod, so\n"
        "# the decision stays singular and always matches the current tag.\n"
        "country_decisions = {\n"
        f"\t{key} = {{\n"
        "\t\tpotential = {\n"
        "\t\t\tOR = {\n"
        f"{ors}\n"
        "\t\t\t}\n"
        "\t\t}\n"
        "\t\tallow = {\n"
        "\t\t\talways = yes\n"
        "\t\t}\n"
        "\t\teffect = {\n"
        f"{branches}\n"
        "\t\t}\n"
        "\t\tai_will_do = {\n"
        "\t\t\tfactor = 0\n"
        "\t\t}\n"
        "\t}\n"
        "}\n"
    )
    p = os.path.join(MOD, "decisions", "KarRestoreColours.txt")
    write_out(p, txt)
    loc = os.path.join(MOD, "localisation", "karolingian_colours_l_english.yml")
    write_loc(
        loc,
        [
            (key, "Restore the Old Colors"),
            (key + "_title", "Restore the Old Colors"),
            (
                key + "_desc",
                "Whoever wears the crown today, the old realm once flew colors "
                "that men could name from across the field. Let us look to our "
                "fathers' banners again and restore the true colors of our nation.",
            ),
        ],
    )
    print(f"wrote {p} ({len(targets)} basegame tags)")
