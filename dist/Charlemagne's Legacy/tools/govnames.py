#!/usr/bin/env python3
"""Which government_names block a tag actually gets (first match wins).

zz_kar_government_names.txt is first-match-wins, so a tag only shows its
CK3 title ladder when it passes the *whole* trigger of its culture's block:
government, primary_culture and - for cultures that span CK3 governments -
the kar_gov_* start flag. A tag that fails the gate falls through to a generic
block (tribal_chiefdoms, default_monarchy, default_tribal ...) and shows
vanilla-style titles instead of its 867 ones. This evaluates the triggers
against the generated country histories to find those tags.

    python3 tools/govnames.py            # list every tag that lands on a generic block
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "..")
ZZ = os.path.join(MOD, "common", "government_names", "zz_kar_government_names.txt")
GENERIC = {"default_monarchy", "default_republic", "default_theocracy", "default_tribal",
           "tribal_chiefdoms", "muslim_monarchy", "hre_county"}


def _end(s, i):
    d = 0
    for k in range(i, len(s)):
        if s[k] == "{":
            d += 1
        elif s[k] == "}":
            d -= 1
            if d == 0:
                return k
    raise ValueError("unbalanced")


def _parse(trig):
    toks = re.findall(r"\{|\}|=|[^\s{}=]+", trig)

    def blk(i):
        items = []
        while i < len(toks) and toks[i] != "}":
            k = toks[i]
            if toks[i + 1] == "=" and toks[i + 2] == "{":
                sub, i = blk(i + 3)
                items.append((k, sub))
                i += 1
            else:
                items.append((k, toks[i + 2]))
                i += 3
        return items, i

    return blk(0)[0]


def blocks():
    t = open(ZZ, encoding="cp1252", errors="replace").read()
    out = []
    for m in re.finditer(r"(?m)^([A-Za-z_0-9]+) = \{\r?$", t):
        body = t[m.end(): _end(t, m.end() - 1)]
        tm = re.search(r"trigger = \{", body)
        if tm:
            out.append((m.group(1), _parse(body[tm.end(): _end(body, tm.end() - 1)])))
    return out


def facts(tag, groups):
    fs = glob.glob(os.path.join(MOD, "history", "countries", f"{tag} - *.txt"))
    if not fs:
        return None
    h = open(fs[0], encoding="cp1252", errors="replace").read()

    def g(k):
        m = re.search(rf"(?m)^{k} = (\S+)", h)
        return m.group(1) if m else None

    return {"gov": g("government"), "cult": g("primary_culture"), "rel": g("religion"), "tag": tag,
            "flags": set(re.findall(r"set_country_flag = (\w+)", h)),
            "reforms": set(re.findall(r"add_government_reform = (\w+)", h)), **groups}


def _holds(items, f, mode_any=False):
    res = []
    for k, v in items:
        if isinstance(v, list):
            if k.upper() == "OR":
                r = any(_holds([x], f) for x in v)
            elif k.upper() == "NOT":
                r = not any(_holds([x], f) for x in v)
            else:
                r = all(_holds([x], f) for x in v)
        else:
            r = f(k, v)
        res.append(r)
    return all(res)


def match(F, items):
    def f(k, v):
        if k == "government":
            return F["gov"] == v
        if k in ("primary_culture", "culture"):
            return F["cult"] == v
        if k == "culture_group":
            return F["cgroup"].get(F["cult"]) == v
        if k == "tag":
            return F["tag"] == v
        if k == "has_country_flag":
            return v in F["flags"]
        if k == "religion":
            return F["rel"] == v
        if k == "religion_group":
            return F["rgroup"].get(F["rel"]) == v
        if k == "has_reform":
            return v in F["reforms"]
        if k == "is_part_of_hre":
            return v == "no"
        return True
    return _holds(items, f)


def cult_groups():
    t = open(os.path.join(MOD, "common", "cultures", "00_cultures.txt"), encoding="cp1252", errors="replace").read()
    out = {}
    for gm in re.finditer(r"(?m)^(\w+) = \{", t):
        body = t[gm.end(): _end(t, gm.end() - 1)]
        for cm in re.finditer(r"(?m)^\t(\w+) = \{", body):
            out[cm.group(1)] = gm.group(1)
    return out


def landing(tags):
    """{tag: block name that wins, or None without a history file}."""
    import rites

    groups = {"cgroup": cult_groups(), "rgroup": rites.religion_groups()}
    bl = blocks()
    out = {}
    for tag in tags:
        F = facts(tag, groups)
        out[tag] = None if F is None else next((n for n, it in bl if match(F, it)), "NONE")
    return out


def culture_blocks():
    """{culture: [block names]} for the dedicated culture blocks (`<culture>_*titles`)."""
    out = {}
    for n, items in blocks():
        for k, v in items:
            if k == "primary_culture" and not isinstance(v, list):
                out.setdefault(v, []).append(n)
    return out


def misses(rows):
    """(tag, culture, block) for tags whose culture has a dedicated block but who land on a generic one."""
    cb = culture_blocks()
    won = landing([r[0] for r in rows])
    return [(t, c, won[t]) for t, c in rows_culture(rows) if won.get(t) in GENERIC | {"NONE"} and c in cb]


def rows_culture(rows):
    return [(r[0], r[1]) for r in rows]


if __name__ == "__main__":
    import sqlite3

    c = sqlite3.connect(os.path.join(HERE, "tags.db"))
    rows = c.execute("select tag, culture from tags").fetchall()
    won = landing([r[0] for r in rows])
    for t, cu in rows:
        if won.get(t) in GENERIC | {"NONE"}:
            print(t, cu, won[t])
