"""Machine paths. Env overrides: EU4_INSTALL (needs the real install, map bitmaps), EU5_GAME."""
import os
from pathlib import Path

EU4_GAME = Path(os.environ.get("EU4_INSTALL", "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"))
EU5_GAME = Path(os.environ.get("EU5_GAME", "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis V/game"))
EU5_MAP = EU5_GAME / "in_game/map_data"
EU5_SETUP = EU5_GAME / "main_menu/setup/1337"
MOD = Path(__file__).resolve().parent.parent
