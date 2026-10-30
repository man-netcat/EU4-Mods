#!/usr/bin/env python3
"""What each sovereign tag can field at the 867 start, for balancing.

    python3 tools/troops.py [N]      # the N largest (default 40); --all lists every tag, --csv writes the table

Model (EU4 1.37): force limit = (6 + 0.1 per development point) x (1 + land_forcelimit_modifier of the government
reforms); manpower = (10 + 0.25 per manpower development point) thousand x (1 + global_manpower_modifier). A subject adds
its own figure times its subject type's forcelimit_to_overlord / manpower_to_overlord (vassal 0, march 0.1, governor
(theme_subject_type) 0.5, personal union and tributary 0). Autonomy, buildings, ideas and traditions are not modelled, so
read the numbers as a ranking, not as in-game values. "Sovereign" is a tag with no vassal-like overlord (tributaries and
allies still count as independent); "bloc" adds every subject's own full figure to show who stands behind a realm."""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("EU4_GAME", os.path.join(HERE, "..", "..", "..", "eu4-ck3-reference", "eu4"))

from paths import EU4_GAME  # noqa: E402
from tagdb import BY_TAG, DIPLOMACY, DORMANT, PEER_RELATIONS  # noqa: E402

MOD = os.path.join(HERE, "..")


def _dev():
    out = {}
    for f in glob.glob(os.path.join(MOD, "history", "provinces", "*.txt")):
        m = re.match(r"(\d+)", os.path.basename(f))
        t = open(f, encoding="cp1252", errors="replace").read()
        g = lambda k: int((re.search(rf"^{k}\s*=\s*(\d+)", t, re.M) or [0, 0])[1])  # noqa: E731
        out[int(m.group(1))] = (g("base_tax") + g("base_production") + g("base_manpower"), g("base_manpower"))
    return out


def _reform_mods():
    mods = {}
    for root in (os.path.join(EU4_GAME, "common", "government_reforms"), os.path.join(MOD, "common", "government_reforms")):
        for f in glob.glob(os.path.join(root, "*.txt")):
            t = open(f, encoding="cp1252", errors="replace").read()
            for m in re.finditer(r"^(\w+)\s*=\s*\{", t, re.M):
                body, depth, i = [], 0, m.end() - 1
                while i < len(t):
                    depth += (t[i] == "{") - (t[i] == "}")
                    if depth == 0:
                        break
                    i += 1
                body = t[m.end():i]
                mm = re.search(r"\bmodifiers\s*=\s*\{([^}]*)\}", body)
                blk = mm.group(1) if mm else ""
                v = lambda k: float((re.search(rf"\b{k}\s*=\s*(-?[\d.]+)", blk) or [0, 0])[1])  # noqa: E731
                mods[m.group(1)] = (v("land_forcelimit_modifier"), v("global_manpower_modifier"))
    return mods


def _subject_values():
    t = open(os.path.join(MOD, "common", "subject_types", "00_subject_types.txt"), encoding="cp1252", errors="replace").read()
    blocks = {}
    for m in re.finditer(r"^(\w+)\s*=\s*\{(.*?)^\}", t, re.M | re.S):
        blocks[m.group(1)] = m.group(2)
    vals = {}
    def get(name):
        if name in vals:
            return vals[name]
        b = blocks.get(name, "")
        cf = re.search(r"copy_from\s*=\s*(\w+)", b)
        base = get(cf.group(1)) if cf else (0.0, 0.0)
        f = re.search(r"^\s*forcelimit_to_overlord\s*=\s*([\d.]+)", b, re.M)
        p = re.search(r"^\s*manpower_to_overlord\s*=\s*([\d.]+)", b, re.M)
        vals[name] = (float(f[1]) if f else base[0], float(p[1]) if p else base[1])
        return vals[name]
    for n in blocks:
        get(n)
    return vals


def main(argv):
    dev, rmods, sv = _dev(), _reform_mods(), _subject_values()
    own = {}
    for tag, t in BY_TAG.items():
        if tag in DORMANT:
            continue
        d = sum(dev.get(p, (0, 0))[0] for p in t.provinces)
        m = sum(dev.get(p, (0, 0))[1] for p in t.provinces)
        flm = sum(rmods.get(r, (0, 0))[0] for r in t.reforms)
        mpm = sum(rmods.get(r, (0, 0))[1] for r in t.reforms)
        if not t.provinces:
            continue
        own[tag] = [(6 + 0.1 * d) * (1 + flm), (10 + 0.25 * m) * (1 + mpm), d, len(t.provinces)]
    subj = {}
    for d in DIPLOMACY:
        if d.relation in PEER_RELATIONS or d.relation == "tributary_state":
            continue
        subj.setdefault(d.subject, []).append((d.liege, d.relation))
    rows = []
    for tag, (fl, mp, d, n) in own.items():
        if any(rel not in ("tributary_state",) for _, rel in subj.get(tag, [])):
            continue
        add_f = add_m = bloc_f = bloc_m = 0.0
        stack = [(tag, 1.0, 1.0)]
        for s, lst in subj.items():
            for lg, rel in lst:
                if lg == tag and s in own:
                    f, p = sv.get(rel, (0.0, 0.0))
                    add_f += own[s][0] * f
                    add_m += own[s][1] * p
                    bloc_f += own[s][0]
                    bloc_m += own[s][1]
        rows.append((tag, BY_TAG[tag].name, n, d, fl, add_f, fl + add_f, mp, add_m, mp + add_m, fl + bloc_f, mp + bloc_m))
    rows.sort(key=lambda r: -r[6])
    hdr = ("tag", "name", "provs", "dev", "FL own", "FL subj", "FL total", "MP own k", "MP subj k", "MP total k", "FL bloc", "MP bloc k")
    if "--csv" in argv:
        w = csv.writer(sys.stdout)
        w.writerow(hdr)
        w.writerows([[round(x, 1) if isinstance(x, float) else x for x in r] for r in rows])
        return
    lim = len(rows) if "--all" in argv else int(next((a for a in argv if a.isdigit()), 40))
    print(("{:<4} {:<22} {:>5} {:>5} {:>7} {:>7} {:>8} {:>9} {:>9} {:>10} {:>8} {:>10}").format(*hdr))
    for r in rows[:lim]:
        print("{:<4} {:<22} {:>5} {:>5} {:>7.1f} {:>7.1f} {:>8.1f} {:>9.1f} {:>9.1f} {:>10.1f} {:>8.1f} {:>10.1f}".format(r[0], r[1][:22], *r[2:]))
    print(f"\n{len(rows)} sovereign tags; median FL total {sorted(r[6] for r in rows)[len(rows)//2]:.1f}")


if __name__ == "__main__":
    main(sys.argv[1:])
