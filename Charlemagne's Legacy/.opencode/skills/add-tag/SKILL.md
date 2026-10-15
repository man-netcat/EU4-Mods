---
name: add-tag
description: Add a new landed tag to Charlemagne's Legacy via tools/tags.db and addtag.py, then rebuild and validate
---

# Add a new landed tag

Source of truth is `tools/tags.db`. Almost every gameplay file is generated — never hand-edit output.

## Workflow

1. Read `AGENTS.md` "Adding a tag (checklist)" plus `tools/addtag.py:1-223`.
2. Pick a free 3-letter code. Check tab-tolerantly against vanilla:
   `grep -rn "^XXX\s*=" /mnt/data/SteamLibrary/steamapps/common/Europa\ Universalis\ IV/common/country_tags/`
   Vanilla uses tabs. Collision silently takes the wrong vanilla tag (BER/Berry precedent).
3. Run from the mod root (`~/.local/share/Paradox Interactive/Europa Universalis IV/mod/Charlemagne's Legacy`):
   `python3 tools/addtag.py TAG ck3_title PID...`
   - Defaults: rank from title tier (`c1/d2/k3/e4`, `tools/addtag.py:30`), capital = first PID, tech western, gov monarchy, name/adj from CK3 loc, culture = 867 holder's CK3 culture via `tools/culturelift.py` (`ruler_default`), religion = capital vanilla religion.
   - Overrides: `--rank/--capital/--tech/--gov/--name/--adj/--file/--culture/--religion/--take/--reuse`.
   - `--to TAG PID...` appends land to an existing tag. `--take` reassigns from current owner. `--culture/--religion` override vanilla values (e.g. english provinces take anglosaxon).
   - If CK3 title has no 867 holder the build fails loudly: fix the title or set `ruler_title` (SAR precedent, lower title).
4. Vanilla tags (SRV, ARM, KRA…): no registration/flag/loc needed, but add the code to `VANILLA_REUSE` in `tools/validate.py:571-592` or the collision guard fails.
5. New tags auto-register in `common/country_tags/00_karolingian_custom.txt` on rebuild. Loc pair goes in `localisation/replace/countries_l_english.yml` before the `HLR:1 "Karolingian Empire"` anchor (UTF-8 with BOM, verify bytes after writing).
6. Diacritics: Latin-1 only on map-visible names (óáúðþ fine, no ž — map font lacks everything above U+00FF). CK3 spellings preferred. Generated files are cp1252 via `tools/enc.py`.
7. Standing rules: provinces keep vanilla culture (no exceptions). Tags take the 867 holder's CK3 culture. Country files keep top-level fields plus the 867 ruler block only; province files keep undated head plus our 867 block on owned land. Reuse vanilla's exact filenames or vanilla merges back in.
8. Flags: never clone placeholders — missing flags stay visibly missing (validate only WARNS). See the add-flag skill and `tools/FLAG_NOTES.md`.
9. Run `python3 tools/build.py && python3 tools/validate.py` — both green before shipping. Never edit `.mod` files while game/launcher runs. Commit only when explicitly asked.
