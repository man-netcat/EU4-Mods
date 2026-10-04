#!/usr/bin/env python3
"""Depth-aware parser for EU4 province history files."""


def parse(path):
    """Return (initial_scalars, initial_cores, all_cores, hre_any)."""
    txt = open(path, encoding="utf-8", errors="surrogateescape").read()
    lines = []
    for ln in txt.splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        lines.append((len(ln) - len(ln.lstrip()), s))

    depth = 0
    started_dated = False
    scalars, cores0, cores_all = {}, [], []
    hre_any = False
    for _, s in lines:
        opens = s.count("{")
        closes = s.count("}")
        m = None
        if depth == 0 and not started_dated and "=" in s and not s.endswith("{"):
            m = s
        if depth == 0:
            if s.split("=")[0].strip().replace("_", "").isdigit() and "=" in s:
                started_dated = True
        if m:
            k, _, v = m.partition("=")
            k, v = k.strip(), re.split(r"#|//", v, 1)[0].strip()
            if k == "add_core":
                cores0.append(v)
                cores_all.append(v)
            else:
                scalars[k] = v
        else:
            for c in re.findall(r"add_core\s*=\s*([A-Z]{3})", s):
                cores_all.append(c)
        if re.search(r"\bhre\s*=\s*yes\b", s):
            hre_any = True
        depth += opens - closes
        if depth < 0:
            depth = 0
    return scalars, cores0, cores_all, hre_any


import re  # noqa: E402  (used by parse)