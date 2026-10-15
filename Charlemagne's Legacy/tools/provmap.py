#!/usr/bin/env python3
"""EU4 province -> CK3 title mapper (text only, no pixels).

Compares every EU4 province name against every CK3 barony/county/duchy
title by normalized text, lowest rank first (barony > county > duchy).
Exact matches resolve immediately; everything else becomes a candidate
shortlist for AI adjudication (see adjudicate()).

Outputs (next to this script):
  provmap_candidates.json  {pid: {name, status, pick, candidates}}
  pid/name/status/pick/candidates[{title, rank, ck3_name, dejure, score}]

Usage:
  python3 tools/provmap.py            # build candidate lists
  python3 tools/provmap.py --stats    # match-rate summary only
"""

import difflib
import json
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ck3  # noqa: E402

EU4 = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
OUT = os.path.join(HERE, "provmap_candidates.json")
RANK_OF = {"b": 0, "c": 1, "d": 2}
RANK_NAME = {0: "barony", 1: "county", 2: "duchy"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def eu4_provinces():
    out = {}
    with open(os.path.join(EU4, "map", "definition.csv"),
              encoding="cp1252", errors="replace") as fh:
        for ln in fh:
            parts = ln.rstrip("\n").split(";")
            if len(parts) < 5 or not parts[0].isdigit():
                continue
            out[int(parts[0])] = parts[4].strip()
    return out


def ck3_titles():
    """{tid: {rank, name, county, duchy}} for b/c/d titles + name index."""
    titles = {}
    root = os.path.join(ck3.GAME_CK3, "common", "landed_titles")
    files = sorted(f for f in os.listdir(root) if f.endswith(".txt"))
    for fn in files:
        text = open(os.path.join(root, fn), encoding="utf-8",
                    errors="replace").read()
        stack = []  # (depth, tid)
        for m in re.finditer(r"(?m)^(\t*)([bcdke]_[\w-]+)\s*=\s*\{", text):
            depth = len(m.group(1))
            tid = m.group(2)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, tid))
            if tid[0] not in RANK_OF:
                continue
            chain = [t for _, t in stack[:-1]]
            county = next((t for t in reversed(chain) if t.startswith("c_")),
                          None)
            duchy = next((t for t in reversed(chain) if t.startswith("d_")),
                         None)
            kingdom = next((t for t in reversed(chain) if t.startswith("k_")),
                           None)
            if tid.startswith("b_"):
                pass
            elif tid.startswith("c_"):
                county = tid
            else:
                duchy = tid
            name = ck3.loc(tid)
            titles[tid] = {
                "rank": RANK_OF[tid[0]],
                "name": name,
                "county": county if tid.startswith("b_") else (
                    tid if tid.startswith("c_") else None),
                "duchy": duchy if not tid.startswith("d_") else tid,
                "kingdom": kingdom,
            }
    return titles


def trigrams(s):
    s = f" {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def enrich(ck3t, cands):
    """Add 867 holder + de-jure names so adjudication needs no tool calls."""
    titles = ck3.load_titles()
    for c in cands:
        t = ck3t[c["title"]]
        holder, _ = ck3.holder_at_exact(c["title"], titles)
        names = {}
        for slot in ("county", "duchy", "kingdom"):
            tid = t[slot]
            names[slot] = ck3.loc(tid) if tid else None
        c["holder867"] = holder
        c["dejure"] = names
    return cands


def build():
    eu4 = eu4_provinces()
    ck3t = ck3_titles()
    index = {}
    for tid, t in ck3t.items():
        if not t["name"]:
            continue
        index.setdefault(norm(t["name"]), []).append(tid)

    keys = [tid for tid in ck3t if ck3t[tid]["name"]]
    normkeys = [norm(ck3t[tid]["name"]) for tid in keys]
    buckets = {}
    for tid, nk in zip(keys, normkeys):
        buckets.setdefault(nk[:2], []).append((tid, nk))
    tri = {}
    for tid, nk in zip(keys, normkeys):
        for tg in trigrams(nk):
            tri.setdefault(tg, []).append((tid, nk))
    land = set(json.load(open(os.path.join(HERE, "cache", "provdata.json"),
                             encoding="utf-8"))["provs"])

    def emit(tid, score):
        t = ck3t[tid]
        return {"title": tid, "rank": RANK_NAME[t["rank"]],
                "ck3_name": t["name"], "county": t["county"],
                "duchy": t["duchy"], "score": score}

    sm = difflib.SequenceMatcher()
    result = {}
    for pid in sorted(eu4):
        name = eu4[pid]
        key = norm(name)
        if str(pid) not in land:
            result[str(pid)] = {"name": name, "status": "void", "pick": None,
                                "candidates": []}
            continue
        cands = [emit(tid, 1.0) for tid in index.get(key, [])]
        cands.sort(key=lambda c: ({"barony": 0, "county": 1,
                                   "duchy": 2}[c["rank"]], c["title"]))
        if len(cands) == 1:
            status, pick = "exact", cands[0]
        elif cands:
            status, pick = "ambiguous", None
        else:
            pool = [p for p in buckets.get(key[:2], [])
                    if abs(len(p[1]) - len(key)) <= max(3, len(key) // 2)]
            sm.set_seq2(key)
            scored = []
            for tid, nk in pool:
                sm.set_seq1(nk)
                r = sm.ratio()
                if r >= 0.75:
                    scored.append((r, tid))
            if not scored and key:
                # trigram recall for transliterations (cairo/qahira...)
                votes = {}
                for tg in trigrams(key):
                    for tid, nk in tri.get(tg, ()):
                        if abs(len(nk) - len(key)) > max(4, len(key)):
                            continue
                        votes[tid] = votes.get(tid, 0) + 1
                need = max(2, len(trigrams(key)) // 4)
                sm.set_seq2(key)
                for tid, _ in sorted(votes.items(), key=lambda kv: -kv[1]):
                    if votes[tid] < need:
                        continue
                    nk = norm(ck3t[tid]["name"])
                    sm.set_seq1(nk)
                    r = sm.ratio()
                    if r >= 0.60:
                        scored.append((r, tid))
                    if len(scored) > 60:
                        break
            scored.sort(reverse=True)
            seen = set()
            for r, tid in scored[:8]:
                if tid in seen:
                    continue
                seen.add(tid)
                cands.append(emit(tid, round(r, 3)))
            cands.sort(key=lambda c: ({"barony": 0, "county": 1,
                                       "duchy": 2}[c["rank"]], -c["score"]))
            if not cands:
                status, pick = "unmatched", None
            elif cands[0]["score"] >= 0.9 and (
                    len(cands) == 1 or cands[1]["score"] < cands[0]["score"] - 0.05):
                status, pick = "sure", cands[0]
            else:
                status, pick = "fuzzy", None
        if cands:
            enrich(ck3t, cands)
        result[str(pid)] = {"name": name, "status": status, "pick": pick,
                            "candidates": cands}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    return result


def stats(result=None):
    result = result or json.load(open(OUT, encoding="utf-8"))
    from collections import Counter
    c = Counter(v["status"] for v in result.values())
    print(f"{len(result)} EU4 provinces: {dict(c)}")
    for st in ("ambiguous", "fuzzy", "sure", "unmatched", "void"):
        n = sum(1 for v in result.values() if v["status"] == st)
        print(f"  {st}: {n}")
    return c


if __name__ == "__main__":
    if "--stats" in sys.argv:
        stats()
    else:
        result = build()
        print(f"wrote {OUT}")
        stats(result)
