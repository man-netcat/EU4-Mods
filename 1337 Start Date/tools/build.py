#!/usr/bin/env python3
"""Regenerate history/ (provinces, countries), new-tag registration and diplomacy stubs from EU5's 1337 setup.

Never hand-edit generated output: change data/*.json or this code and rebuild.
"""
import json, re, shutil, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import chars, eu5info
from eu5setup import countries
from loc2prov import eu4_geo, land_provinces
from paths import EU4_GAME, MOD
from pdx import get, getall
from tagmap import build_table, province_owners, eu4_tags

DATA = MOD / "tools/data"
VAN = EU4_GAME / "history"
BACKSTORY_END = (1444, 11, 11)
OWN_KEYS = r"(?:owner|controller|add_core|remove_core|add_claim|remove_claim|add_permanent_claim|remove_permanent_claim)"
# 1444 owners whose land belonged to a different state in 1337 (used only for provinces EU5 could not be mapped to)
VANILLA_PROXY = {"MNG": "YUA", "KHA": "YUA", "KRC": "YUA", "NHX": "YUA", "SOL": "YUA", "MYR": "YUA", "MJZ": "YUA",
                 "EJZ": "YUA", "NVK": "YUA", "SHY": "GLH"}
DATED = re.compile(r"^(\d{1,4})\.(\d{1,2})\.(\d{1,2})\s*=\s*\{", re.M)


def ascii_(s):
    s = s.translate(str.maketrans({"ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ə": "e", "ʻ": "'", "’": "'", "ʼ": "'"}))
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def latin1(s):
    """keep Latin-1 letters, flatten everything else"""
    return "".join(c if ord(c) < 256 else (ascii_(c) or "") for c in s)


def split_blocks(text):
    """-> (base_text, [(date, block_text)]) splitting at depth-0 dated entries."""
    out, pos, base_end = [], 0, None
    depth = 0
    starts = []
    i = 0
    n = len(text)
    line_start = True
    while i < n:
        ch = text[i]
        if ch == "#":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if depth == 0 and (i == 0 or text[i - 1] == "\n"):
            m = DATED.match(text, i)
            if m:
                starts.append((i, (int(m[1]), int(m[2]), int(m[3]))))
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        i += 1
    if not starts:
        return text, []
    base = text[:starts[0][0]]
    blocks = []
    for k, (s, d) in enumerate(starts):
        e = starts[k + 1][0] if k + 1 < len(starts) else n
        blocks.append((d, text[s:e]))
    return base, blocks


def strip_depth0(base, pattern):
    """remove depth-0 statements matching pattern, whole `key = { ... }` blocks included"""
    out, depth, skip = [], 0, False
    for line in base.split("\n"):
        code = line.split("#")[0]
        delta = code.count("{") - code.count("}")
        if skip:
            depth += delta
            skip = depth > 0
            continue
        if depth == 0 and re.match(pattern, code):
            if delta > 0:
                depth, skip = delta, True
            continue
        depth = max(0, depth + delta)
        out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------- provinces

def clean_dated(blocks, own_only=True):
    kept = []
    for d, b in blocks:
        b2 = re.sub(rf"\b{OWN_KEYS}\s*=\s*\w+", "", b)
        body = re.sub(r"^\d+\.\d+\.\d+\s*=\s*\{|\}|#[^\n]*|\s", "", b2)
        if body:
            kept.append(b2)
    return kept


def hre_members(table):
    """(members, emperor, electors) as EU4 tags, from EU5's Holy Roman Empire organisation."""
    from paths import EU5_SETUP
    t = (EU5_SETUP / "15_international_organizations.txt").read_text(encoding="utf-8-sig")
    m = re.search(r"type\s*=\s*hre\b.*?members\s*=\s*\{([^}]*)\}.*?leader\s*=\s*(\w+)", t, re.S)
    mem = set(m[1].split())
    electors = set()
    for key in ("elector", "archbishop_elector"):
        e = re.search(key + r"\s*=\s*\{([^}]*)\}", t[m.start():])
        if e:
            electors |= set(re.sub(r"#[^\n]*", "", e[1]).split())
    return ({table[x]["eu4"] for x in mem if x in table}, table.get(m[2], {}).get("eu4"),
            {table[x]["eu4"] for x in electors if x in table})


def development_targets(land, cr_vote, lp):
    """EU4 province -> total development from EU5 population. Only provinces whose locations were matched
    by name (not the area fallbacks, which share locations) take part; their pops are ranked and given
    the sorted vanilla totals of the same provinces, so the world's development distribution stays
    vanilla's while who holds it follows 1337's population (Western Europe at its pre-plague peak).
    A floor of half the vanilla total keeps lone city locations from collapsing."""
    pops, vanilla = {}, {}
    files = {int(re.match(r"\d+", f.name)[0]): f for f in (VAN / "provinces").iterdir()}
    for pid in land:
        v = cr_vote.get(str(pid))
        if not v or v["tier"] in ("area-fallback", "area-node"):
            continue
        pop = sum(lp[l]["pop"] for l in v["locations"] if l in lp)
        f = files.get(pid)
        if not pop or f is None:
            continue
        top = split_blocks(f.read_text(encoding="latin-1"))[0]
        vals = [int(m[1]) for m in re.finditer(r"(?m)^base_(?:tax|production|manpower)\s*=\s*(\d+)", top)]
        if len(vals) == 3:
            pops[pid], vanilla[pid] = pop, sum(vals)
    ranked = sorted(pops, key=lambda p: (pops[p], p))
    totals = sorted(vanilla.values())
    # a province never falls below half its vanilla development: EU5's pops are per location, so a lone city
    # location (London, Cologne) can rank below a province that sums several rural ones
    return {p: max(t, -(-vanilla[p] // 2)) for p, t in zip(ranked, totals)}


def scale_development(base, total):
    """Rewrite base_tax/base_production/base_manpower to sum to `total`, keeping their vanilla proportions
    (each at least 1)."""
    keys = ("base_tax", "base_production", "base_manpower")
    old = [int(re.search(rf"(?m)^{k}\s*=\s*(\d+)", base)[1]) for k in keys]
    total = max(total, 3)
    raw = [o / sum(old) * total for o in old]
    new = [max(1, int(r)) for r in raw]
    while sum(new) < total:
        i = max(range(3), key=lambda j: (raw[j] - new[j], -j))
        new[i] += 1
    while sum(new) > total:
        i = max((j for j in range(3) if new[j] > 1), key=lambda j: (new[j] - raw[j], -j))
        new[i] -= 1
    for k, n in zip(keys, new):
        base = re.sub(rf"(?m)^({k}\s*=\s*)\d+", rf"\g<1>{n}", base, count=1)
    return base


# EU5 raw material -> (EU4 trade good, weight). Rare goods weigh more so a single silk or gem location wins over
# several wheat ones; lumber and game are everywhere and weigh less. Materials with no EU4 good are absent
# (a province with only those keeps its vanilla trade good).
GOODS = {}
for _good, _w, _raws in (
    ("grain", 0.8, "wheat millet legumes rice maize potato fruit olives"),
    ("livestock", 1, "livestock horses camels"), ("fish", 1, "fish"), ("wool", 1.5, "wool"),
    ("fur", 2, "fur"), ("fur", 0.5, "wild_game"), ("naval_supplies", 0.5, "lumber"),
    ("cloth", 1.5, "fiber_crops"), ("cotton", 2, "cotton"), ("silk", 4, "silk"), ("wine", 2, "wine"),
    ("salt", 2, "salt"), ("iron", 2, "iron"), ("copper", 2, "copper tin lead"), ("coal", 2, "coal"),
    ("gold", 4, "goods_gold silver"), ("gems", 3, "gems pearls amber"), ("ivory", 4, "ivory elephants"),
    ("dyes", 3, "dyes alum"), ("tea", 4, "tea"), ("coffee", 4, "coffee"), ("cocoa", 4, "cocoa"),
    ("sugar", 3, "sugar"), ("tobacco", 3, "tobacco"), ("spices", 4, "pepper chili saffron"),
    ("cloves", 4, "cloves"), ("incense", 4, "incense"), ("glass", 1.5, "sand"),
):
    for _r in _raws.split():
        GOODS[_r] = (_good, _w)
FORT_BUILDINGS = {"castle", "city_walls", "yamashiro", "order_stronghold", "nobility_fortifications", "dun_fort",
                  "qalat_al_mashwar", "theodosian_walls", "the_bock_fortifications"}
SHIP_BUILDINGS = {"wharf", "dock", "clan_shipyards", "hanseatic_shipwright_guild", "venetian_arsenal",
                  "barcelona_royal_shipyard", "royal_atarazanas_seville", "galley_barracks", "porto_pisano"}


def eu5_economy():
    """-> (raw material per EU5 location, locations with a fort building, with a shipyard, market towns)."""
    from paths import EU5_GAME, EU5_SETUP
    raw = {}
    for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{[^}\n]*?raw_material\s*=\s*(\w+)",
                         (EU5_GAME / "in_game/map_data/location_templates.txt").read_text(encoding="utf-8-sig")):
        raw[m[1]] = m[2]
    forts, ships = set(), set()
    t = (EU5_SETUP / "07_cities_and_buildings.txt").read_text(encoding="utf-8-sig")
    for m in re.finditer(r"(?m)^\s*(\w+)\s*=\s*\{[^}\n]*?location\s*=\s*(\w+)", t):
        if m[1] in FORT_BUILDINGS:
            forts.add(m[2])
        elif m[1] in SHIP_BUILDINGS:
            ships.add(m[2])
    markets = set(re.findall(r"(?m)^\s*add_market\s*=\s*(\w+)", (EU5_SETUP / "03_markets.txt").read_text(encoding="utf-8-sig")))
    return raw, forts, ships, markets


def economy_targets(land, cr_vote):
    """EU4 province -> {trade_good, fort, shipyard, market} from the EU5 locations matched to it by name (not
    the shared area pools, which would repeat one answer over several provinces)."""
    raw, forts, ships, markets = eu5_economy()
    pools = Counter(tuple(sorted(v["locations"])) for v in cr_vote.values())
    out = {}
    for pid in land:
        v = cr_vote.get(str(pid))
        if not v or v["tier"] in ("area-fallback", "area-node") or pools[tuple(sorted(v["locations"]))] > 1:
            continue
        locs = v["locations"]
        score = Counter()
        for l in locs:
            if l in raw and raw[l] in GOODS:
                good, w = GOODS[raw[l]]
                score[good] += w
        out[pid] = dict(good=max(score, key=lambda g: (score[g], g)) if score else None,
                        fort=any(l in forts for l in locs), ship=any(l in ships for l in locs),
                        market=any(l in markets for l in locs))
    return out


def apply_economy(base, e):
    if e["good"]:
        base = re.sub(r"(?m)^trade_goods\s*=\s*\w+", f"trade_goods = {e['good']}", base, count=1)
    base = re.sub(r"(?m)^(fort_1[5-8]th|shipyard)\s*=\s*\w+[^\n]*\n", "", base)
    add = (["fort_15th = yes"] if e["fort"] else []) + (["shipyard = yes"] if e["ship"] else [])
    if e["market"] and not re.search(r"(?m)^center_of_trade\s*=", base):
        add.append("center_of_trade = 1")
    return base.rstrip("\n") + "\n" + "\n".join(add) + ("\n" if add else "")


def step_provinces(table, po, cmap, rmap, stats, hre_members=None):
    reused_codes = {r["eu4"] for r in table.values()}
    out = MOD / "history/provinces"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    land = land_provinces()
    cr_vote = json.load(open(DATA / "loc2prov.json"))
    from popdata import location_pops
    lp = location_pops()
    dev = development_targets(land, cr_vote, lp)
    stats["developed"] = len(dev)
    econ = economy_targets(land, cr_vote)
    stats["economy"] = len(econ)
    for f in sorted((VAN / "provinces").iterdir()):
        m = re.match(r"(\d+)", f.name)
        pid = int(m[1])
        text = f.read_text(encoding="latin-1")
        base, blocks = split_blocks(text)
        base = strip_depth0(base, rf"\s*(?:{OWN_KEYS}|is_city|seat_in_parliament)\s*=")
        info = po.get(pid)
        new = []
        if info and pid in land:
            ow = info["owner"]
            if ow and ow in table:
                tag = table[ow]["eu4"]
                new += [f"owner = {tag}"]
                ct = info["controller"]
                new += [f"controller = {table[ct]['eu4'] if ct in table else tag}"]
                cores = {table[t]["eu4"] for t in info["cores"] if t in table} | {tag}
                new += [f"add_core = {c}" for c in sorted(cores)]
                new += ["is_city = yes"]
                stats["owned"] += 1
            else:
                stats["unowned"] += 1
            if pid in dev:
                base = scale_development(base, dev[pid])
            if pid in econ:
                base = apply_economy(base, econ[pid])
            if info["tier"] != "area-fallback":
                cul, rel = Counter(), Counter()
                for l in cr_vote[str(pid)]["locations"]:
                    if l in lp:
                        cul += lp[l]["cul"]
                        rel += lp[l]["rel"]
                if cul:
                    c4 = cmap.get(max(cul, key=lambda k: (cul[k], k)))
                    r4 = rmap.get(max(rel, key=lambda k: (rel[k], k)))
                    if c4:
                        base = re.sub(r"(?m)^culture\s*=\s*\w+", f"culture = {c4}", base)
                    if r4:
                        base = re.sub(r"(?m)^religion\s*=\s*\w+", f"religion = {r4}", base)
        else:
            stats["vanilla_kept"] += 1
            # keep vanilla ownership for provinces we could not map
            vtext = text
            ow = re.search(r"(?m)^owner\s*=\s*(\w+)", split_blocks(vtext)[0])
            vo = ow and VANILLA_PROXY.get(ow[1], ow[1])
            if vo and vo in reused_codes:
                new += [f"owner = {vo}", f"controller = {vo}", f"add_core = {vo}", "is_city = yes"]
        if hre_members is not None and info and pid in land:
            own_m = re.search(r"(?m)^owner = (\w+)", "\n".join(new))
            flag = "yes" if own_m and own_m[1] in hre_members else "no"
            if re.search(r"(?m)^hre\s*=", base):
                base = re.sub(r"(?m)^hre\s*=\s*\w+", f"hre = {flag}", base)
            else:
                new.append(f"hre = {flag}")
        # inject after the leading comment lines
        lines = base.split("\n")
        k = 0
        while k < len(lines) and (lines[k].startswith("#") or not lines[k].strip()):
            k += 1
        base = "\n".join(lines[:k] + new + lines[k:])
        res = base.rstrip("\n") + "\n\n" + "".join(clean_dated(blocks))
        (out / f.name).write_bytes(res.rstrip("\n").encode("latin-1", "replace") + b"\n")


# ---------------------------------------------------------------- countries

def culture_gfx():
    from pdx import parse
    t = parse((EU4_GAME / "common/cultures/00_cultures.txt").read_text(encoding="latin-1"))
    gfx, cul = {}, {}
    for grp, b in t:
        if isinstance(b, list):
            g = get(b, "graphical_culture") or "westerngfx"
            for k, v in b:
                if isinstance(v, list) and k not in ("dynasty_names", "male_names", "female_names"):
                    cul[k] = g
    return cul


def vanilla_country(tag):
    for f in sorted((VAN / "countries").iterdir()):
        if f.name.startswith(tag + " -"):
            return f
    return None


def tech_by_area():
    area, reg = eu4_geo()
    vote = defaultdict(Counter)
    vtech = {}
    for f in sorted((VAN / "countries").iterdir()):
        t = f.name[:3]
        m = re.search(r"(?m)^technology_group\s*=\s*(\w+)", f.read_text(encoding="latin-1"))
        if m:
            vtech[t] = m[1]
    for f in sorted((VAN / "provinces").iterdir()):
        pid = int(re.match(r"(\d+)", f.name)[1])
        ow = re.search(r"(?m)^owner\s*=\s*(\w+)", split_blocks(f.read_text(encoding="latin-1"))[0])
        if ow and ow[1] in vtech:
            vote[area.get(pid)][vtech[ow[1]]] += 1
            vote[reg.get(area.get(pid))][vtech[ow[1]]] += 1
    return vote, area, reg, vtech


GOV_DEFAULT = {
    "monarchy": ("monarchy", "feudalism_reform"),
    "republic": ("republic", "plutocratic_reform"),
    "theocracy": ("theocracy", "leading_clergy_reform"),
    "tribe": ("tribal", "tribal_despotism"),
    "horde": ("tribal", "steppe_horde"),
}
NATIVE_TECH = {"north_american", "mesoamerican", "andean", "south_american", "aboriginal_tech", "polynesian_tech"}
RANK = {"rank_county": 1, "rank_duchy": 1, "rank_kingdom": 2, "rank_empire": 3}


def ruler_text(tag, b, gov, table, stats):
    """monarch / heir / queen blocks for an EU5 country block `b` (empty when EU5 leaves the ruler random)."""
    rid, hid = chars.country_rulers(b) if b else (None, None)
    ch = chars.characters().get(rid) if rid else None
    mb = chars.block(rid, ch, chars.ruler_regnal(rid, b)) if ch and b else None
    if not mb:
        return "", False
    out = "\nmonarch = {\n" + mb + "\n}\n"
    hch = chars.characters().get(hid) if hid else None
    hb = chars.block(hid, hch, heir=True) if hch else None
    if hb:
        out += "heir = {\n" + hb + "\n}\n"
        stats["heirs"] += 1
    qb = chars.queen_block(rid, tag, lambda t: (table.get(t) or {}).get("eu4")) if gov != "republic" else None
    if qb:
        out += "queen = {\n" + qb + "\n}\n"
        stats["queens"] += 1
        origin = re.search(r"country = (\w+)", qb)[1]
        if origin != tag:
            MARRIAGES.add(tuple(sorted((tag, origin))))
    return out, True


def step_countries(table, po, cmap, rmap, stats):
    out = MOD / "history/countries"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    info = eu5info.info()
    cdefs = eu5info.country_defs()
    cdict = dict(countries())
    # EU5 location -> EU4 province (prefer non-fallback)
    l2p = {}
    for pid, v in json.load(open(DATA / "loc2prov.json")).items():
        for l in v["locations"]:
            if l not in l2p or v["tier"] != "area-fallback":
                l2p[l] = int(pid)
    vote, area, reg, vtech = tech_by_area()
    vown = {}
    for f in sorted((VAN / "provinces").iterdir()):
        pid = int(re.match(r"(\d+)", f.name)[1])
        ow = re.search(r"(?m)^owner\s*=\s*(\w+)", split_blocks(f.read_text(encoding="latin-1"))[0])
        vown[pid] = ow[1] if ow else None
    owned_by = defaultdict(list)
    for pid, v in po.items():
        if v["owner"] in table and v["tier"] != "area-fallback" or v["owner"] in table:
            owned_by[v["owner"]].append(pid)
    reused = {r["eu4"] for r in table.values() if not r["new"]}
    prov_file = {int(re.match(r"(\d+)", f.name)[1]): f.name for f in sorted((MOD / "history/provinces").iterdir())}
    for tag5, r in table.items():
        tag, nm = r["eu4"], r["name"]
        i = info.get(tag5, {})
        b = cdict.get(tag5)
        cd = cdefs.get(tag5, {})
        cul = cmap.get(cd.get("culture")) if cd.get("culture") else None
        rel = rmap.get(cd.get("religion")) if cd.get("religion") else None
        # capital province
        cap = l2p.get(i.get("capital")) if i.get("capital") else None
        if cap and po.get(cap, {}).get("owner") != tag5:
            cap = None
        if not cap and owned_by[tag5]:
            cap = max(owned_by[tag5], key=lambda p: po[p]["pop"])
        van = vanilla_country(tag) if not r["new"] else None
        if van:
            text = van.read_text(encoding="latin-1")
            base, blocks = split_blocks(text)
            base = strip_depth0(base, r"\s*(?:monarch|heir|queen|elector|add_accepted_culture|historical_rival|historical_friend|change_estate_land_share|set_estate_privilege|add_estate_loyalty|add_estate_loyalty_modifier)\s*=")
            if cap:
                base = re.sub(r"(?m)^capital\s*=\s*\d+", f"capital = {cap}", base)
            if cul:
                base = re.sub(r"(?m)^primary_culture\s*=\s*\w+", f"primary_culture = {cul}", base)
            if rel:
                base = re.sub(r"(?m)^religion\s*=\s*\w+", f"religion = {rel}", base)
            if i.get("rank") in RANK:
                if re.search(r"(?m)^government_rank\s*=", base):
                    base = re.sub(r"(?m)^government_rank\s*=\s*\d", f"government_rank = {RANK[i['rank']]}", base)
                else:
                    base += f"\ngovernment_rank = {RANK[i['rank']]}\n"
            kept = [b_ for d, b_ in blocks if d > BACKSTORY_END]
            body = base.rstrip() + "\n"
            fname = van.name
        else:
            gov, reform = GOV_DEFAULT.get(i.get("gov", "monarchy"), GOV_DEFAULT["monarchy"])
            cored = None
            if not cap:
                cored = [p for p, v in po.items() if tag5 in v["cores"] and p in prov_file]
                if cored:
                    cap = None
                    cul_src = max(cored, key=lambda p: po[p]["pop"])
                    m_ = re.search(r"(?m)^culture\s*=\s*(\w+)", (MOD / "history/provinces" / prov_file[cul_src]).read_text(encoding="latin-1"))
                    cul = cul or (m_ and m_[1])
            area_ = area.get(cap) or (area.get(cul_src) if not cap and cored else None)
            tv = vote.get(area_) or vote.get(reg.get(area_)) or Counter({"western": 1})
            tech = max(tv, key=lambda k: (tv[k], k))
            if tech in NATIVE_TECH and gov in ("tribal",):
                gov, reform = "native", "native_clan_council_reform"
            if not cul and cap:
                m_ = re.search(r"(?m)^culture\s*=\s*(\w+)", (MOD / "history/provinces" / prov_file[cap]).read_text(encoding="latin-1"))
                cul = m_ and m_[1]
            lines = [f"government = {gov}", f"add_government_reform = {reform}",
                     f"government_rank = {RANK.get(i.get('rank'), 1)}",
                     f"technology_group = {tech}",
                     f"primary_culture = {cul or 'unknown'}",
                     f"religion = {rel or 'animism'}"]
            if cap:
                lines.append(f"capital = {cap}")
            body = "\n".join(lines) + "\n"
            kept = []
            fname = f"{tag} - {latin1(ascii_(nm))}.txt"
            stats["new_tags"] += 1
        # rulers, heirs and consorts, lifted from EU5's characters
        text, got = ruler_text(tag, b, i.get("gov"), table, stats)
        body += text
        stats["rulers" if got else "no_ruler"] += 1
        if tag in ELECTORS:
            body += "\nelector = yes\n"
        if tag == EMP[0] and "emperor = yes" not in body:
            body += "\nemperor = yes\n"
        res = body + "\n" + "".join(kept)
        (out / fname).write_bytes(res.rstrip().encode("latin-1", "replace") + b"\n")


def step_dormant(table, stats):
    """vanilla tags with no EU5 1337 counterpart that holds land keep their files (backstory entries dropped);
    where EU5 has a country of the same name (no land of ours), it lends its ruler, heir and consort."""
    from loc2prov import norm
    import tagmap
    out = MOD / "history/countries"
    used = {r["eu4"] for r in table.values()}
    n4, e4 = tagmap.eu4_names(), tagmap.eu4_tags()
    by_name = {}
    for t in sorted(e4):
        if t in n4:
            by_name.setdefault(norm(n4[t]), t)
    cdict = dict(countries())
    lent = {}
    for t5, b in cdict.items():
        cand = tagmap.ALIASES.get(t5) or by_name.get(norm(eu5info.display(t5)))
        if cand and cand not in used and cand not in lent:
            lent[cand] = b
    n = 0
    for f in sorted((VAN / "countries").iterdir()):
        if f.name[:3] in used:
            continue
        base, blocks = split_blocks(f.read_text(encoding="latin-1"))
        base = strip_depth0(base, r"\s*(?:monarch|heir|queen|elector)\s*=")
        res = base.rstrip() + "\n"
        if f.name[:3] in lent:
            text, got = ruler_text(f.name[:3], lent[f.name[:3]], None, table, stats)
            res += text
            stats["dormant_rulers"] += got
        res += "\n" + "".join(b_ for d, b_ in blocks if d > BACKSTORY_END)
        (out / f.name).write_bytes(res.rstrip().encode("latin-1", "replace") + b"\n")
        n += 1
    return n


def step_accepted(table):
    """add_accepted_culture in the country files: a culture that makes up a real share of a realm's development
    (>= 20%, or >= 10% for a culture of the ruling culture's own group) is accepted, up to three. The base game's
    1444 lists are stripped, so every tag's come from where its people actually live at the start."""
    import cultures_of
    group = cultures_of.groups()
    share = defaultdict(Counter)
    for f in (MOD / "history/provinces").iterdir():
        top = re.split(r"(?m)^\d{3,4}\.\d+\.\d+\s*=", f.read_text(encoding="latin-1"))[0]
        o, c = re.search(r"(?m)^owner = (\w+)", top), re.search(r"(?m)^culture = (\w+)", top)
        if o and c:
            d = sum(int(x) for x in re.findall(r"(?m)^base_(?:tax|production|manpower)\s*=\s*(\d+)", top))
            share[o[1]][c[1]] += d
    n = 0
    for tag, cnt in share.items():
        for f in (MOD / "history/countries").glob(f"{tag} - *.txt"):
            t = f.read_text(encoding="latin-1")
            m = re.search(r"(?m)^primary_culture = (\w+)", t)
            if not m:
                continue
            tot = sum(cnt.values()) or 1
            own = group.get(m[1])
            acc = [c for c, d in cnt.most_common()
                   if c != m[1] and (d / tot >= 0.2 or (group.get(c) == own and d / tot >= 0.1))][:3]
            if acc:
                add = "".join(f"add_accepted_culture = {c}\n" for c in acc)
                f.write_text(re.sub(r"(?m)^(primary_culture = \w+[^\n]*\n)", lambda x: x[1] + add, t, count=1), encoding="latin-1")
                n += len(acc)
    return n


def step_bookmark(table):
    """common/bookmarks/1337_start.txt: the playable roster is the tags with the most development at the start (the
    base game's bookmarks likewise list the great and mid powers), centred on the emperor-less west like the base
    game's, with the weakest-start large tags as the easy picks."""
    dev, held = Counter(), Counter()
    for f in (MOD / "history/provinces").iterdir():
        top = re.split(r"(?m)^\d{3,4}\.\d+\.\d+\s*=", f.read_text(encoding="latin-1"))[0]
        m = re.search(r"(?m)^owner = (\w+)", top)
        if m:
            held[m[1]] += 1
            dev[m[1]] += sum(int(x) for x in re.findall(r"(?m)^base_(?:tax|production|manpower)\s*=\s*(\d+)", top))
    names = {r["eu4"]: r["name"] for r in table.values()}
    subjects = set(re.findall(r"(?:vassal|dependency|union) = \{ first = \w+ second = (\w+)",
                              (MOD / "history/diplomacy/1337_diplomacy.txt").read_text(encoding="latin-1")))
    ranked = [t for t, _ in dev.most_common() if t in names and t not in subjects][:30]
    ranked += [t for t in ("BYZ", "TUR", "VEN", "GEN", "TEU", "MOS", "NOV", "GOL", "HSA", "PAP") if t in names and held[t] and t not in ranked and t not in subjects]
    easy = [t for t in ("FRA", "ENG", "CAS", "HAB", "POL", "HUN") if t in ranked][:3] or ranked[:3]
    lines = ["bookmark =", "{", '\tname = "START_1337_NAME"', '\tdesc = "START_1337_DESC"', "\tdate = 1337.4.1",
             "\tdefault = yes", "\tcenter = 236", ""]
    lines += [f"\tcountry = {t}" for t in ranked] + [""] + [f"\teasy_country = {t}" for t in easy] + ["}"]
    (MOD / "common/bookmarks/1337_start.txt").write_text("\n".join(lines) + "\n")
    return {"playable": len(ranked)}


def step_institutions():
    """common/institutions/00_Core.txt: the base game's file, its Feudalism rule wrapped so that provinces matched
    to EU5 locations follow EU5 (feudalism present where any of their locations has it at 1337, absent where none
    does; EU5 lists only locations an institution has reached) and the base game's own rule (culture, technology group, government) still decides the rest. EU5's
    other institutions (legalism, meritocracy) have no EU4 counterpart."""
    from paths import EU5_SETUP
    t5 = (EU5_SETUP / "08_institutions.txt").read_text(encoding="utf-8-sig")
    have = set(re.findall(r"(?m)^(\w+) = \{\n(?:\t[^\n]*\n)*?\tfeudalism = yes", t5))
    vote = json.load(open(DATA / "loc2prov.json"))
    pools = Counter(tuple(sorted(v["locations"])) for v in vote.values())
    yes, no = [], []
    for pid, v in sorted(vote.items(), key=lambda kv: int(kv[0])):
        if v["tier"] in ("area-fallback", "area-node") or pools[tuple(sorted(v["locations"]))] > 1:
            continue
        (yes if any(l in have for l in v["locations"]) else no).append(pid)
    src = (EU4_GAME / "common/institutions/00_Core.txt").read_text(encoding="latin-1")
    a = src.index("feudalism = {")
    h = src.index("history = {", a)
    start = src.index("\n", h) + 1
    # end of the history block: matching brace
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(src[i], 0)
        i += 1
    body = src[start:i - 1]
    year = "\t\tis_year = 1000\n"
    assert year in body, "feudalism history changed"
    rule = body.replace(year, "")
    new = (year + "\t\tOR = {\n" + "".join(f"\t\t\tprovince_id = {p}\n" for p in yes)
           + "\t\t\tAND = {\n\t\t\t\tNOT = {\n" + "".join(f"\t\t\t\t\tprovince_id = {p}\n" for p in no)
           + "\t\t\t\t}\n" + "".join("\t" + ln + "\n" if ln.strip() else "\n" for ln in rule.rstrip("\n").split("\n"))
           + "\t\t\t}\n\t\t}\n\t")
    out = MOD / "common/institutions"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    (out / "00_Core.txt").write_bytes((src[:start] + new + src[i - 1:]).encode("latin-1", "replace"))
    return {"feudalism_yes": len(yes), "feudalism_no": len(no)}


def step_tags(table):
    """register new tags: common/country_tags, common/countries, localisation"""
    gfx = culture_gfx()
    ctags = MOD / "common/country_tags"
    cdir = MOD / "common/countries"
    for d in (ctags, cdir):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    tagfile, loc = [], ["l_english:"]
    info = eu5info.info()
    import tagmap
    base_names, base_adjs = tagmap.eu4_names(), {}
    for f in sorted((EU4_GAME / "localisation").glob("*_l_english.yml")):
        for m in re.finditer(r'^\s*([A-Z0-9]{3})_ADJ:\d*\s+"(.*)"', f.read_text(encoding="utf-8-sig"), re.M):
            base_adjs[m[1]] = m[2]
    replace = ["l_english:"]
    for tag5, r in sorted(table.items(), key=lambda kv: kv[1]["eu4"]):
        if not r["new"]:
            # a base-game tag takes the name and adjective EU5 gives its state, replacing the base game's
            nm = latin1(r["name"])
            adj = latin1(eu5info.display(tag5 + "_ADJ", nm))
            if nm != base_names.get(r["eu4"]) or adj != base_adjs.get(r["eu4"]):
                replace += [f' {r["eu4"]}:0 "{nm}"', f' {r["eu4"]}_ADJ:0 "{adj}"']
            continue
        tag, nm = r["eu4"], latin1(r["name"])
        fn = f"{tag} - {ascii_(nm)}.txt".replace("/", "-")
        cname = f"{ascii_(nm)}".replace("/", "-").replace(":", "")
        col = eu5info.color_of(tag5) or (100, 100, 100)
        cd = eu5info.country_defs().get(tag5, {})
        c4 = json.load(open(DATA / "cr_map.json"))["culture"].get(cd.get("culture"))
        g = gfx.get(c4, "westerngfx")
        tagfile.append(f'{tag} = "countries/{cname}.txt"')
        (cdir / f"{cname}.txt").write_bytes(
            f"graphical_culture = {g}\n\ncolor = {{ {col[0]} {col[1]} {col[2]} }}\n".encode("latin-1"))
        adj = latin1(eu5info.display(tag5 + "_ADJ", nm))
        loc += [f' {tag}:0 "{nm}"', f' {tag}_ADJ:0 "{adj}"']
    (ctags / "1337_tags.txt").write_bytes(("\n".join(tagfile) + "\n").encode("latin-1"))
    p = MOD / "localisation/1337_countries_l_english.yml"
    p.write_text("﻿" + "\n".join(loc) + "\n", encoding="utf-8")
    r = MOD / "localisation/replace"
    shutil.rmtree(r, ignore_errors=True)
    r.mkdir(parents=True)
    (r / "1337_countries_l_english.yml").write_text("﻿" + "\n".join(replace) + "\n", encoding="utf-8")


# EU5 subject type -> (history/diplomacy key, EU4 subject type). Vassal-like EU5 types are all EU4 vassals; royal
# cadet branches and family governors are appanages, tributaries are tributary states. Hanseatic members are
# not subjects at all in EU4: they ally with their league.
SUBJECT_KIND = {
    "vassal": ("vassal", None), "fiefdom": ("vassal", None), "dominion": ("vassal", None),
    "samanta": ("vassal", None), "tusi": ("vassal", None),
    "appanage": ("dependency", "appanage"), "familial_governor": ("dependency", "appanage"),
    "tributary": ("dependency", "tributary_state"), "hanseatic_member": ("alliance", None),
}


def drop_base_game_relations_at_start(tags):
    """The base game's history/diplomacy files carry relations that were already running before 1337.4.1
    (a 1299 Hainaut-Holland alliance, ...). Where one of them involves a tag that EU5 has in a subject or union
    relation, the mod ships that file without the relation, so it cannot double up with ours."""
    start = (1337, 4, 1)
    for f in sorted((EU4_GAME / "history/diplomacy").glob("*.txt")):
        text = f.read_text(encoding="latin-1")
        kept, changed = [], False
        for m in re.finditer(r"(?ms)^(\w+) = \{.*?^\}[^\n]*\n?|[^\n]*\n", text):
            blk = m[0]
            if m[1] and m[1] != "emperor":
                sd = re.search(r"start_date\s*=\s*(\d+)\.(\d+)\.(\d+)", blk)
                ed = re.search(r"end_date\s*=\s*(\d+)\.(\d+)\.(\d+)", blk)
                two = re.findall(r"(?:first|second)\s*=\s*(\w+)", blk)
                if (sd and tuple(map(int, sd.groups())) <= start and (not ed or tuple(map(int, ed.groups())) > start)
                        and len(two) == 2 and set(two) <= tags):
                    changed = True
                    continue
            kept.append(blk)
        dst = MOD / "history/diplomacy" / f.name
        if changed:
            dst.write_text("".join(kept), encoding="latin-1")


def step_diplomacy(table):
    """history/diplomacy from 12_diplomacy. A subject of a tag that was folded into its own overlord is
    re-attached to that overlord; each subject keeps its first overlord only; no subject is also allied
    with, or guaranteed by, the overlord it already serves."""
    import tagmap
    from paths import EU5_SETUP
    from pdx import parse
    held = Counter()
    for f in sorted((MOD / "history/provinces").iterdir()):
        m = re.search(r"(?m)^owner\s*=\s*(\w+)", f.read_text(encoding="latin-1"))
        if m:
            held[m[1]] += 1
    dm = get(parse((EU5_SETUP / "12_diplomacy.txt").read_text(encoding="utf-8-sig")), "diplomacy_manager")
    out, n = ["# generated from EU5 12_diplomacy.txt - do not edit"], Counter()
    sd = "start_date = 1337.4.1 end_date = 1836.12.31"
    subjects, pairs = {}, set()
    rows = []
    for k, b in dm:
        if not isinstance(b, list):
            continue
        t = get(b, "subject_type") if k == "dependency" else get(b, "type")
        a, c = get(b, "first"), get(b, "second")
        a = tagmap.FOLDED.get(a, a)
        if a not in table or c not in table:
            continue
        a, c = table[a]["eu4"], table[c]["eu4"]
        if not (held[a] and held[c]) or a == c:
            continue
        rows.append((k, t, a, c))
    for k, t, a, c in rows:
        kind = SUBJECT_KIND.get(t) if k == "dependency" else None
        if kind and kind[0] in ("vassal", "dependency"):
            if c in subjects:
                continue  # one overlord each
            subjects[c] = a
    for k, t, a, c in rows:
        kind = SUBJECT_KIND.get(t) if k == "dependency" else None
        if kind and kind[0] in ("vassal", "dependency"):
            if subjects.get(c) != a or (a, c, t) in pairs:
                continue
            pairs.add((a, c, t))
            extra = f' subject_type = "{kind[1]}"' if kind[1] else ""
            out.append(f"{kind[0]} = {{ first = {a} second = {c}{extra} {sd} }}")
        elif kind or t in ("alliance", "guarantee", "military_sponsorship"):
            key = kind[0] if kind else ("guarantee" if t == "guarantee" else "alliance")
            if subjects.get(c) == a or subjects.get(a) == c or (key, frozenset((a, c))) in pairs:
                continue
            pairs.add((key, frozenset((a, c))))
            out.append(f"{key} = {{ first = {a} second = {c} {sd} }}")
        else:
            continue
        n[t] += 1
    # personal unions: EU5 has no union object, a union is one ruler holding several crowns. The ruler's own
    # country (character `tag`) is the senior; the others, unless already subjects of someone, become juniors.
    cdict = dict(countries())
    crowns = defaultdict(list)
    for t5, cb in cdict.items():
        rid = chars.country_rulers(cb)[0]
        if rid:
            crowns[rid].append(t5)
    union_juniors = set()
    for rid, group in sorted(crowns.items()):
        if len(group) < 2:
            continue
        home = chars.get(chars.characters()[rid], "tag")
        senior = home
        if senior not in table or senior in tagmap.FOLDED:
            continue
        s4 = table[senior]["eu4"]
        for j5 in sorted(group):
            if j5 == senior or j5 not in table or j5 in tagmap.FOLDED:
                continue
            j4 = table[j5]["eu4"]
            if (held[s4] and held[j4] and j4 != s4 and j4 not in subjects and s4 not in subjects
                    and j4 not in union_juniors and s4 not in union_juniors):
                union_juniors.add(j4)
                subjects[j4] = s4
                out.append(f"union = {{ first = {s4} second = {j4} {sd} }}")
                n["union"] += 1
    # royal marriages: a ruler whose consort is another country's (lifted queen origin)
    for x, y in sorted(MARRIAGES):
        if held[x] and held[y] and subjects.get(x) != y and subjects.get(y) != x:
            out.append(f"royal_marriage = {{ first = {x} second = {y} {sd} }}")
            n["royal_marriage"] += 1
    # the Celestial Empire: EU5's China organisation names its leader and its celestial governors (tributaries)
    org = (EU5_SETUP / "15_international_organizations.txt").read_text(encoding="utf-8-sig")
    m = re.search(r"leader\s*=\s*(\w+)\s*celestial_governor\s*=\s*\{([^}]*)\}", org)
    emperor = table.get(m[1], {}).get("eu4") if m else None
    p = MOD / "history/diplomacy"
    shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True)
    drop_base_game_relations_at_start(set(subjects) | set(subjects.values()))
    if emperor and held[emperor]:
        for g5 in m[2].split():
            g4 = table.get(g5, {}).get("eu4")
            if g4 and held[g4] and g4 not in subjects and g4 != emperor:
                subjects[g4] = emperor
                out.append(f'dependency = {{ first = {emperor} second = {g4} subject_type = "tributary_state" {sd} }}')
                n["celestial_governor"] += 1
        # same file name as the base game's, which crowns the Khalkha khan in 1260 and Ming in 1368
        (p / "celestial_empire.txt").write_text(f"1260.5.5 = {{ celestial_emperor = {emperor} }}\n"
                                                "1368.1.23 = { celestial_emperor = MNG }\n"
                                                "1644.10.30 = { celestial_emperor = QNG }\n")
    (p / "1337_diplomacy.txt").write_text("\n".join(out) + "\n")
    return dict(n)


WAR_NAMES = {
    "CIVIL_WAR_NAME": "Second War of Scottish Independence",
    "CRUSADE_WAR_NAME": "Lithuanian Crusade",
    "FATE_OF_TLEMCEN": "Fate of Tlemcen",
    "UNIFY_ILKHANATE_WAR_NAME": "Unification of the Ilkhanate",
    "SCALIGER_WAR_NAME": "War against the Scaligeri",
}
# EU5 war kind -> EU4 war goal; `capital` points the goal at the first defender's capital province
WAR_GOALS = {
    "civil_war": ("take_capital_throne", "cb_claim_throne", "tag"),
    "cb_crusade": ("superiority_crusade", "cb_crusade", None),
    "cb_conquer_province": ("take_claim", "cb_conquest", "province"),
    "cb_unify_ilkahante": ("take_claim", "cb_conquest", "capital"),
    "cb_scaligeri_war": ("take_claim", "cb_conquest", "capital"),
}


def tag_capital(tag):
    for f in (MOD / "history/countries").glob(f"{tag} - *.txt"):
        m = re.search(r"(?m)^capital\s*=\s*(\d+)", f.read_text(encoding="latin-1"))
        if m:
            return m[1]
    return None


def step_wars(table):
    """The wars and truces EU5 has running in April 1337 (16_wars): wars as history/wars files dated
    1337.3.1, truces as add_truce_with in the country files. Countries with no EU4 counterpart or no
    land are left out; a war that loses all of one side is dropped."""
    from paths import EU5_SETUP
    from pdx import parse
    held = Counter()
    for f in (MOD / "history/provinces").iterdir():
        m = re.search(r"(?m)^owner\s*=\s*(\w+)", f.read_text(encoding="latin-1"))
        if m:
            held[m[1]] += 1
    l2p = json.load(open(DATA / "loc2prov.json"))
    loc_prov = {loc: pid for pid, v in l2p.items() for loc in v["locations"]}

    def eu4(t):
        e = table.get(t, {}).get("eu4")
        return e if e and held[e] else None

    wm = get(parse((EU5_SETUP / "16_wars.txt").read_text(encoding="utf-8-sig")), "war_manager")
    shutil.rmtree(MOD / "history/wars", ignore_errors=True)
    (MOD / "history/wars").mkdir(parents=True)
    stats = Counter()
    for kind, w in wm:
        if kind not in ("war", "civil_war"):
            continue
        att = [x for x in (eu4(get(a, "country")) for a in getall(w, "attacker")) if x]
        dfn = [x for x in (eu4(get(a, "country")) for a in getall(w, "defender")) if x]
        wn = get(w, "war_name")
        name = WAR_NAMES.get(get(wn, "name"), get(wn, "name"))
        if not att or not dfn:
            stats["war_skipped"] += 1
            continue
        tp = get(w, "take_province") or get(w, "superiority") or []
        cb = "civil_war" if kind == "civil_war" else get(tp, "casus_belli")
        typ, ecb, how = WAR_GOALS[cb]
        goal = [f"\ttype = {typ}", f"\tcasus_belli = {ecb}"]
        if how == "tag":
            goal.append(f"\ttag = {att[0]}")
        elif how == "province":
            prov = loc_prov.get(get(tp, "location")) or tag_capital(dfn[0])
            goal.append(f"\tprovince = {prov}")
        elif how == "capital":
            goal.append(f"\tprovince = {tag_capital(dfn[0])}")
        body = [f'name = "{name}"', "war_goal = {", *goal, "}", "", "1337.3.1 = {"]
        body += [f"\tadd_attacker = {t}" for t in att] + [f"\tadd_defender = {t}" for t in dfn] + ["}", ""]
        fn = re.sub(r"[^A-Za-z0-9]+", "_", name) + ".txt"
        (MOD / "history/wars" / fn).write_text("# generated from EU5 16_wars.txt - do not edit\n" + "\n".join(body))
        stats["wars"] += 1
    # truces: every pair across the two sides of each EU5 truce, in the country files
    pairs = defaultdict(set)
    for kind, tr in wm:
        if kind != "truce":
            continue
        a = {x for x in (eu4(t) for t in getall(tr, "attacker")) if x}
        d = {x for x in (eu4(t) for t in getall(tr, "defender")) if x}
        for x in a:
            for y in d:
                if x != y:
                    pairs[x].add(y)
                    pairs[y].add(x)
    for tag, others in pairs.items():
        for f in (MOD / "history/countries").glob(f"{tag} - *.txt"):
            f.write_text(f.read_text(encoding="latin-1").rstrip("\n") + "\n\n1337.3.1 = {\n"
                         + "".join(f"\tadd_truce_with = {o}\n" for o in sorted(others)) + "}\n", encoding="latin-1")
            stats["truces"] += len(others)
    return dict(stats)


def step_rivals(table):
    """historical_rival / historical_friend in the country files: EU5's 20_rivals (a rival = { first second }
    is first's rival) and the alliances of 12_diplomacy (friends). The 1444 ones the vanilla files carry are
    stripped in step_countries. Only tags with land."""
    from paths import EU5_SETUP
    from pdx import parse
    held = set()
    for f in (MOD / "history/provinces").iterdir():
        m = re.search(r"(?m)^owner\s*=\s*(\w+)", f.read_text(encoding="latin-1"))
        if m:
            held.add(m[1])

    def eu4(t):
        e = table.get(t, {}).get("eu4")
        return e if e in held else None

    rel = defaultdict(lambda: {"historical_rival": set(), "historical_friend": set()})
    for fname, man, kinds in (("20_rivals.txt", "diplomacy_manager", {"rival": "historical_rival"}),
                              ("12_diplomacy.txt", "diplomacy_manager", {"alliance": "historical_friend"})):
        for k, b in get(parse((EU5_SETUP / fname).read_text(encoding="utf-8-sig")), man):
            if not isinstance(b, list):
                continue
            key = kinds.get(k) or (kinds.get(get(b, "type")) if k == "dependency" else kinds.get(get(b, "type")))
            a, c = eu4(get(b, "first")), eu4(get(b, "second"))
            if key and a and c and a != c:
                rel[a][key].add(c)
                if key == "historical_friend":
                    rel[c][key].add(a)
    n = Counter()
    for tag, d in rel.items():
        lines = [f"{k} = {o}" for k in ("historical_rival", "historical_friend") for o in sorted(d[k])]
        for f in (MOD / "history/countries").glob(f"{tag} - *.txt"):
            f.write_text("\n".join(lines) + "\n" + f.read_text(encoding="latin-1"), encoding="latin-1")
            n["countries"] += 1
            n["rivals"] += len(d["historical_rival"])
            n["friends"] += len(d["historical_friend"])
    return dict(n)


EMP = [None]
ELECTORS = set()
MARRIAGES = set()  # (tag, tag) royal marriages: a ruler's consort comes from another country


def main():
    table, _ = build_table()
    json.dump(table, open(DATA / "tags.json", "w"), indent=0, ensure_ascii=False, sort_keys=True)
    po = province_owners()
    crm = json.load(open(DATA / "cr_map.json"))
    cmap, rmap = crm["culture"], crm["religion"]
    stats = Counter()
    hre, emperor, electors = hre_members(table)
    ELECTORS.update(electors)
    stats["hre_members"] = len(hre)
    step_provinces(table, po, cmap, rmap, stats, hre)
    stats["emperor"] = emperor
    EMP[0] = emperor
    step_countries(table, po, cmap, rmap, stats)
    stats["dormant"] = step_dormant(table, stats)
    step_tags(table)
    import ideas
    stats["idea_sets"] = ideas.write()
    stats["diplomacy"] = step_diplomacy(table)
    stats["wars"] = step_wars(table)
    stats["institutions"] = step_institutions()
    stats["rivals"] = step_rivals(table)
    stats["accepted_cultures"] = step_accepted(table)
    stats["bookmark"] = step_bookmark(table)
    import flags
    stats["flags"] = flags.write(MOD / "gfx/flags", {r["eu4"]: eu5info.color_of(t5) or (100, 100, 100)
                                                       for t5, r in table.items() if r["new"]})
    print(dict(stats))


if __name__ == "__main__":
    main()
