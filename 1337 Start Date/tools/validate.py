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
        if kind in ("vassal", "dependency"):
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
