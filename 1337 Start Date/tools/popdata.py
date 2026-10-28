"""Per-location pop/culture/religion from EU5 06_pops.txt, aggregated per EU4 province via loc2prov."""
import json, re
from collections import defaultdict, Counter
from paths import EU5_SETUP, MOD, EU4_GAME


def location_pops():
    """-> {loc: {'pop': float, 'cul': Counter, 'rel': Counter}}"""
    out = {}
    cur = None
    pat = re.compile(r"size\s*=\s*([\d.]+)\s+culture\s*=\s*(\w+)\s+religion\s*=\s*(\w+)")
    for line in (EU5_SETUP / "06_pops.txt").read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"(\w+)\s*=\s*\{\s*$", line)
        if m and not line.startswith(("\t", " ")):
            cur = out.setdefault(m[1], {"pop": 0.0, "cul": Counter(), "rel": Counter()})
            continue
        m = pat.search(line)
        if m and cur is not None:
            s = float(m[1])
            cur["pop"] += s
            cur["cul"][m[2]] += s
            cur["rel"][m[3]] += s
    return out


def vanilla_cr():
    """EU4 vanilla province id -> (culture, religion) from undated top of history file."""
    out = {}
    for f in sorted((EU4_GAME / "history/provinces").iterdir()):
        m = re.match(r"(\d+)", f.name)
        if not m:
            continue
        top = re.split(r"^\d{3,4}\.\d+\.\d+\s*=", f.read_text(encoding="latin-1"), maxsplit=1, flags=re.M)[0]
        c = re.search(r"^\s*culture\s*=\s*(\w+)", top, re.M)
        r = re.search(r"^\s*religion\s*=\s*(\w+)", top, re.M)
        out[int(m[1])] = (c and c[1], r and r[1])
    return out
