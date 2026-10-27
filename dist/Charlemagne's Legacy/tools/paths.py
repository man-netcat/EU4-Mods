"""Install locations. Defaults are the author's machine; set the env vars to
build somewhere else (cloud sessions point them at the eu4-ck3-reference clone)."""
import os
from pathlib import Path

MOD = Path(__file__).resolve().parent.parent
EU4_GAME = os.environ.get(
    "EU4_GAME", "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
)
CK3_GAME = os.environ.get(
    "CK3_GAME", "/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game"
)
# Sibling mods (flag sources etc.) live next to this mod's folder.
MODS_DIR = Path(os.environ.get("EU4_MODS_DIR", MOD.parent))
PATRUM = os.environ.get(
    "PATRUM_SCUTA", "/home/rick/Paradox/Workshop/Crusader Kings III/Patrum Scuta"
)


def local_mod_path(p):
    """Re-root a stored absolute path under .../mod/ onto MODS_DIR if it is missing."""
    p = str(p)
    if not os.path.exists(p) and "/mod/" in p:
        alt = MODS_DIR / p.split("/mod/", 1)[1]
        if alt.exists():
            return str(alt)
    return p
