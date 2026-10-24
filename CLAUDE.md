# EU4-Mods

A collection of Europa Universalis IV mods (one folder + `.mod` file each).
`new_mod.py <name>` scaffolds a new one. Game version: EU4 v1.37.5.0.

## Charlemagne's Legacy

The main project. **Read `Charlemagne's Legacy/AGENTS.md` first**: the mod is
generated from `tools/tags.db`, so never hand-edit generated output
(`history/`, `common/countries`, `decisions/Form*`, ...) - change the DB or
tools and rebuild.

```bash
cd "Charlemagne's Legacy"
python3 tools/build.py      # regenerate everything (~5 s)
python3 tools/validate.py   # must end with ALL CHECKS PASSED
```

## Cloud sessions

Vanilla game files are not on the cloud machine. They come from the private
repo `man-netcat/eu4-ck3-reference` (text-only copy of EU4 + CK3, versions in
its `VERSION.txt`; read-only for us).

1. Add and clone it: `add_repo man-netcat/eu4-ck3-reference`, then clone it
   next to this repo (`../eu4-ck3-reference`; shallow clone, one git op at a time).
2. `bash "Charlemagne's Legacy/tools/cloud_setup.sh"` (a SessionStart hook also
   runs this) installs deps from `tools/requirements.txt` and exports
   `EU4_GAME` / `CK3_GAME` pointing at the reference clone via `CLAUDE_ENV_FILE`.
   If the env vars aren't set in your shell:
   `export EU4_GAME=../eu4-ck3-reference/eu4 CK3_GAME=../eu4-ck3-reference/ck3/game` (absolute paths).
3. Build + validate as above. Use the reference to check vanilla tags,
   provinces, cultures, triggers, localisation keys.

Paths are defined in `tools/paths.py` (env overrides: `EU4_GAME`, `CK3_GAME`,
`EU4_MODS_DIR`, `PATRUM_SCUTA`). Don't hardcode machine paths in tools.

### What cloud sessions cannot do

- Run EU4/CK3 or playtest - the owner validates in-game and pastes `error.log`.
- CoA flag baking (`tools/coaflags.py`: needs inkscape, a CK3 save, Patrum
  Scuta workshop files and the user's charges). Uncommitted/custom
  `gfx/flags/*.tga` are the user's own work: never overwrite or delete.
- Update the reference repo (re-copy on game patches is done locally).

## Git

Work on the branch the session names; commit build output together with the
DB/tool change that caused it. Don't open PRs unless asked.
