# Charlemagne's Legacy - install

This package contains the build script and the mod's own files. It contains no
Europa Universalis IV or Crusader Kings III material: the province history, country
files, names, cultures, religions and flags are lifted from your own copies of the
games by the build.

## Needs

* Europa Universalis IV 1.37.* and Crusader Kings III, installed.
* Python 3.10+ with `pip install -r tools/requirements.txt`.

## Steps

1. Put this folder in `Documents/Paradox Interactive/Europa Universalis IV/mod/`.
2. Point the build at the games (the defaults are the author's Steam paths):

       export EU4_GAME="/path/to/Europa Universalis IV"
       export CK3_GAME="/path/to/Crusader Kings III/game"

3. From this folder run `python3 tools/build.py`. It writes the rest of the mod
   here (a minute or so), then run `python3 tools/validate.py` to check it.
4. Enable the mod in the launcher (the `.mod` file next to this folder points at it).

## Not included

Images under `gfx/` (flags, religion and rite icons) are not part of the package, so
new realms show no flag and the religion strips are the base game's until you
add your own art (`python3 tools/faiths.py icons` lifts CK3's faith icons into them
when both games are installed).
