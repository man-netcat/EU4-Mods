#!/usr/bin/env python3
"""Shared helpers for the verification scripts.

All paths are absolute. Every function returns plain data; the verify
scripts decide pass/fail and print the report.
"""
import importlib.util
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = "/home/rick/Paradox/Mods/Europa Universalis IV/States of the New World"
INSTALL = "/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/States of the New World"
GAME = "/home/rick/Paradox/Games/Europa Universalis IV"
GAME_COUNTRIES = f"{GAME}/common/countries"
GAME_COUNTRY_TAGS = f"{GAME}/common/country_tags/00_countries.txt"
GAME_HIST_CNT = f"{GAME}/history/countries"
GAME_HIST_PROV = f"{GAME}/history/provinces"
GAME_REGIONS = f"{GAME}/map/region.txt"
GAME_COLONIAL = f"{GAME}/common/colonial_regions/00_colonial_regions.txt"
GAME_POSITIONS = f"{GAME}/map/positions.txt"

SEA_AREAS = {
    "caribbean_sea_area", "coast_of_brazil_sea_area", "gulf_of_mexico_area",
    "gulf_stream_area", "hudson_bay_sea_area", "north_pacific_coast_area",
    "sea_of_grau_area",
}

FORBIDDEN = {"ADD","ADM","AND","AGE","ART","AUX","CAR","CAT","CAV","CON","DIP","HAS","HRE","INF",
             "JAM","MIL","MIN","NOT","NUL","PRN","RGB","SUM","VAL","VAN"}


def load_design():
    """Import design.py the same way gen_mod.py does."""
    spec = importlib.util.spec_from_file_location("design", f"{BASE}/design.py")
    design = importlib.util.module_from_spec(spec)
    sys.modules["design"] = design
    spec.loader.exec_module(design)
    return design


def load_america():
    with open(f"{BASE}/america.json") as f:
        return json.load(f)


def load_tribes():
    with open(f"{BASE}/tribes.json") as f:
        return json.load(f)


def load_used_tags():
    with open(f"{BASE}/used_tags.txt") as f:
        return {l.strip() for l in f if l.strip()}


def read(path, enc="utf-8"):
    with open(path, encoding=enc) as f:
        return f.read()


# ---------- vanilla file lookups ----------

def vanilla_hist_files(tag):
    """Vanilla history/countries files whose name starts with this tag.

    Accepts "AZT - Aztec.txt" and the no-space variant "KER- Keres.txt".
    """
    out = []
    for f in os.listdir(GAME_HIST_CNT):
        if f.startswith(tag + " -") or f.startswith(tag + "- "):
            out.append(f)
    return sorted(out)


def vanilla_prov_files(pid):
    """Vanilla history/provinces files for one province id."""
    return sorted(f for f in os.listdir(GAME_HIST_PROV)
                  if re.match(rf"^{pid}\s", f) or f.startswith(pid + " -"))


DISC = b"discovered_by = high_american"
DATED = re.compile(rb"^\d{4}\.\d{1,2}\.\d{1,2}\s*=\s*\{", re.M)


def discovery_copy(vanilla_raw):
    """Vanilla restored province file + the discovery line.

    The line goes BEFORE the first dated history block; if the file has no
    dated block, it is appended at the end.  This is the canonical form both
    apply_discovery.py writes and verify_mod.py expects.
    """
    m = DATED.search(vanilla_raw)
    if m:
        return vanilla_raw[:m.start()] + DISC + b"\n\n" + vanilla_raw[m.start():]
    if vanilla_raw.endswith(b"\n"):
        return vanilla_raw + DISC + b"\n"
    return vanilla_raw + b"\n" + DISC + b"\n"


def vanilla_prov_dev(pid):
    """Sum of base_tax/base_production/base_manpower in the vanilla province file."""
    files = vanilla_prov_files(str(pid))
    if not files:
        return 0
    text = read(f"{GAME_HIST_PROV}/{files[0]}", "latin-1")
    tot = 0
    for key in ("base_tax", "base_production", "base_manpower"):
        m = re.search(rf"^\s*{key}\s*=\s*(\d+)", text, re.M)
        if m:
            tot += int(m.group(1))
    return tot


def gov_rank(tag, dev_total):
    """1444 government rank from development: 3 only for Aztec, 2 >= 20 dev, else 1."""
    return 3 if tag == "AZT" else (2 if dev_total >= 20 else 1)


def parse_country_tags():
    """tag -> def filename, from the vanilla country_tags file (tab-separated)."""
    out = {}
    for line in read(GAME_COUNTRY_TAGS, "latin-1").splitlines():
        m = re.match(r"^\s*(\w+)\s*=\s*\"countries/([^\"]+)\"", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def parse_region_names():
    """Set of region block names in map/region.txt."""
    data = read(GAME_REGIONS, "latin-1")
    return set(re.findall(r"^(\w+_region)\s*=\s*\{", data, re.M))


def parse_colonial_names():
    """Set of top-level colonial region block names."""
    data = read(GAME_COLONIAL, "latin-1")
    return set(re.findall(r"^(\w+)\s*=\s*\{", data, re.M))


def parse_positions():
    """province id -> (x, y) from map/positions.txt (first coord pair)."""
    data = read(GAME_POSITIONS, "latin-1")
    pos = {}
    for m in re.finditer(r"(\d+)\s*=\s*\{\s*position\s*=\s*\{\s*(-?[\d.]+)\s+(-?[\d.]+)",
                         data):
        pos[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return pos


# ---------- mod output helpers ----------

def out_country_files():
    return sorted(os.listdir(f"{OUT}/history/countries")) if os.path.isdir(
        f"{OUT}/history/countries") else []


def out_prov_files():
    return sorted(os.listdir(f"{OUT}/history/provinces")) if os.path.isdir(
        f"{OUT}/history/provinces") else []


def tag_of_country_file(fname):
    """Leading country tag from a history/countries filename."""
    m = re.match(r"^([A-Z]{3})(?: -|- )", fname)
    return m.group(1) if m else None


def owner_of_prov_file(fname):
    """owner = TAG from a generated province file."""
    text = read(f"{OUT}/history/provinces/{fname}")
    m = re.search(r"^\s*owner\s*=\s*(\S+)", text, re.M)
    return m.group(1) if m else None