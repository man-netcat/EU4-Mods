#!/usr/bin/env python3
"""Interface overrides that must stay in step with the data: religion strips and government rank strips."""

import os
import re
from checks.report import note, warn
from checks.context import GAME, MOD


def interface_religion_strip_overrides_stay_in_sync() -> None:
    """Interface religion-strip overrides stay in sync."""
    print("\n== interface religion-strip overrides stay in sync ==")
    max_icon = max(
        int(n)
        for n in re.findall(
            r"(?m)^\t\ticon = (\d+)",
            open(
                os.path.join(MOD, "common", "religions", "00_religion.txt"),
                encoding="utf-8",
                errors="replace",
            ).read(),
        )
    )
    REL_SPRITES = {
        "countryview.gfx": [
            "GFX_icon_religion",
            "GFX_country_icon_religion",
            "GFX_icon_religion_small",
        ],
        "ledger.gfx": ["GFX_religion_icon_strip"],
        "provinceview.gfx": ["GFX_province_view_religion"],
    }
    gfx_bad = []
    missing_strips = set()
    for fn, want in REL_SPRITES.items():
        vtext = open(
            os.path.join(GAME, "interface", fn), encoding="utf-8", errors="replace"
        ).read()
        mtext = open(os.path.join(MOD, "interface", fn), encoding="utf-8").read()
        vspr = re.findall(r'name = "(GFX_[^"]+)"', vtext)
        mspr = re.findall(r'name = "(GFX_[^"]+)"', mtext)
        if vspr != mspr:
            gfx_bad.append(f"{fn} sprite list drifted")
        for spr in want:
            m = re.search(
                r'name = "' + spr + r'".*?texturefile = "([^"]+)"',
                mtext,
                re.S,
            )
            if not m or not m.group(1).endswith(".dds"):
                gfx_bad.append(f"{fn} {spr} not pointed at our DDS strip")
                continue
            rel = re.split(r"[\\/]+", m.group(1))[-1]
            full = os.path.join(MOD, "gfx", "interface", rel)
            if not os.path.exists(full):
                # the strips are images, made by a local `faiths.py icons` run; a package
                # built from the text alone has none
                missing_strips.add(rel)
                continue
            with open(full, "rb") as fh:
                head = fh.read(24)
            import struct as _st

            w = _st.unpack("<I", head[16:20])[0] if head[:4] == b"DDS " else 0
            if w % max_icon or w // max(1, max_icon) not in (64, 32):
                gfx_bad.append(f"{fn} {spr} strip width {w} != {max_icon} frames")
            f = re.search(
                r'name = "' + spr + r'".*?noOfFrames = (\d+)', mtext, re.S
            )
            if not f or int(f.group(1)) != max_icon:
                gfx_bad.append(f"{fn} {spr} frames != {max_icon}")
    note(not gfx_bad, f"religion icon overrides intact ({len(gfx_bad)} bad)")
    if missing_strips:
        warn("religion icon strips not built here: " + ", ".join(sorted(missing_strips)))
    for b in gfx_bad[:8]:
        print("        " + b)


def government_rank_strip_matches_rank_count() -> None:
    """Government rank strip matches the rank count."""
    print("\n== government rank strip matches the rank count ==")
    rank_bad = []
    mgfx = open(os.path.join(MOD, "interface", "countrydiplomacyview.gfx")).read()
    vgfx = open(
        os.path.join(GAME, "interface", "countrydiplomacyview.gfx"),
        encoding="utf-8",
        errors="replace",
    ).read()
    if re.findall(r'name = "(GFX_[^"]+)"', vgfx) != re.findall(
        r'name = "(GFX_[^"]+)"', mgfx
    ):
        rank_bad.append("countrydiplomacyview.gfx sprite list drifted")
    f = re.search(
        r'name = "GFX_government_rank_strip".*?noOfFrames = (\d+)', mgfx, re.S
    )
    want = 5 if os.path.exists(os.path.join(MOD, "gfx", "interface", "government_rank_strip.dds")) else 3
    if not f or int(f.group(1)) != want:
        rank_bad.append(f"GFX_government_rank_strip frames != {want} (county..hegemony)")
    dds = os.path.join(MOD, "gfx", "interface", "government_rank_strip.dds")
    if os.path.exists(dds):
        with open(dds, "rb") as fh:
            head = fh.read(24)
        import struct as _st2

        w = _st2.unpack("<I", head[16:20])[0] if head[:4] == b"DDS " else 0
        if w != 200:
            rank_bad.append(f"government_rank_strip width {w} != 5x40 frames")
    else:
        warn("government_rank_strip.dds not built here (an image: made locally); ranks keep the base game's 3 icons")
    note(not rank_bad, f"rank strip intact ({len(rank_bad)} bad)")
    for b in rank_bad[:8]:
        print("        " + b)


def run() -> None:
    interface_religion_strip_overrides_stay_in_sync()
    government_rank_strip_matches_rank_count()
