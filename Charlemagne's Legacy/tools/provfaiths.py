#!/usr/bin/env python3
"""Province religions that track CK3's counties (curated, region by region).

A province's religion is the religion lifting the CK3 faith of the county it
corresponds to: the county's capital barony carries a `rite` in CK3's
history/provinces, the rite belongs to a faith (rite_types), and
faiths.FAITH_RELIGION says which EU4 religion lifts that faith. The EU4
province -> CK3 county pairing is a curated table (PROVINCE_COUNTY), one region
at a time; provinces in the table are verified, the rest are not.

Japan is audited first: CK3 splits it between the Shinto, Mahayana and
Vajrayana faiths (plus the Ryukyuan utaki faith), where the area-basis pass had
set the whole archipelago to one religion.

    python3 tools/provfaiths.py          # print the audit
    python3 tools/provfaiths.py apply    # write the expected religions to tags.db
"""
import os
import re
import sqlite3
import sys

from paths import CK3_GAME

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "tags.db")

# EU4 province id -> CK3 county (Japan, reviewed against the names and the
# geography of both maps; the old provmap.json guesses are corrected here).
PROVINCE_COUNTY = {
    1012: "c_satsuma", 1014: "c_bungo", 1015: "c_ucinaa", 1017: "c_suo",
    1018: "c_izumo", 1019: "c_harima", 1020: "c_yamashiro", 1021: "c_settsu",
    1023: "c_echizen", 1024: "c_echigo", 1025: "c_tokisara", 1027: "c_hitachi",
    1028: "c_musashi", 1029: "c_kai", 1030: "c_owari", 1818: "c_chikuzen",
    1819: "c_tosa", 1820: "c_awa", 1825: "c_aki", 1830: "c_tajima",
    1832: "c_yamato", 1835: "c_mino", 1837: "c_etchu", 1839: "c_totomi",
    1843: "c_kozuke", 4180: "c_hyuga", 4181: "c_higo", 4182: "c_hizen",
    4183: "c_iwami", 4184: "c_bizen", 4185: "c_tango", 4186: "c_iyo",
    4187: "c_kii", 4188: "c_shinano", 4189: "c_sagami", 4190: "c_shimosa",
    4191: "c_shimotsuke", 4192: "c_nushiro", 4359: "c_ise", 4360: "c_mikawa",
    4651: "c_tsushima",
}

# Japanese provinces with no certain CK3 county yet: reported, never guessed.
UNMAPPED = {
    1026: "Mutsu (Tohoku: candidates c_korehari kamuyism, c_iwase/c_isawa/c_iwaki mahayana)",
    4131: "Nanbu (Tohoku: candidates c_isawa mahayana, c_tsugaru kamuyism)",
    1031: "Kamikawa (Hokkaido, unowned)", 1032: "Kurils (Hokkaido, unowned)",
    1847: "Shiribeshi (Hokkaido, unowned)", 1852: "Tokachi (Hokkaido, unowned)",
    4193: "Oshima (Hokkaido, unowned)",
}

_cache = {}


def _county_data():
    """({county: [barony ...]}, {barony: province id}, {province id: rite})."""
    if "d" in _cache:
        return _cache["d"]
    root = os.path.join(CK3_GAME, "common", "landed_titles")
    cnty, bprov = {}, {}
    for fn in sorted(os.listdir(root)):
        text = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
        stack = []
        for m in re.finditer(r"(?m)^(\t*)([bcdke]_[\w-]+)\s*=\s*\{", text):
            depth, tid = len(m.group(1)), m.group(2)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, tid))
            if not tid.startswith("b_"):
                continue
            end = text.find("\n" + "\t" * depth + "}", m.end())
            pm = re.search(r"province\s*=\s*(\d+)", text[m.end(): end])
            c = next((t for _, t in reversed(stack[:-1]) if t.startswith("c_")), None)
            if pm and c:
                bprov[tid] = int(pm.group(1))
                cnty.setdefault(c, []).append(tid)
    prov_rite = {}
    hroot = os.path.join(CK3_GAME, "history", "provinces")
    for f in os.listdir(hroot):
        t = open(os.path.join(hroot, f), encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r"(?m)^(\d+)\s*=\s*\{(.*?)^\}", t, re.S):
            r = re.search(r'^\s*(?:rite|religion|faith)\s*=\s*"?(\w+)', m.group(2), re.M)
            if r:
                prov_rite[int(m.group(1))] = r.group(1)
    _cache["d"] = (cnty, bprov, prov_rite)
    return _cache["d"]


def county_rite(county):
    cnty, bprov, prov_rite = _county_data()
    for b in cnty.get(county, []):
        r = prov_rite.get(bprov[b])
        if r:
            return r
    return None


def expected(pid):
    """(EU4 religion, CK3 rite, CK3 faith) for a table province, else Nones."""
    from faiths import FAITH_RELIGION, ck3_rites

    rite = county_rite(PROVINCE_COUNTY[pid])
    faith = ck3_rites().get(rite)
    return FAITH_RELIGION.get(faith), rite, faith


def db_religions():
    c = sqlite3.connect(DB)
    out = {p: r for p, r in c.execute("select pid, religion from provinces")}
    c.close()
    return out


def verify():
    """Errors/warnings: each table province carries the religion of its CK3 county's faith."""
    err, warn = [], []
    have = db_religions()
    for pid, county in sorted(PROVINCE_COUNTY.items()):
        rel, rite, faith = expected(pid)
        if rite is None:
            err.append(f"province {pid}: CK3 county {county} has no rite on any barony")
        elif rel is None:
            err.append(f"province {pid}: CK3 county {county} follows the {rite} rite (faith {faith}), which no EU4 religion lifts")
        elif have.get(pid) != rel:
            err.append(f"province {pid}: religion '{have.get(pid)}' but CK3 county {county} follows {rite} ({faith}) -> '{rel}'")
    if UNMAPPED:
        warn.append("Japanese provinces not yet matched to a CK3 county (religion not audited): "
                    + "; ".join(f"{p} {n}" for p, n in sorted(UNMAPPED.items())))
    return err, warn


def apply():
    c = sqlite3.connect(DB)
    n = 0
    for pid in PROVINCE_COUNTY:
        rel = expected(pid)[0]
        if rel and c.execute("update provinces set religion=? where pid=? and religion is not ?", (rel, pid, rel)).rowcount:
            n += 1
    c.commit()
    c.close()
    print(f"{n} province religions rewritten in tags.db")


if __name__ == "__main__":
    if sys.argv[1:] == ["apply"]:
        apply()
    have = db_religions()
    for pid, county in sorted(PROVINCE_COUNTY.items()):
        rel, rite, faith = expected(pid)
        flag = "ok " if have.get(pid) == rel else "FIX"
        print(f"{flag} {pid:5} {county:14} {str(rite):12} {str(faith):16} db={have.get(pid)} expected={rel}")
    for e in verify()[1]:
        print("WARN", e)
