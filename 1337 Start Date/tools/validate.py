#!/usr/bin/env python3
"""Static checks on generated output. Must end with ALL CHECKS PASSED."""
import re, sys
from collections import Counter
from pathlib import Path
from paths import EU4_GAME, MOD
from pdx import parse

errs, warns = [], []


def tags_all():
    tags = {}
    for f in list((EU4_GAME / "common/country_tags").glob("*.txt")) + list((MOD / "common/country_tags").glob("*.txt")):
        for m in re.finditer(r"^([A-Z0-9]{3})\s*=\s*\"([^\"]+)\"", f.read_text(encoding="latin-1"), re.M):
            if m[1] in tags and f.parent == MOD / "common/country_tags":
                errs.append(f"tag {m[1]} defined twice")
            tags[m[1]] = m[2]
    return tags


def names(kind):
    s = set()
    t = (EU4_GAME / f"common/{kind}")
    for f in [*t.glob("*.txt"), *(MOD / f"common/{kind}").glob("*.txt")]:
        for k, v in parse(f.read_text(encoding="latin-1")):
            if isinstance(v, list):
                s.add(k)
                for k2, v2 in v:
                    if isinstance(v2, list):
                        s.add(k2)
    return s


def balanced(text):
    d = 0
    for line in text.split("\n"):
        d += line.split("#")[0].count("{") - line.split("#")[0].count("}")
        if d < 0:
            return False
    return d == 0


def main():
    tags = tags_all()
    cultures, religions = names("cultures"), names("religions")
    reforms = names("government_reforms")
    provs = {}
    for f in (MOD / "history/provinces").iterdir():
        t = re.sub(r"#[^\n]*", "", f.read_text(encoding="latin-1"))
        pid = int(re.match(r"\d+", f.name)[0])
        provs[pid] = t
        if not balanced(t):
            errs.append(f"unbalanced braces {f.name}")
        for m in re.finditer(r"\b(?:owner|controller|add_core)\s*=\s*([A-Z0-9]{3})\b", t):
            if m[1] not in tags and m[1] != "REB":
                errs.append(f"{f.name}: unknown tag {m[1]}")
        for k, pool, label in (("culture", cultures, "culture"), ("religion", religions, "religion")):
            for m in re.finditer(rf"(?m)^{k}\s*=\s*(\w+)", t):
                if m[1] not in pool:
                    errs.append(f"{f.name}: unknown {label} {m[1]}")
        o = re.search(r"(?m)^owner\s*=\s*(\w+)", t)
        if o and not re.search(r"(?m)^is_city\s*=\s*yes", t):
            errs.append(f"{f.name}: owned without is_city")
    owners = Counter()
    for t in provs.values():
        o = re.search(r"(?m)^owner\s*=\s*(\w+)", t)
        if o:
            owners[o[1]] += 1
    hist = {f.name[:3]: f for f in (MOD / "history/countries").iterdir()}
    for tag in tags:
        if tag in owners and tag not in hist:
            warns.append(f"{tag} owns {owners[tag]} provinces but has no history file")
    for tag, f in hist.items():
        t = f.read_text(encoding="latin-1")
        if tag not in tags:
            errs.append(f"{f.name}: history for unregistered tag")
        if not balanced(t):
            errs.append(f"unbalanced braces {f.name}")
        cap = re.search(r"(?m)^capital\s*=\s*(\d+)", t)
        if cap and int(cap[1]) not in provs:
            errs.append(f"{f.name}: capital {cap[1]} missing")
        for k, pool in (("primary_culture", cultures), ("religion", religions)):
            m = re.search(rf"(?m)^{k}\s*=\s*(\w+)", t)
            if m and m[1] not in pool:
                errs.append(f"{f.name}: unknown {k} {m[1]}")
        for m in re.finditer(r"(?m)^add_government_reform\s*=\s*(\w+)", t):
            if m[1] not in reforms:
                errs.append(f"{f.name}: unknown reform {m[1]}")
        if tag in owners and not re.search(r"(?m)^technology_group\s*=", t):
            errs.append(f"{f.name}: no technology_group")
    # new tags need common/countries + loc
    loc = (MOD / "localisation/1337_countries_l_english.yml").read_text(encoding="utf-8-sig")
    for m in re.finditer(r"^([A-Z0-9]{3})\s*=\s*\"countries/(.+)\"", (MOD / "common/country_tags/1337_tags.txt").read_text(encoding="latin-1"), re.M):
        if not (MOD / "common/countries" / m[2]).exists():
            errs.append(f"{m[1]}: missing common/countries/{m[2]}")
        if f" {m[1]}:0 " not in loc:
            errs.append(f"{m[1]}: missing loc")
        if m[1] not in hist:
            errs.append(f"{m[1]}: no history file")
    # subjects: known type, one overlord each, no cycles, both sides own land, no alliance with the overlord
    dip = (MOD / "history/diplomacy/1337_diplomacy.txt").read_text(encoding="latin-1")
    types = set(re.findall(r"^(\w+) = \{", (EU4_GAME / "common/subject_types/00_subject_types.txt").read_text(encoding="latin-1"), re.M))
    over, allied = {}, set()
    own_land = {m[1] for f in (MOD / "history/provinces").iterdir()
                if (m := re.search(r"(?m)^owner\s*=\s*(\w+)", f.read_text(encoding="latin-1")))}
    for kind, body in re.findall(r"^(\w+) = \{(.*)\}", dip, re.M):
        m = re.search(r"first = (\w+) second = (\w+)", body)
        a_, c_ = m[1], m[2]
        for x in (a_, c_):
            if x not in own_land:
                errs.append(f"diplomacy: {kind} {a_}/{c_}: {x} owns no province")
        st = re.search(r'subject_type = "(\w+)"', body)
        if st and st[1] not in types:
            errs.append(f"diplomacy: unknown subject type {st[1]}")
        if kind in ("vassal", "dependency", "union"):
            if c_ in over:
                errs.append(f"diplomacy: {c_} has two overlords ({over[c_]}, {a_})")
            over[c_] = a_
        elif kind == "alliance":
            allied.add(frozenset((a_, c_)))
    for c_, a_ in over.items():
        seen, x = {c_}, a_
        while x in over:
            if x in seen:
                errs.append(f"diplomacy: subject cycle through {x}")
                break
            seen.add(x)
            x = over[x]
        if frozenset((a_, c_)) in allied:
            errs.append(f"diplomacy: {c_} is allied with its overlord {a_}")
    # national ideas: every modifier is one the base game's own idea sets use ,
    # seven ideas per set, every name and description present, tag registered
    import ideas as _ideas
    mods = _ideas.vanilla_modifiers()
    own_loc = (MOD / "localisation/1337_ideas_l_english.yml").read_text(encoding="utf-8-sig")
    registered = {m[1] for m in re.finditer(r"(?m)^([A-Z0-9]{3})\s*=", (MOD / "common/country_tags/1337_tags.txt").read_text(encoding="latin-1"))}
    n_sets = 0
    for name, body in parse((MOD / "common/ideas/1337_national_ideas.txt").read_text(encoding="latin-1")):
        n_sets += 1
        tag = name[:3]
        if tag not in registered:
            errs.append(f"ideas {name}: {tag} is not a registered tag")
        singles = [k for k, v in body if isinstance(v, list) and k not in ("start", "bonus", "trigger")]
        if len(singles) != 7:
            errs.append(f"ideas {name}: {len(singles)} ideas, not 7")
        for key, part in body:
            if not isinstance(part, list) or key == "trigger":
                continue
            for mod, val in part:
                if mod not in mods:
                    errs.append(f"ideas {name}: modifier {mod} is not used by any base-game idea set")
        for k in (name, name + "_start", name + "_bonus", *singles, *(x + "_desc" for x in singles)):
            if f" {k}:0 " not in own_loc:
                errs.append(f"ideas {name}: missing loc {k}")
    print(f"  {n_sets} national idea sets checked against {len(mods)} base-game modifiers")
    # colours in range, a flag for every tag the mod adds
    for f in (MOD / "common/countries").glob("*.txt"):
        c = re.search(r"color = \{ (\d+) (\d+) (\d+) \}", f.read_text(encoding="latin-1"))
        if not c or any(int(x) > 255 for x in c.groups()):
            errs.append(f"{f.name}: colour missing or above 255")
    for m in re.finditer(r"^([A-Z0-9]{3})\s*=", (MOD / "common/country_tags/1337_tags.txt").read_text(encoding="latin-1"), re.M):
        if not (MOD / "gfx/flags" / f"{m[1]}.tga").exists():
            errs.append(f"{m[1]}: no flag")
    # technology: years ascend, every group has a start level the countries' adjustments are relative to
    for f in ("adm", "dip", "mil"):
        yrs = [int(x) for x in re.findall(r"(?m)^\s*year\s*=\s*(\d+)", (MOD / f"common/technologies/{f}.txt").read_text(encoding="latin-1"))]
        if yrs != sorted(yrs):
            errs.append(f"technologies/{f}.txt: years not ascending")
    if not re.search(r"start_level = \d", (MOD / "common/technology.txt").read_text(encoding="latin-1")):
        errs.append("technology.txt: no start levels")
    # the Age of Traditions: lifted objectives and our abilities exist, every key is localised, a window is in the gui
    import ages as _ages
    age = (MOD / "common/ages/00_traditions.txt").read_text(encoding="latin-1")
    base_age = (EU4_GAME / "common/ages/00_default.txt").read_text(encoding="latin-1")
    for o in _ages.LIFTED:
        if f"\t\t{o} = {{" not in age or f"{o} = {{" not in base_age:
            errs.append(f"ages: objective {o} not lifted from the base game")
    amods = []
    for _n, body in parse(age):
        for key, part in body:
            if key == "abilities":
                for _ab, ab in part:
                    amods += [k for kk, blk in ab if kk == "modifier" for k, _v in blk]
    for m_ in amods:
        if m_ != "num_of_age_rewards" and m_ not in mods:
            errs.append(f"ages: modifier {m_} is not used by any base-game idea set")
    aloc = (MOD / "localisation/1337_ages_l_english.yml").read_text(encoding="utf-8-sig")
    for k in (_ages.AGE, _ages.AGE + "_desc", *(a_[0] + s_ for a_ in _ages.ABILITIES for s_ in ("", "_desc"))):
        if f" {k}:0 " not in aloc:
            errs.append(f"ages: missing loc {k}")
    if f'name = "{_ages.AGE}"' not in (MOD / "interface/ages_view.gui").read_text(encoding="latin-1"):
        errs.append("ages: no window for the new age in ages_view.gui")
    # a realm's capital is one of its own provinces
    capital_owner = {}
    for f in (MOD / "history/provinces").iterdir():
        m = re.search(r"(?m)^owner\s*=\s*(\w+)", re.split(r"(?m)^\d{3,4}\.\d+\.\d+\s*=", f.read_text(encoding="latin-1"))[0])
        if m:
            capital_owner[int(re.match(r"\d+", f.name)[0])] = m[1]
    for f in (MOD / "history/countries").glob("*.txt"):
        c = re.search(r"(?m)^capital\s*=\s*(\d+)", f.read_text(encoding="latin-1"))
        if c and f.name[:3] in capital_owner.values() and capital_owner.get(int(c[1])) != f.name[:3]:
            errs.append(f"{f.name}: capital {c[1]} is not an own province")
    # provinces: an owned province has development, a known trade good, a controller and its owner as a core
    def _top(path):
        return re.split(r"(?m)^\d{3,4}\.\d+\.\d+\s*=", path.read_text(encoding="latin-1"))[0]

    goods = set(re.findall(r"(?m)^(\w+) = \{", (EU4_GAME / "common/tradegoods/00_tradegoods.txt").read_text(encoding="latin-1"))) | {"unknown"}
    for f in (MOD / "history/provinces").iterdir():
        top = _top(f)
        o = re.search(r"(?m)^owner = (\w+)", top)
        g = re.search(r"(?m)^trade_goods = (\w+)", top)
        if g and g[1] not in goods:
            errs.append(f"{f.name}: unknown trade good {g[1]}")
        if o:
            if not all(re.search(rf"(?m)^{k} = [1-9]", top) for k in ("base_tax", "base_production", "base_manpower")):
                errs.append(f"{f.name}: owned but has no development (wasteland?)")
            if not re.search(r"(?m)^controller = ", top):
                errs.append(f"{f.name}: owned without a controller")
            if not re.search(rf"(?m)^add_core = {o[1]}\b", top):
                errs.append(f"{f.name}: the owner {o[1]} is not a core holder")
    # text: braces balance in every text file, localisation lines are well formed and keys unique, no characters
    # Windows-1252 cannot show left as '?' in the names of history files
    seen = {}
    for f in (MOD / "localisation").rglob("*.yml"):
        for i, line in enumerate(f.read_text(encoding="utf-8-sig").split("\n"), 1):
            if line.strip() and not line.startswith("l_english") and not re.match(r'^ ([\w.\-]+):\d* ".*"\s*$', line):
                errs.append(f"{f.name}:{i}: malformed localisation line")
            k = re.match(r"^ ([\w.\-]+):", line)
            if k and k[1] in seen and seen[k[1]] != f.name:
                errs.append(f"localisation key {k[1]} in both {seen[k[1]]} and {f.name}")
            elif k:
                seen[k[1]] = f.name
    for f in list((MOD / "history").rglob("*.txt")) + list((MOD / "common").rglob("*.txt")) + list((MOD / "interface").rglob("*.gui")):
        t = re.sub(r'"[^"\n]*"', '""', re.sub(r"#[^\n]*", "", f.read_text(encoding="latin-1")))
        if t.count("{") != t.count("}"):
            errs.append(f"{f.relative_to(MOD)}: unbalanced braces")
        if re.search(r'"[^"\n]*\?[^"\n]*"', f.read_text(encoding="latin-1")) and "history/" in str(f):
            errs.append(f"{f.relative_to(MOD)}: a name lost characters to '?'")
    # wars use real casus belli and war goals
    cbs = set(re.findall(r"(?m)^(\w+) = \{", (EU4_GAME / "common/cb_types/00_cb_types.txt").read_text(encoding="latin-1")))
    wgs = set(re.findall(r"(?m)^(\w+) = \{", (EU4_GAME / "common/wargoal_types/00_wargoal_types.txt").read_text(encoding="latin-1")))
    for f in (MOD / "history/wars").glob("*.txt"):
        t = f.read_text(encoding="latin-1")
        for k in re.findall(r"casus_belli = (\w+)", t):
            if k not in cbs:
                errs.append(f"{f.name}: unknown casus belli {k}")
        for k in re.findall(r"(?m)^\s*type = (\w+)", t):
            if k not in wgs:
                errs.append(f"{f.name}: unknown war goal {k}")
    # a new tag's common/countries file must not replace a base-game tag's (same file name)
    for f in (MOD / "common/countries").glob("*.txt"):
        if (EU4_GAME / "common/countries" / f.name).exists():
            errs.append(f"common/countries/{f.name} replaces a base-game country file")
    # wars: both sides non-empty, every tag owns land, a goal province exists, truce partners own land
    owners = {}
    for f in (MOD / "history/provinces").iterdir():
        m = re.search(r"(?m)^owner\s*=\s*(\w+)", f.read_text(encoding="latin-1"))
        if m:
            owners[int(re.match(r"\d+", f.name)[0])] = m[1]
    landed = set(owners.values())
    for f in sorted((MOD / "history/wars").glob("*.txt")):
        t = f.read_text(encoding="latin-1")
        att = re.findall(r"add_attacker\s*=\s*(\w+)", t)
        dfn = re.findall(r"add_defender\s*=\s*(\w+)", t)
        if not att or not dfn:
            errs.append(f"{f.name}: a war needs both sides")
        for tag in att + dfn:
            if tag not in landed:
                errs.append(f"{f.name}: {tag} owns no province")
        if set(att) & set(dfn):
            errs.append(f"{f.name}: a tag fights on both sides")
        for pid in re.findall(r"^\s*province\s*=\s*(\d+)", t, re.M):
            if int(pid) not in owners:
                errs.append(f"{f.name}: war goal province {pid} is unowned")
    for f in (MOD / "history/countries").glob("*.txt"):
        for o in re.findall(r"add_truce_with\s*=\s*(\w+)", f.read_text(encoding="latin-1")):
            if o not in landed:
                errs.append(f"{f.name}: truce with {o}, which owns no province")
    for w in warns[:30]:
        print("WARN", w)
    for e in errs[:80]:
        print("ERR", e)
    print(f"{len(errs)} errors, {len(warns)} warnings")
    print("ALL CHECKS PASSED" if not errs else "FAILED")
    sys.exit(1 if errs else 0)


main()
