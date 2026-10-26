#!/usr/bin/env python3
"""Lift a region's 867 states into tags.db.

Every EU4 province of the region that provfaiths.PROVINCE_COUNTY pairs with a CK3
county goes to the state that county belongs to at 867: its holder's liege chain
(explicit `liege =` in CK3's title history) is followed to the top, and the top
liege - the sovereign - receives the province, vassals and all. Independent
counts and dukes are states of their own, and so are tributaries (CK3's
`tributary_of`, which is not a `liege =`): they are independent, their suzerain is
only a relationship. The tag carries the sovereign's primary title (state867).

    python3 tools/liftstates.py india            # plan only
    python3 tools/liftstates.py india apply      # write tags, provinces and loc

Existing tags with the state's primary title keep their code and gain/lose
provinces; new tags get a free 3-letter code made from their name.
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

REGIONS = {
    "seasia": ["burma_region", "indo_china_region"],
    "china": ["@TNG", 701, 702, 709, 2183, 2747, 4223, 4670],
    "maritime": ["malaya_region", "indonesia_region", "moluccas_region"],
    "westafrica": ["sahel_region", "niger_region", "guinea_region"],
    "eastside": ["east_africa_region", "central_africa_region", "west_siberia_region", "mongolia_region", "horn_of_africa_region", "russia_region", "ural_region"],
    "india": ["hindusthan_region", "bengal_region", "west_india_region", "deccan_region", "coromandel_region"],
}


# technology group of the tags a region creates (vanilla gives the Indonesian realms `chinese`)
TECH = {"china": "chinese", "maritime": "chinese", "westafrica": "sub_saharan", "eastside": "east_african"}
TECH_OF_PID = {pid: "aboriginal_tech" for pid in (1237, 2719, 2720, 2721, 2722, 1245, 2718, 2723, 2724)}


def region_pids(names):
    import eu4

    areas, regions = eu4.load_areas(), eu4.load_region_areas()
    out = set()
    for r in names:
        if isinstance(r, str) and r.startswith("@"):  # every province the tag owns now
            con = sqlite3.connect(os.path.join(HERE, "tags.db"))
            out.update(p for (p,) in con.execute("select pid from tag_provinces where tag=?", (r[1:],)))
            continue
        if isinstance(r, int):
            out.add(r)
            continue
        for a in regions[r]:
            out.update(areas.get(a, []))
    return out


def eu4_government(title):
    from ck3 import title_government

    g = title_government(title)
    return {"tribal_government": "tribal", "ecclesiastical_government": "theocracy",
            "republic_government": "republic"}.get(g, "monarchy")


# capitals where CK3's capital county is not the EU4 province of that name
CAPITAL = {"k_kosala": 4497, "k_bengal": 563}


def title_capital(title):
    """CK3's `capital = c_x` of a title (a county is its own capital)."""
    import culturalnames

    if title.startswith("c_"):
        return title
    m = re.search(r"capital\s*=\s*(c_[\w\-]+)", culturalnames._title_blocks().get(title, ""))
    return m.group(1) if m else None


def free_code(name, taken):
    letters = re.sub(r"[^A-Z]", "", __import__("addtag").ascii_name(name).upper())
    cands = []
    if len(letters) >= 3:
        cands += [letters[:3], letters[0] + letters[1] + letters[-1], letters[0] + letters[2] + letters[-1],
                  letters[0] + letters[-2:], letters[:2] + letters[3:4] if len(letters) > 3 else letters[:3]]
        for i in range(2, len(letters)):
            for j in range(i + 1, len(letters)):
                cands.append(letters[0] + letters[i] + letters[j])
    for c in cands:
        if len(c) == 3 and c not in taken:
            return c
    import itertools

    # every in-order triple of the name's letters, then its first letter with any two others
    for c in ("".join(t) for t in itertools.combinations(letters, 3)):
        if c not in taken:
            return c
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for c in (letters[:1] + a + b for a in alpha for b in alpha):
        if len(letters) and c not in taken:
            return c
    raise SystemExit(f"no free tag code for {name}")


def plan(pids):
    import provfaiths as pf
    import state867 as st

    table = {p: c for p, c in pf.PROVINCE_COUNTY.items() if p in pids}
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    bytitle = {r[1]: r[0] for r in con.execute("select tag, ck3_title from tags")}
    out = []
    for s in st.states(table):
        pt = s["primary"]
        provs = [p for p, _c in s["provinces"]]
        cap_county = title_capital(pt)
        cap = next((p for p, c in s["provinces"] if c == cap_county), provs[0])
        cap = CAPITAL.get(pt, cap) if CAPITAL.get(pt) in provs else cap
        out.append({"title": pt, "name": s["name"], "provs": provs, "capital": cap,
                    "tag": bytitle.get(pt), "gov": eu4_government(pt)})
    return out


def apply(pids, region=None):
    import addtag
    import db
    import eu4
    import provfaiths as pf
    from models import Culture, Province

    plans = plan(pids)
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    taken = {r[0] for r in con.execute("select tag from tags")} | addtag.vanilla_tags()
    con.close()
    vanilla_files = {fn for fn, _t in eu4.load_vanilla_countries().values()}
    # provinces first: vanilla name and culture, religion from the CK3 county's faith
    s = db.session()
    for pl in plans:
        for pid in pl["provs"]:
            if s.get(Province, pid) is not None:
                continue
            src = eu4.vanilla_prov_file(pid)
            nm = re.sub(r"^\d+\s*-\s*", "", os.path.basename(src)[:-4])
            txt = open(src, encoding="cp1252", errors="replace").read()
            cul = re.search(r"^culture\s*=\s*(\w+)", txt, re.M)
            rel = pf.expected(pid)[0]
            culture = cul.group(1) if cul else None
            if not culture:  # unowned land in vanilla: the culture of the county's 867 holder
                import culturelift as cl

                _h, cc = cl.holder_culture(pf.PROVINCE_COUNTY[pid])
                culture = cl.ensure_culture(cc, s) if cc else None
            if not culture or not rel:
                raise SystemExit(f"province {pid} {nm}: no culture or no CK3 religion")
            if s.get(Culture, culture) is None:
                s.add(Culture(name=culture))
            s.add(Province(pid=pid, name=nm, culture=culture, religion=rel, fort=False))
    s.commit()
    s.close()
    for pl in sorted(plans, key=lambda p: -len(p["provs"])):
        if pl["tag"]:
            print(f"{pl['tag']} ({pl['title']}) keeps its code")
            addtag.main(["--to", pl["tag"], *map(str, pl["provs"]), "--take"]) if _missing(pl) else None
            continue
        code = free_code(pl["name"], taken)
        taken.add(code)
        tech = TECH_OF_PID.get(pl["capital"]) or TECH.get(region, "indian")
        args = [code, pl["title"], *map(str, pl["provs"]), "--tech", tech, "--gov", pl["gov"],
                "--capital", str(pl["capital"]), "--take"]
        # a country file named like a vanilla one would merge with it: name it apart
        if addtag.ascii_name(pl["name"]) + ".txt" in vanilla_files:
            args += ["--file", f"{addtag.ascii_name(pl['name'])}_{code}"]
        addtag.main(args)
    # a tag that already existed gains only what it did not own; drop what the plan took away
    print(f"{len(plans)} states written")


def _missing(pl):
    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    own = {r[0] for r in con.execute("select pid from tag_provinces where tag=?", (pl["tag"],))}
    con.close()
    return [p for p in pl["provs"] if p not in own]


if __name__ == "__main__":
    reg = sys.argv[1] if len(sys.argv) > 1 else "india"
    pids = region_pids(REGIONS[reg])
    if sys.argv[2:3] == ["apply"]:
        apply(pids, reg)
    else:
        for pl in sorted(plan(pids), key=lambda p: -len(p["provs"])):
            print(f"{pl['tag'] or '(new)':6} {pl['title']:18} {pl['name']:18} {len(pl['provs']):2} provs cap {pl['capital']} gov {pl['gov']}")
