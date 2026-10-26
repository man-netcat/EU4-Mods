#!/usr/bin/env python3
"""Move every tag onto its 867 ruler's culture and faith (what validate checks).

    python3 tools/synctags.py        # list the drift
    python3 tools/synctags.py apply  # write culture and religion into tags.db

A culture the lift maps (culturelift.CK3_TO_EU4) is created when the mod lacks it.
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def main(apply):
    import culturelift as cl

    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    n = 0
    for tag, title, cul, rel in con.execute("select tag, ck3_title, culture, religion from tags order by seq").fetchall():
        _h, cc = cl.holder_culture(title)
        want_c = cl.CK3_TO_EU4.get(cc) if cc else None
        _h, faith = cl.holder_faith(title)
        want_r = cl.FAITH_TO_RELIGION.get(faith) if faith else None
        ch = {}
        if want_c and want_c != cul:
            ch["culture"] = want_c
        if want_r and want_r != rel:
            ch["religion"] = want_r
        if not ch:
            continue
        n += 1
        print(f"{tag}: {cul}/{rel} -> {ch}")
        if apply:
            if "culture" in ch:
                con.execute("insert or ignore into cultures(name) values (?)", (ch["culture"],))
            for k, v in ch.items():
                con.execute(f"update tags set {k}=? where tag=?", (v, tag))
    con.commit()
    print(n, "tags" + (" updated" if apply else " drift"))


if __name__ == "__main__":
    main(sys.argv[1:2] == ["apply"])
