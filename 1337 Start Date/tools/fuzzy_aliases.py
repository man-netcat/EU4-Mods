"""Name matches the exact-name tiers of loc2prov miss, for the provinces still unmatched or matched only to a whole area.

An EU4 province name is compared with EU5 locations and province/area nodes in the EU5 regions its EU4 region already maps
to. Spelling variants count (Tsaidam/Qaidam, Ghazni/Ghaznah): names are folded to a skeleton (no vowels doubled or
accents, k/q/c, ph/f, ...) and a match needs a high similarity, a unique best candidate, and no better claim by another
province. Results go to data/aliases_auto.json (EU4 province -> EU5 names); hand aliases in aliases.json win.

    python3 tools/fuzzy_aliases.py            # write data/aliases_auto.json, then rerun loc2prov.py
    python3 tools/fuzzy_aliases.py --show     # also print every match
"""
import collections
import difflib
import json
import re
import sys

from loc2prov import L5, eu4_geo, eu4_provinces, eu5_tree, land_provinces, norm, yml
from paths import MOD

SIM = 0.9
EUROPE = ("scandinavia british_isles france iberia italy low_countries north_german south_german poland baltic russia ruthenia "
          "carpathia balkan crimea").split()
FOLD = (("ph", "f"), ("q", "k"), ("c", "k"), ("w", "v"), ("y", "i"), ("j", "i"), ("z", "s"), ("x", "s"), ("th", "t"),
        ("dh", "d"), ("kh", "k"), ("gh", "g"), ("sh", "s"), ("ch", "s"), ("oo", "u"), ("ou", "u"), ("ee", "i"))


def skeleton(s):
    s = norm(s)
    for a, b in FOLD:
        s = s.replace(a, b)
    s = re.sub(r"(.)\1+", r"\1", s)
    return s


def main(show=False):
    nodes, level, locs, path = eu5_tree()
    area, reg = eu4_geo()
    names, land = eu4_provinces(), land_provinces()
    import loc2prov
    # the matching without the fuzzy aliases themselves, so rerunning gives the same answer
    _prov, base, _locs = loc2prov.main(auto=False, write=False)
    m = {str(p): {"tier": t, "locations": l} for p, (t, l) in base.items()}
    hand = {int(k) for k in json.load(open(MOD / "tools/data/aliases.json")) if not k.startswith("_")}
    pools = collections.Counter(tuple(sorted(v["locations"])) for v in m.values())

    def uncertain(p):
        v = m.get(str(p))
        return not v or v["tier"] in ("area-node", "area-fallback") or pools[tuple(sorted(v["locations"]))] > 1

    top = lambda l: next((n for n in path[l] if n.endswith("_region")), None)
    # EU5 regions each EU4 region maps to (from its certain provinces)
    votes = collections.defaultdict(collections.Counter)
    for p in land:
        if not uncertain(p) and str(p) in m:
            for l in m[str(p)]["locations"]:
                votes[reg.get(area.get(p))][top(l)] += 1
    ok = {r: {k for k, v in c.items() if v >= 0.1 * sum(c.values())} for r, c in votes.items()}
    other_names = collections.defaultdict(set)  # skeleton of an EU4 province name -> its provinces
    for p2, ns in names.items():
        for n in ns:
            other_names[skeleton(n)].add(p2)
    claimed = set()
    for p, v in m.items():
        if not uncertain(int(p)):
            claimed |= set(v["locations"])
    # display names of EU5 locations and nodes
    disp = {}
    for f in sorted((L5 / "location_names").glob("*_l_english.yml")):
        for k, v in yml(f).items():
            if k in locs:
                disp.setdefault(k, set()).add(v)
    cands = collections.defaultdict(list)  # EU5 region -> [(skeleton, name, kind)]
    for l in locs:
        if l in claimed:
            continue
        for n in {l, *disp.get(l, ())}:
            cands[top(l)].append((skeleton(n), l, "loc", norm(n)))
    for n, ls in nodes.items():
        if level.get(n) == 3 and all(x not in claimed for x in ls):
            cands[top(next(iter(ls)))].append((skeleton(re.sub(r"_(province|area)$", "", n)), n, "node", norm(re.sub(r"_(province|area)$", "", n))))
    prov_names = {}
    for f in ("province_names", "area"):
        for k, v in yml(L5 / f"{f}_l_english.yml").items():
            n = re.sub(r"_(province|area|region)$", "", k)
            for cand in (k, n):
                if cand in nodes:
                    prov_names.setdefault(cand, set()).add(v)
    for n, vs in prov_names.items():
        if n in nodes and all(x not in claimed for x in nodes[n]):
            for v in vs:
                cands[top(next(iter(nodes[n])))].append((skeleton(v), n, "node", norm(v)))
    found = {}
    taken = collections.defaultdict(set)
    scored = []
    for p in sorted(land):
        if not uncertain(p) or p in hand:
            continue
        r = reg.get(area.get(p))
        if r and r[:-len("_region")] in EUROPE:
            continue  # Europe is done by hand
        sk = [(skeleton(n), norm(n)) for n in names[p] if len(norm(n)) >= 4]
        best = []
        for er in ok.get(r, ()):
            for s, target, kind, raw in cands.get(er, ()):
                for a, an in sk:
                    if len(s) < 5 or len(a) < 5 or a[0] != s[0] or abs(len(a) - len(s)) > 3:
                        continue
                    ratio = difflib.SequenceMatcher(None, a, s).ratio()
                    if difflib.SequenceMatcher(None, an, raw).ratio() < 0.88:
                        continue  # the skeletons agree but the plain spellings do not (Nanjing / Nanning)
                    if ratio >= SIM and other_names.get(s, {p}) <= {p}:  # not another province's own name
                        best.append((ratio, target, kind))
        if best:
            best.sort(reverse=True)
            scored.append((best[0][0], p, best[0][1], best[0][2], len({b[1] for b in best if b[0] == best[0][0]})))
    for ratio, p, target, kind, ties in sorted(scored, reverse=True):
        if ties == 1 and target not in taken[kind]:
            taken[kind].add(target)
            found[p] = [target]
            if show:
                print(f"{p:5} {names[p][0]:22} -> {target} ({kind}, {ratio:.2f})")
    json.dump({str(p): v for p, v in sorted(found.items())}, open(MOD / "tools/data/aliases_auto.json", "w"), indent=0)
    print(len(found), "fuzzy matches")


if __name__ == "__main__":
    main("--show" in sys.argv)
