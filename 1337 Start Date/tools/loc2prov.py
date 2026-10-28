"""Name/hierarchy based EU4 province -> EU5 location sets (no map geometry).

Tiers, first hit wins per EU4 province:
  1 key      EU4 file/loc name == EU5 location key
  2 display  EU4 name == EU5 location display name (any language file)
  3 node     EU4 name == EU5 province/area/region display name -> all its locations
"""
import re, sys, unicodedata
from collections import defaultdict
from pathlib import Path
from paths import EU4_GAME, EU5_GAME, EU5_MAP, MOD

L5 = EU5_GAME / "main_menu/localization/english"


TR = str.maketrans({"æ": "ae", "Æ": "ae", "ø": "o", "Ø": "o", "ß": "ss", "ð": "d", "þ": "th", "ł": "l", "Ł": "l", "œ": "oe", "ö": "o", "ä": "a", "å": "a"})


def norm(s):
    s = s.translate(TR)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def yml(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r'\s*([\w.\-]+):\d*\s+"(.*)"', line)
        if m:
            out[m[1]] = m[2]
    return out


def eu5_tree():
    """-> (node name -> [locations], node name -> level, all locations, loc -> path)"""
    text = (EU5_MAP / "definitions.txt").read_text(encoding="utf-8-sig")
    text = re.sub(r"#.*", "", text)
    stack, nodes, level, locs, path = [], defaultdict(set), {}, set(), {}
    for tok in re.finditer(r"([\w']+)\s*=\s*\{|\}|([\w']+)", text):
        if tok.group(1):
            stack.append(tok.group(1))
        elif tok.group(0) == "}":
            stack.pop()
        else:
            loc = tok.group(2)
            locs.add(loc)
            path[loc] = tuple(stack)
            for i, n in enumerate(stack):
                nodes[n].add(loc)
                level[n] = i
    return nodes, level, locs, path


def eu4_provinces():
    prov = {}
    for f in sorted((EU4_GAME / "history/provinces").iterdir()):
        m = re.match(r"(\d+)\s*-?\s*(.*)\.txt", f.name, re.I)
        if m:
            prov[int(m[1])] = [m[2].strip()]
    loc = yml(EU4_GAME / "localisation/prov_names_l_english.yml")
    for k, v in loc.items():
        m = re.match(r"PROV(\d+)$", k)
        if m and int(m[1]) in prov and v not in prov[int(m[1])]:
            prov[int(m[1])].append(v)
    return prov


def land_provinces():
    t = (EU4_GAME / "map/default.map").read_text(encoding="latin-1")
    t = re.sub(r"#.*", "", t)
    bad = set()
    for key in ("sea_starts", "lakes", "impassable", "force_coastal"):
        if key == "force_coastal":
            continue
        for m in re.finditer(key + r"\s*=\s*\{([^}]*)\}", t):
            bad |= {int(x) for x in re.findall(r"\d+", m[1])}
    return {p for p in eu4_provinces() if p not in bad}


def eu4_geo():
    ta = re.sub(r"#.*", "", (EU4_GAME / "map/area.txt").read_text(encoding="latin-1"))
    area = {}
    for m in re.finditer(r"^(\w+)\s*=\s*\{([^}]*)\}", ta, re.M):
        for p in re.findall(r"\b\d+\b", m[2]):
            area[int(p)] = m[1]
    tr = re.sub(r"#.*", "", (EU4_GAME / "map/region.txt").read_text(encoding="latin-1"))
    reg = {}
    for m in re.finditer(r"^(\w+_region)\s*=\s*\{\s*areas\s*=\s*\{([^}]*)\}", tr, re.M):
        for a in m[2].split():
            reg[a] = m[1]
    return area, reg


def main():
    nodes, level, locs, path = eu5_tree()
    disp = defaultdict(set)  # normalised display name -> location keys
    for f in sorted((L5 / "location_names").glob("*_l_english.yml")):
        for k, v in yml(f).items():
            if k in locs:
                disp[norm(v)].add(k)
    for k in locs:
        disp[norm(k)].add(k)
    nodedisp = defaultdict(set)
    for f in ("province_names", "area", "region_names"):
        for k, v in yml(L5 / f"{f}_l_english.yml").items():
            n = re.sub(r"_(province|area|region)$", "", k)
            for cand in (k, n):
                if cand in nodes:
                    nodedisp[norm(v)].add(cand)
    for n in nodes:
        nodedisp[norm(re.sub(r"_(province|area|region)$", "", n))].add(n)

    prov = eu4_provinces()
    res, tiers = {}, defaultdict(int)
    for pid, names in sorted(prov.items()):
        for tier, fn in (("key/display", lambda n: disp.get(norm(n))),
                         ("node", lambda n: set().union(*[nodes[x] for x in nodedisp.get(norm(n), [])]) or None)):
            hit = next((fn(n) for n in names if fn(n)), None)
            if hit:
                res[pid] = (tier, sorted(hit))
                tiers[tier] += 1
                break
    import json
    for p, names in json.load(open(MOD / "tools/data/aliases.json")).items():
        if p.startswith("_"):
            continue
        hit = set()
        for n in names:
            hit |= nodes[n] if n in nodes else {n}
        res[int(p)] = ("alias", sorted(hit))
        tiers["alias"] += 1
    land = land_provinces()
    prov = {p: n for p, n in prov.items() if p in land}
    res = {p: v for p, v in res.items() if p in land}
    area, reg = eu4_geo()
    # region compatibility: EU4 region -> EU5 level-1 regions holding >=8% of its matches
    votes = defaultdict(lambda: defaultdict(int))
    top = lambda l: path[l][1] if len(path[l]) > 1 else path[l][0]
    for p, (t, l) in res.items():
        votes[reg.get(area.get(p))][top(l[0])] += 1
    ok = {r: {k for k, v in c.items() if v >= 0.08 * sum(c.values())} for r, c in votes.items()}
    dropped = [p for p, (t, l) in res.items() if top(l[0]) not in ok[reg.get(area.get(p))]]
    for p in dropped:
        del res[p]
    # area-node: EU4 area whose localised name equals an EU5 area/province name
    a4name = {k: v for k, v in yml(EU4_GAME / "localisation/areas_regions_l_english.yml").items() if k.endswith("_area")}
    used = {x for _, l in res.values() for x in l}
    for p in prov:
        if p in res:
            continue
        a = area.get(p)
        nm = norm(a4name.get(a, a.replace("_area", "") if a else ""))
        cands = nodedisp.get(nm)
        if cands:
            node = sorted(cands, key=lambda n: level.get(n, 9))[0]
            pool = sorted(nodes[node] - used) or sorted(nodes[node])
            res[p] = ("area-node", pool)
            tiers["area-node"] += 1
    # fallback: unmatched province inherits the dominant EU5 area of its EU4 area
    used = {x for _, l in res.values() for x in l}
    areavote = defaultdict(lambda: defaultdict(int))
    for p, (t, l) in res.items():
        a5 = next((n for n in path[l[0]] if n.endswith("_area")), None)
        areavote[area.get(p)][a5] += 1
    for p in prov:
        if p in res:
            continue
        v = areavote.get(area.get(p))
        if v and max(v.values()) >= 2 and max(v.values()) >= 0.6 * sum(v.values()):
            a5 = max(v, key=v.get)
            pool = sorted(nodes[a5] - used) or sorted(nodes[a5])
            res[p] = ("area-fallback", pool)
            tiers["area-fallback"] += 1
    print(f"{len(res)}/{len(prov)} land provinces matched; dropped {len(dropped)} region-incompatible", dict(tiers))
    out = MOD / "tools/data"
    out.mkdir(exist_ok=True)
    import json
    json.dump({str(p): {"tier": t, "locations": l} for p, (t, l) in sorted(res.items())}, open(out / "loc2prov.json", "w"), indent=0)
    unmatched = [(p, prov[p]) for p in prov if p not in res]
    json.dump(unmatched, open(out / "loc2prov_unmatched.json", "w"), indent=0)
    return prov, res, locs


if __name__ == "__main__":
    prov, res, locs = main()
    if len(sys.argv) > 1:
        for p, n in prov.items():
            if p not in res:
                print(p, n)
