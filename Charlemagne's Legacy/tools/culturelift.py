#!/usr/bin/env python3
"""Ruler-culture pipeline: every tag takes its 867 holder's CK3 culture.

Maps the holder culture to our EU4 key (CK3_TO_EU4) and lifts the culture
(entry + CK3 names + loc + DB row, Pictish precedent) when we don't have
the key yet (tools/cultures.py writes the cultures file from the base game and
CK3; a new key needs a LIFTS entry there); anything else resolves to None and the caller
falls back to the vanilla province culture.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ck3  # noqa: E402
import db  # noqa: E402
from models import Culture as CultureRow  # noqa: E402

CULT_FILE = os.path.join(HERE, "..", "common", "cultures", "00_cultures.txt")

from cultmap import CK3_TO_EU4  # noqa: E402,F401

_WALK_KEYS = ("father", "real_father", "mother")
_WALK_DEPTH = 3


def _body_value(body, key):
    """Value of a dated-aware character field as of 867.1.1: the latest
    dated change at or before 867.1.1 wins (Boris's birth Tengri vs his
    864 Greek-rite baptism); the undated head value is only the
    start-state fallback."""
    undated, best, depth, cur = None, None, 0, ""
    for ln in body.splitlines():
        s = ln.strip()
        if re.match(r"^\d+\.\d+\.\d+\s*=", s) and depth == 0:
            cur = s.split("=")[0].strip()
        code = ln.split("#", 1)[0]
        opens = code.count("{")
        m = re.match(r'^%s\s*=\s*"?([a-z_0-9]+)"?\s*$' % key, code.strip())
        if m:
            if depth == 0 and undated is None:
                undated = m.group(1)
            elif cur and cur <= "867.1.1":
                best = m.group(1)
        depth += opens - code.count("}")
        if depth <= 0:
            depth, cur = 0, ""
    return best if best is not None else undated


def _holder_with(title, key):
    """(holder id, value at 867) for a title's character field, walking
    up to three generations when the holder's own is unscripted."""
    titles = ck3.load_titles()
    chars = ck3.load_chars()
    holder = ck3.holder_at(title, titles)
    if not holder:
        return None, None
    seen = set()

    def walk(cid, d):
        if not cid or cid in seen or d > _WALK_DEPTH:
            return None
        seen.add(cid)
        body = chars.get(cid)
        if not body:
            return None
        got = _body_value(body, key)
        if got:
            return got
        for key_ in _WALK_KEYS:
            m = re.search(r"(?m)^\s*%s\s*=\s*([A-Za-z0-9_]+)" % key_, body)
            if m:
                got = walk(m.group(1), d + 1)
                if got:
                    return got
        return None

    return holder, walk(holder, 0)


def holder_culture(title):
    """(holder id, CK3 culture at 867) for a title's holder."""
    return _holder_with(title, "culture")


def holder_faith(title):
    """(holder id, CK3 faith at 867) - the character's `rite` entry."""
    return _holder_with(title, "rite")



def file_has(eu4key):
    import cultures
    cultures.ensure()
    try:
        text = open(CULT_FILE, encoding="cp1252", errors="replace").read()
    except FileNotFoundError:
        return False
    return bool(re.search(r"(?m)^[ \t]*%s = \{" % re.escape(eu4key), text))


def have_culture(eu4key):
    if eu4key is None or not file_has(eu4key):
        return False
    s = db.session()
    found = s.get(CultureRow, eu4key) is not None
    s.close()
    return found


def ensure_culture(ck3cult, session=None):
    """EU4 key for a CK3 culture: repair the DB row when the key exists,
    lift the whole culture when it doesn't (needs a tools/cultures.py LIFTS entry),
    else None so the caller falls back to the land culture. Pass the
    caller's session when one already holds the database: a second
    connection deadlocks against an uncommitted write (the addtag
    --take-then-lift crash)."""
    eu4key = CK3_TO_EU4.get(ck3cult) if ck3cult else None
    if eu4key is None:
        return None
    if not file_has(eu4key):
        print(f"  {ck3cult} -> {eu4key}: not in tools/cultures.py LIFTS, keeping land culture")
        return None
    s = session or db.session()
    s.merge(CultureRow(name=eu4key))
    if session is None:
        s.commit()
        s.close()
    return eu4key


def selftest():
    """Every mapped value must exist in our cultures file (direct check:
    substring key lists lie, e.g. catalan contains alan)."""
    text = open(CULT_FILE, encoding="cp1252", errors="replace").read()
    bad = sorted(
        {v for v in CK3_TO_EU4.values() if not re.search(r"(?m)^[ \t]*%s = \{" % v, text)}
    )
    if bad:
        print("UNDEFINED EU4 KEYS:", bad)
        return 1
    print(f"map OK ({len(set(CK3_TO_EU4.values()))} keys defined)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())


# CK3 rite at 867 -> our EU4 religion key: through the CK3 faith the rite
# belongs to (rite_types), lifted by exactly one EU4 religion (see
# faiths.FAITH_RELIGION). No approximations: a tag never gets a religion that
# is a different CK3 faith than its ruler's.
from faiths import rite_religion_map  # noqa: E402

FAITH_TO_RELIGION = rite_religion_map()


def ruler_default(title, session=None):
    """EU4 culture for a new tag from its title's 867 holder (None to
    fall back to the vanilla province culture)."""
    holder, cc = holder_culture(title)
    if not cc:
        print(f"  no holder culture for {title}, keeping land culture")
        return None
    eu4key = ensure_culture(cc, session)
    if eu4key:
        print(f"  {title}: holder {holder} is {cc} -> {eu4key}")
    return eu4key


def ruler_religion(title):
    """EU4 religion for a new tag from its title's 867 holder's faith
    (None to fall back to the vanilla province religion)."""
    _holder, faith = holder_faith(title)
    if not faith:
        return None
    return FAITH_TO_RELIGION.get(faith)
