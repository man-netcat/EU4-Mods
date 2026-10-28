"""Read EU5's 1337 country setup: per-country location sets."""
import re
from collections import defaultdict
from pdx import parse, get, getall
from paths import EU5_SETUP

OWN = ("own_control_core", "own_control_integrated", "own_control_conquered", "own_control_colony",
       "own_core", "own_conquered", "own_integrated", "own_colony")
CTRL = ("own_control_core", "own_control_integrated", "own_control_conquered", "own_control_colony",
        "control_core", "control")
CORE = ("own_control_core", "own_core", "control_core", "our_cores_conquered_by_others",
        "own_control_integrated", "own_integrated")


def countries():
    r = parse((EU5_SETUP / "10_countries.txt").read_text(encoding="utf-8-sig"))
    return get(get(r, "countries"), "countries")


def locset(items, key):
    out = set()
    for b in getall(items, key):
        if isinstance(b, list):
            out |= {v for k, v in b if k is None and isinstance(v, str)}
    return out


def ownership():
    """-> owner[loc], controller[loc], cores[loc] -> set(tags)"""
    owner, ctrl, cores = {}, {}, defaultdict(set)
    for tag, b in countries():
        for k in OWN:
            for l in locset(b, k):
                owner[l] = tag
        for k in CTRL:
            for l in locset(b, k):
                ctrl[l] = tag
        for k in CORE:
            for l in locset(b, k):
                cores[l].add(tag)
    return owner, ctrl, cores
