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
    """remove depth-0 lines matching pattern (single-line statements only)"""
    out, depth = [], 0
    for line in base.split("\n"):
        code = line.split("#")[0]
        if depth == 0 and re.match(pattern, code):
            if code.count("{") > code.count("}"):
                depth += code.count("{") - code.count("}")
                continue
            continue
        if depth > 0 and re.match(pattern, code) is None:
            pass
        depth += code.count("{") - code.count("}")
        if depth < 0:
            depth = 0
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
    from paths import EU5_SETUP
    t = (EU5_SETUP / "15_international_organizations.txt").read_text(encoding="utf-8-sig")
    m = re.search(r"type\s*=\s*hre\b.*?members\s*=\s*\{([^}]*)\}.*?leader\s*=\s*(\w+)", t, re.S)
    mem = set(m[1].split())
    return {table[x]["eu4"] for x in mem if x in table}, table.get(m[2], {}).get("eu4")


def step_provinces(table, po, cmap, rmap, stats, hre_members=None):
    reused_codes = {r["eu4"] for r in table.values()}
    out = MOD / "history/provinces"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    land = land_provinces()
    cr_vote = json.load(open(DATA / "loc2prov.json"))
    from popdata import location_pops
    lp = location_pops()
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
            base = strip_depth0(base, r"\s*(?:monarch|heir|queen|add_accepted_culture)\s*=")
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
        # rulers
        rid = i.get("ruler")
        ch = chars.characters().get(rid) if rid else None
        mb = chars.block(rid, ch, chars.ruler_regnal(rid, b)) if ch and b else None
        if mb:
            body += "\nmonarch = {\n" + mb + "\n}\n"
            hid, hch = chars.find_heir(rid)
            hb = chars.block(hid, hch, heir=True) if hch else None
            if hb:
                body += "heir = {\n" + hb + "\n}\n"
            stats["rulers"] += 1
        else:
            stats["no_ruler"] += 1
        if tag == EMP[0] and "emperor = yes" not in body:
            body += "\nemperor = yes\n"
        res = body + "\n" + "".join(kept)
        (out / fname).write_bytes(res.rstrip().encode("latin-1", "replace") + b"\n")


def step_dormant(table):
    """vanilla tags with no EU5 1337 counterpart keep their files (backstory entries dropped)"""
    out = MOD / "history/countries"
    used = {r["eu4"] for r in table.values()}
    n = 0
    for f in sorted((VAN / "countries").iterdir()):
        if f.name[:3] in used:
            continue
        base, blocks = split_blocks(f.read_text(encoding="latin-1"))
        base = strip_depth0(base, r"\s*(?:monarch|heir|queen)\s*=")
        res = base.rstrip() + "\n\n" + "".join(b for d, b in blocks if d > BACKSTORY_END)
        (out / f.name).write_bytes(res.rstrip().encode("latin-1", "replace") + b"\n")
        n += 1
    return n


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
    for tag5, r in sorted(table.items(), key=lambda kv: kv[1]["eu4"]):
        if not r["new"]:
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


def step_diplomacy(table):
    from paths import EU5_SETUP
    from pdx import parse
    held = Counter()
    for f in sorted((MOD / "history/provinces").iterdir()):
        m = re.search(r"(?m)^owner\s*=\s*(\w+)", f.read_text(encoding="latin-1"))
        if m:
            held[m[1]] += 1
    dm = get(parse((EU5_SETUP / "12_diplomacy.txt").read_text(encoding="utf-8-sig")), "diplomacy_manager")
    out, n = ["# generated from EU5 12_diplomacy.txt - do not edit"], Counter()
    for k, b in dm:
        if not isinstance(b, list):
            continue
        a, c = get(b, "first"), get(b, "second")
        if a not in table or c not in table:
            continue
        a, c = table[a]["eu4"], table[c]["eu4"]
        if not (held[a] and held[c]) or a == c:
            continue
        t = get(b, "subject_type") if k == "dependency" else get(b, "type")
        sd = "start_date = 1337.4.1 end_date = 1836.12.31"
        if t in ("vassal", "fiefdom", "dominion", "appanage", "samanta", "tusi", "familial_governor", "hanseatic_member"):
            out.append(f"vassal = {{ first = {a} second = {c} {sd} }}")
        elif t == "tributary":
            out.append(f"tributary = {{ first = {a} second = {c} {sd} }}")
        elif t == "alliance":
            out.append(f"alliance = {{ first = {a} second = {c} {sd} }}")
        elif t == "guarantee":
            out.append(f"guarantee = {{ first = {a} second = {c} {sd} }}")
        elif t == "military_sponsorship":
            out.append(f"alliance = {{ first = {a} second = {c} {sd} }}")
        else:
            continue
        n[t] += 1
    p = MOD / "history/diplomacy"
    shutil.rmtree(p, ignore_errors=True)
    p.mkdir(parents=True)
    (p / "1337_diplomacy.txt").write_text("\n".join(out) + "\n")
    return dict(n)


def step_clear_wars():
    for d in ("wars",):
        p = MOD / "history" / d
        shutil.rmtree(p, ignore_errors=True)
        p.mkdir(parents=True)
        (p / "1337_placeholder.txt").write_text("# generated diplomacy goes here\n")


EMP = [None]


def main():
    table, _ = build_table()
    json.dump(table, open(DATA / "tags.json", "w"), indent=0, ensure_ascii=False)
    po = province_owners()
    crm = json.load(open(DATA / "cr_map.json"))
    cmap, rmap = crm["culture"], crm["religion"]
    stats = Counter()
    hre, emperor = hre_members(table)
    stats["hre_members"] = len(hre)
    step_provinces(table, po, cmap, rmap, stats, hre)
    stats["emperor"] = emperor
    EMP[0] = emperor
    step_countries(table, po, cmap, rmap, stats)
    stats["dormant"] = step_dormant(table)
    step_tags(table)
    stats["diplomacy"] = step_diplomacy(table)
    step_clear_wars()
    print(dict(stats))


if __name__ == "__main__":
    main()
