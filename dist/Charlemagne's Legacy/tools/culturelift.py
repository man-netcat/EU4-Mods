#!/usr/bin/env python3
"""Ruler-culture pipeline: every tag takes its 867 holder's CK3 culture.

Takes the holder culture as it is (the EU4 culture IS the CK3 culture) and adds the DB row when we don't have
the key yet (tools/cultures.py writes the cultures file from CK3's cultures, so
the culture is its CK3 key).
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
    """The culture key of a CK3 culture, which is its own: the EU4 culture IS the CK3 culture. Repairs the
    DB lookup row; None when CK3 has no such culture."""
    import cultures

    if not ck3cult or cultures.group_of(ck3cult) is None:
        return None
    s = session or db.session()
    s.merge(CultureRow(name=ck3cult))
    if session is None:
        s.commit()
        s.close()
    return ck3cult


def selftest():
    """Every culture the database names must be a CK3 culture."""
    import cultures

    bad = sorted(c for c in cultures.used_in_db() if cultures.group_of(c) is None)
    if bad:
        print("NOT CK3 CULTURES:", bad)
        return 1
    print(f"cultures OK ({len(cultures.used_in_db())} in use)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())


# CK3 rite at 867 -> our religion key: the CK3 faith the rite belongs to (rite_types),
# which is the religion's own key.
from faiths import rite_religion_map  # noqa: E402

FAITH_TO_RELIGION = rite_religion_map()


def ruler_default(title, session=None):
    """The culture of a new tag: its title's 867 holder's CK3 culture."""
    holder, cc = holder_culture(title)
    if not cc:
        print(f"  no holder culture for {title}, keeping land culture")
        return None
    key = ensure_culture(cc, session)
    if key:
        print(f"  {title}: holder {holder} is {cc}")
    return key


def ruler_religion(title):
    """The religion of a new tag: the CK3 faith of its title's 867 holder."""
    _holder, faith = holder_faith(title)
    if not faith:
        return None
    return FAITH_TO_RELIGION.get(faith)
