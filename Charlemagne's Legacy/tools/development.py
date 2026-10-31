#!/usr/bin/env python3
"""867 development of every owned province, from CK3's counties.

The base game's province files carry 1444 development. For 867 each province's development is rebuilt from the
CK3 county it is paired with (provfaiths.PROVINCE_COUNTY):

  1. the county's score at 867.1.1 = its baronies' holdings (city 3, castle 2, temple citadel 2, church 1.5,
     tribal/nomad/herder 1, no holding 0.3) + 0.6 per building + 3 per landmark (special building or its slot);
  2. a province paired with a county shares that score with every other province paired with it;
  3. a province's share of its region is 70% its CK3 score and 30% its 1444 development (VANILLA_WEIGHT: CK3 counts
     baronies, not the size of the city); a region's total is the base game's total for its provinces times REGION_RATIO (the 867 world was smaller
     than the 1444 one: Europe about half, the Middle East and Asia close to it), spread over its provinces in
     proportion to their scores (a province with no CK3 score keeps its 1444 value times the ratio);
  4. a province gets at least MIN_DEV and at most MAX_DEV, and keeps its 1444 split between tax, production and
     manpower (each at least 1).

    python3 tools/development.py            # per-region totals before/after and Europe's extremes
    python3 tools/development.py PID...     # the working for these provinces
"""
import os
import re
import sys
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import CK3_GAME, EU4_GAME  # noqa: E402

HOLDING = {"city_holding": 3.0, "castle_holding": 2.0, "temple_citadel_holding": 2.0, "church_holding": 1.5,
           "tribal_holding": 1.0, "nomad_holding": 1.0, "herder_holding": 1.0, "none": 0.3}
BUILDING, SPECIAL = 0.6, 3.0
MIN_DEV, MAX_DEV = 3, 40
# how much of a province's share of its region comes from its 1444 development (CK3 counts baronies, not the size of
# the city: Constantinople is one barony), the rest from the CK3 score
VANILLA_WEIGHT = 0.3
# CK3 counts baronies, not city size, and models Asia and Africa thinly: there the 1444 value (which does know the big cities) counts for more
REGION_VANILLA_WEIGHT = {"europe": 0.4, "anatolia": 0.5, "middle_east": 0.6, "steppe": 0.4, "india": 0.7, "east_asia": 0.7,
                         "southeast_asia": 0.6, "africa": 0.5}

# EU4 regions -> group; ratio of 867 development to the base game's 1444 development, per group
GROUP = {}
for r in ("france_region scandinavia_region low_countries_region italy_region north_german_region "
          "south_german_region russia_region iberia_region british_isles_region baltic_region poland_region "
          "ruthenia_region balkan_region carpathia_region crimea_region").split():
    GROUP[r] = "europe"
for r in "anatolia_region caucasia_region".split():
    GROUP[r] = "anatolia"
for r in "egypt_region maghreb_region mashriq_region arabia_region persia_region khorasan_region".split():
    GROUP[r] = "middle_east"
for r in ("central_asia_region ural_region west_siberia_region east_siberia_region mongolia_region "
          "manchuria_region tibet_region").split():
    GROUP[r] = "steppe"
for r in "hindusthan_region bengal_region west_india_region deccan_region coromandel_region".split():
    GROUP[r] = "india"
for r in "south_china_region xinan_region north_china_region korea_region japan_region".split():
    GROUP[r] = "east_asia"
for r in "burma_region indo_china_region malaya_region moluccas_region indonesia_region oceanea_region".split():
    GROUP[r] = "southeast_asia"
for r in ("niger_region guinea_region sahel_region horn_of_africa_region east_africa_region central_africa_region "
          "kongo_region south_africa_region").split():
    GROUP[r] = "africa"
REGION_RATIO = {"europe": 0.5, "anatolia": 0.7, "middle_east": 0.9, "steppe": 0.7, "india": 0.9, "east_asia": 0.9,
                "southeast_asia": 0.8, "africa": 0.75}


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _blocks(text):
    """[(key, body)] for the top-level `key = { ... }` blocks of a Clausewitz text."""
    out, i, n = [], 0, len(text)
    for m in re.finditer(r"(?m)^([^\s={}#]+)\s*=\s*\{", text):
        if m.start() < i:
            continue
        d, j = 1, m.end()
        while j < n and d:
            d += (text[j] == "{") - (text[j] == "}")
            j += 1
        out.append((m.group(1), text[m.end():j - 1]))
        i = j
    return out


@lru_cache(maxsize=1)
def barony_provinces():
    """{county: [CK3 province ids of its baronies]} from common/landed_titles."""
    out = {}
    root = os.path.join(CK3_GAME, "common", "landed_titles")
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".txt"):
            continue
        t = _strip(open(os.path.join(root, fn), encoding="utf-8-sig", errors="replace").read())
        stack = []
        for m in re.finditer(r"([\w\-.:]+)\s*=\s*\{|\{|\}|\bprovince\s*=\s*(\d+)", t):
            g = m.group(0)
            if g.endswith("{"):
                stack.append(m.group(1) if m.group(1) else "")
            elif g == "}":
                if stack:
                    stack.pop()
            elif m.group(2):
                ts = [s for s in stack if re.match(r"[bcdkeh]_", s)]
                if ts and ts[-1][0] == "b":
                    cs = [s for s in ts if s[0] == "c"]
                    if cs:
                        out.setdefault(cs[-1], []).append(int(m.group(2)))
    return out


def _date(s):
    y, mo, d = (int(x) for x in s.split("."))
    return (y, mo, d)


@lru_cache(maxsize=1)
def province_state():
    """{CK3 province id: (holding, building count, special building)} at 867.1.1."""
    out = {}
    root = os.path.join(CK3_GAME, "history", "provinces")
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".txt"):
            continue
        t = _strip(open(os.path.join(root, fn), encoding="utf-8-sig", errors="replace").read())
        for key, body in _blocks(t):
            if not key.isdigit():
                continue
            holding, hdate = None, (0, 0, 0)
            nb, bdate, special = 0, (0, 0, 0), 0
            # undated lines at the top level
            top = re.sub(r"(?ms)^\s*\d+\.\d+\.\d+\s*=\s*\{.*?^\s*\}", "", body)
            m = re.search(r"\bholding\s*=\s*(\w+)", top)
            if m:
                holding = m.group(1)
            if re.search(r"\bspecial_building(?:_slot)?\s*=\s*\w+", top):
                special = 1
            for dk, db in _blocks(body):
                if not re.fullmatch(r"\d+\.\d+\.\d+", dk) or _date(dk) > (867, 1, 1):
                    continue
                dd = _date(dk)
                m = re.search(r"\bholding\s*=\s*(\w+)", db)
                if m and dd >= hdate:
                    holding, hdate = m.group(1), dd
                bm = re.search(r"buildings\s*=\s*\{([^}]*)\}", db)
                if bm and dd >= bdate:
                    nb, bdate = len(bm.group(1).split()), dd
                if re.search(r"\bspecial_building(?:_slot)?\s*=\s*\w+", db):
                    special = 1  # a landmark site (Hagia Sophia, the Tower of London): its slot or building
            out[int(key)] = (holding or "none", nb, special)
    return out


@lru_cache(maxsize=1)
def county_scores():
    """{county: score at 867}."""
    st = province_state()
    out = {}
    for county, pids in barony_provinces().items():
        s = 0.0
        for p in pids:
            h, nb, sp = st.get(p, ("none", 0, 0))
            s += HOLDING.get(h, 0.5) + BUILDING * nb + SPECIAL * sp
        out[county] = s
    return out


@lru_cache(maxsize=1)
def province_region():
    """{EU4 province id: group} from the base game's areas and regions."""
    def mapfile(name):  # the mod's own copy (its areas and regions) wins over the base game's
        mine = os.path.join(HERE, "..", "map", name)
        return mine if os.path.exists(mine) else os.path.join(EU4_GAME, "map", name)

    def top_blocks(text, suffix):
        text = re.sub(r"#[^\n]*", "", text)
        out2, pos = {}, 0
        for m in re.finditer(r"(?m)^\s*(\w+%s) = \{" % suffix, text):
            if m.start() < pos:
                continue
            d, j = 1, m.end()
            while j < len(text) and d:
                d += (text[j] == "{") - (text[j] == "}")
                j += 1
            out2[m.group(1)] = text[m.end():j - 1]
            pos = j
        return out2

    areas = {}
    for name, body in top_blocks(open(mapfile("area.txt"), encoding="latin-1").read(), "").items():
        body = re.sub(r"color = \{[^}]*\}", "", body)
        areas[name] = [int(x) for x in re.findall(r"\b\d+\b", body)]
    out = {}
    for name, body in top_blocks(open(mapfile("region.txt"), encoding="latin-1").read(), "").items():
        g = GROUP.get(name)
        m = re.search(r"areas = \{(.*?)\}", body, re.S)
        if g and m:
            for ar in re.findall(r"[A-Za-z_]\w*", m.group(1)):
                for p in areas.get(ar, []):
                    out.setdefault(p, g)
    return out


def vanilla_dev(pid):
    """(tax, production, manpower) of the base game's province file, or None."""
    from steps.provdata import vanilla_prov_file

    f = vanilla_prov_file(pid)
    if not f:
        return None
    t = open(f, encoding="utf-8", errors="replace").read()
    t = re.sub(r"(?ms)^\d+\.\d+\.\d+\s*=\s*\{.*", "", t)  # undated head only

    def g(k):
        m = re.search(rf"(?m)^{k}\s*=\s*(\d+)", t)
        return int(m.group(1)) if m else None

    v = (g("base_tax"), g("base_production"), g("base_manpower"))
    return v if None not in v else None


def _split(total, vanilla):
    """total split over tax/production/manpower in the base game's proportions, each at least 1."""
    w = [max(1, x) for x in vanilla]
    s = sum(w)
    raw = [total * x / s for x in w]
    out = [max(1, int(x)) for x in raw]
    order = sorted(range(3), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    k = 0
    while sum(out) < total:
        out[order[k % 3]] += 1
        k += 1
    while sum(out) > total:
        i = max(range(3), key=lambda j: out[j])
        if out[i] <= 1:
            break
        out[i] -= 1
    return tuple(out)


@lru_cache(maxsize=1)
def compute(pids=None):
    """{pid: (tax, production, manpower, working)} for every owned province."""
    import provfaiths as pf
    from tagdb import PROVINCE_OWNERS

    owned = sorted(PROVINCE_OWNERS) if pids is None else sorted(pids)
    cs = county_scores()
    paired = {}
    for p in owned:
        paired.setdefault(pf.PROVINCE_COUNTY.get(p), []).append(p)
    score = {}
    for county, ps in paired.items():
        for p in ps:
            score[p] = cs.get(county, 0.0) / len(ps)
    region = province_region()
    groups = {}
    for p in owned:
        groups.setdefault(region.get(p), []).append(p)
    out = {}
    for g, ps in groups.items():
        van = {p: vanilla_dev(p) for p in ps}
        ratio = REGION_RATIO.get(g)
        if ratio is None:  # outside the groups (the New World): the base game's value stays
            for p in ps:
                if van[p]:
                    out[p] = (*van[p], "unchanged (no region group)")
            continue
        base_total = sum(sum(v) for v in van.values() if v)
        target = base_total * ratio
        scored = [p for p in ps if score.get(p, 0) > 0 and van[p]]
        ssum = sum(score[p] for p in scored) or 1.0
        vsum = sum(sum(van[p]) for p in scored) or 1.0
        spread = target - sum(sum(van[p]) * ratio for p in ps if p not in scored and van[p])
        vw = REGION_VANILLA_WEIGHT.get(g, VANILLA_WEIGHT)
        for p in ps:
            if not van[p]:
                continue
            if p in scored:
                share = (1 - vw) * score[p] / ssum + vw * sum(van[p]) / vsum
                dev = spread * share
                how = f"score {score[p]:.1f} of {ssum:.0f}, 1444 {sum(van[p])} of {vsum}, x {spread:.0f}"
            else:
                dev = sum(van[p]) * ratio
                how = f"no CK3 score: 1444 value {sum(van[p])} x {ratio}"
            total = max(MIN_DEV, min(MAX_DEV, round(dev)))
            out[p] = (*_split(total, van[p]), f"{g}: {how} -> {total}")
    return out


if __name__ == "__main__":
    res = compute()
    if sys.argv[1:]:
        for a in sys.argv[1:]:
            p = int(a)
            print(p, res.get(p), vanilla_dev(p))
        sys.exit()
    region = province_region()
    by = {}
    for p, (t, pr, m, _w) in res.items():
        g = region.get(p, "other")
        v = vanilla_dev(p)
        a = by.setdefault(g, [0, 0, 0])
        a[0] += 1
        a[1] += sum(v) if v else 0
        a[2] += t + pr + m
    for g, (n, before, after) in sorted(by.items()):
        print(f"{g:15} {n:4} provinces  1444 total {before:6}  867 total {after:6}  (avg {before / n:.1f} -> {after / n:.1f})")
