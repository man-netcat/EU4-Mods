#!/usr/bin/env python3
"""Lift CK3's rite icons onto the Christian rite schools.

Each rite's `icon` in CK3's common/religion/rite_types is a faith icon
(gfx/interface/icons/faith/<icon>.dds). It is scaled to the 52x52 of the
vanilla school icons and written over the placeholder
gfx/interface/icon_christian_school_<key>.tga, which build.py then keeps.
Idempotent; needs Pillow and the CK3 game files.

    python3 tools/rite_icons.py
"""
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import CK3_GAME  # noqa: E402
import rites  # noqa: E402

MOD = os.path.join(HERE, "..")
SIZE = 52


def rite_icon(rite, text):
    m = re.search(r"(?m)^%s = \{" % re.escape(rite), text)
    if not m:
        sys.exit(f"CK3 has no rite {rite}")
    depth, i = 0, text.index("{", m.start())
    for j in range(i, len(text)):
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        if depth == 0:
            body = text[m.start():j]
            break
    ic = re.search(r"(?m)^\s*icon = (\S+)", body)
    if not ic:
        sys.exit(f"CK3 rite {rite} has no icon")
    return ic.group(1)


def main():
    text = open(os.path.join(CK3_GAME, "common", "religion", "rite_types",
                             "00_rite_types.txt"), encoding="utf-8-sig").read()
    for key, rite, *_ in rites.RITES:
        icon = rite_icon(rite, text)
        src = os.path.join(CK3_GAME, "gfx", "interface", "icons", "faith",
                           icon + ".dds")
        out = os.path.join(MOD, "gfx", "interface",
                           f"icon_christian_school_{key}.tga")
        im = Image.open(src).convert("RGBA").resize((SIZE, SIZE), Image.LANCZOS)
        im.save(out)
        print(f"{key:20} <- {icon}")


if __name__ == "__main__":
    main()
