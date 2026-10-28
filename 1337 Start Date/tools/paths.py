"""Machine paths. Env overrides: EU4_INSTALL or EU4_GAME (EU4 root; only text files are needed), EU5_GAME (EU5 `game` dir).

Cloud: the reference repo has eu4/ and eu5/ (see CLAUDE.md); cloud_setup.sh exports EU4_GAME, and EU5_GAME
is `<reference>/eu5`.
"""
import os
from pathlib import Path

_ref = Path(os.environ.get("EU4_GAME", "")) if os.environ.get("EU4_GAME") else None
EU4_GAME = Path(os.environ.get("EU4_INSTALL") or _ref or "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV")
_eu5 = os.environ.get("EU5_GAME") or (str(_ref.parent / "eu5") if _ref and (_ref.parent / "eu5").exists() else None)
EU5_GAME = Path(_eu5 or "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis V/game")
EU5_MAP = EU5_GAME / "in_game/map_data"
EU5_SETUP = EU5_GAME / "main_menu/setup/1337"
MOD = Path(__file__).resolve().parent.parent
