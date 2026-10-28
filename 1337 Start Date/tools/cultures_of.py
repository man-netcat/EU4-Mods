"""culture -> culture group of the base game's cultures file."""
from paths import EU4_GAME
from pdx import parse


def groups():
    out = {}
    for g, body in parse((EU4_GAME / "common/cultures/00_cultures.txt").read_text(encoding="latin-1")):
        if isinstance(body, list):
            for k, v in body:
                if isinstance(v, list) and k not in ("dynasty_names", "male_names", "female_names"):
                    out[k] = g
    return out
