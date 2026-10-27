#!/usr/bin/env python3
"""The sovereign states of 867 behind a set of EU4 provinces.

Each EU4 province is tied to a CK3 county (provfaiths.PROVINCE_COUNTY); this
lifts the 867 state that county belongs to:

  holder     the county's 867 holder
  sovereign  the top of the liege chain at 867.1.1: a title's explicit
             `liege =` in its history (CK3 names every vassalage there; 0 or
             none means independent); a character follows the liege of his
             primary title
  primary    the sovereign's primary title: his highest-tier title, ties
             going to the one CK3 loads first (history/titles file order, then
             line) - e.g. Fafan before Berbera and Makhir for Dhidhin
  name       what the state is called in 867: a sunni/shia/kharijite realm of
             duchy rank or above ruled by a dynasty named "...id" is
             "<Dynasty>s" (Shirazids for d_adal's Mirza); everything else
             carries the primary title's name
  vassals    the other holders whose lands fold into the state

Usage:  python3 tools/state867.py [PID ...]    (default: every mapped province
        of the Horn of Africa and Nubia)
Only top-level states come out; their vassals are folded in, not listed.
"""
import collections
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ck3  # noqa: E402
from paths import CK3_GAME  # noqa: E402

_T = ck3.load_titles()
_CH = ck3.load_chars()
_DATE = ck3._date_key("867.1.1")
TIER = {"b": 0, "c": 1, "d": 2, "k": 3, "e": 4, "h": 5}
MUSLIM = {"shafii", "hanafi", "maliki", "hanbali", "ibadi", "sunni_rite", "zaidi", "imami",
          "ismaili", "azariqa", "najdat", "sufri", "nizari", "alawite", "alevi", "ghulat"}


def _parents():
    root = os.path.join(CK3_GAME, "common", "landed_titles")
    par = {}
    for fn in sorted(os.listdir(root)):
        text = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
        stack = []
        for m in re.finditer(r"(?m)^(\t*)([bcdkeh]_[\w\-]+)\s*=\s*\{", text):
            depth, tid = len(m.group(1)), m.group(2)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            if stack:
                par[tid] = stack[-1][1]
            stack.append((depth, tid))
    return par


def _order():
    """title -> (history file, line): the order CK3 loads them in."""
    root = os.path.join(CK3_GAME, "history", "titles")
    out = {}
    for f in sorted(os.listdir(root)):
        if not f.endswith(".txt"):
            continue
        for i, ln in enumerate(open(os.path.join(root, f), encoding="utf-8-sig", errors="replace"), 1):
            m = re.match(r"^([bcdkeh]_[\w\-]+)\s*=\s*\{", ln)
            if m and m.group(1) not in out:
                out[m.group(1)] = (f, i)
    return out


PAR = _parents()
ORDER = _order()
_held = {}


def entries(title):
    out = []
    for head, body in _T.get(title, []):
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", head)
        if m:
            k = ck3._date_key(f"{m[1]}.{m[2]}.{m[3]}")
            if k <= _DATE:
                out.append((k, body))
    return sorted(out, key=lambda x: x[0])


def holder(title):
    try:
        h = str(ck3.holder_at(title, _T))
    except Exception:
        return None
    return None if h in ("None", "0") else h


def liege_holder(title):
    lg = "UNSET"
    for _, body in entries(title):
        m = re.search(r'liege\s*=\s*"?([A-Za-z0-9_\-]+)"?', body)
        if m:
            lg = m.group(1)
    if lg == "UNSET" or lg == "0":
        return None  # CK3 history names every vassalage; no `liege =` is independence
    return holder(lg) if lg[:2] in ("b_", "c_", "d_", "k_", "e_", "h_") else lg


def titles_of(h):
    """The landed titles above barony a character holds at 867 (indexed once)."""
    if not _held:
        for k in _T:
            if k[:2] in ("c_", "d_", "k_", "e_", "h_"):
                holder_ = holder(k)
                if holder_:
                    _held.setdefault(holder_, []).append(k)
        _held.setdefault(None, [])
    return _held.get(h, [])


def primary(h):
    ts = titles_of(h)
    if not ts:
        return None
    best = max(TIER[k[0]] for k in ts)
    return min((k for k in ts if TIER[k[0]] == best), key=lambda k: ORDER.get(k, ("~", 0)))


def sovereign(h, seen=()):
    pt = primary(h)
    if pt is None:
        return h, None
    lh = liege_holder(pt)
    if lh is None or lh == h or lh in seen:
        return h, pt
    return sovereign(lh, seen + (h,))


def _body(char):
    return str(_CH.get(char) or "")


def dynasty_name(char):
    m = re.search(r'dynasty = "?(\w+)"?', _body(char))
    if not m:
        return None
    key = m.group(1)
    dyn = ck3.load_dynasties()
    nm = dyn.get(key) or dyn.get(int(key) if key.isdigit() else key)
    return ck3.loc(nm) if nm else None


def rite_of(char):
    m = re.search(r"rite = (\w+)", _body(char))
    return m.group(1) if m else None


def state_name(sov, title):
    dyn = dynasty_name(sov)
    if TIER[title[0]] >= 2 and rite_of(sov) in MUSLIM and dyn and dyn.endswith("id"):
        return dyn + "s"
    return ck3.loc(title) or title


def states(province_county):
    out = collections.OrderedDict()
    for pid, county in sorted(province_county.items()):
        h = holder(county)
        if h is None:
            continue
        sov, pt = sovereign(h)
        s = out.setdefault(sov, {"sovereign": sov, "primary": pt, "name": state_name(sov, pt),
                                 "provinces": [], "holders": set()})
        s["provinces"].append((pid, county))
        s["holders"].add(h)
    return list(out.values())


if __name__ == "__main__":
    import provfaiths as pf
    want = {int(a) for a in sys.argv[1:]}
    table = {p: c for p, c in pf.PROVINCE_COUNTY.items() if not want or p in want}
    if not want:
        table = {p: c for p, c in table.items()
                 if p in set(range(1205, 1235)) | set(range(2756, 2800)) | {2024, 2324, 4033, 4158, 1217, 1220, 1222, 1225, 2322, 2323, 2797, 2798, 2799}}
    for s in states(table):
        print(f"{s['name']:<14} {s['primary']:<14} sov={s['sovereign']:<14} "
              f"provs={[p for p, _ in s['provinces']]} holders={sorted(s['holders'])}")
