---
name: lift-vanilla
description: Lift data from vanilla EU4 and CK3 867 sources without hand-copying history or inventing rulers
---

# Lift from vanilla EU4 / CK3

Base paths (never touch base-game files):

- EU4: `/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV`
- CK3: `/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game`
- Run all commands from the mod root.

## Cache discipline

- `tools/cache/` holds mtime-keyed pickles + `provdata.json`; never commit it (`tools/cache/` is gitignored), never edit by hand, safe to wipe.
- CK3 parsers in `tools/ck3.py:58-82` use `_cached()` + `_CACHE_VERSION` (`tools/ck3.py:161`); EU4 province probe in `tools/eu4.py:1367-1547` re-runs when vanilla is newer. Bump `_CACHE_VERSION` whenever you change a parser, or stale pickles survive.
- New CK3 title syntax (hyphenated keys like `d_tao-klarjeti`, `han_XXXX` holders, single-line birth/death, commented loc values) is handled in `tools/ck3.py:28-56,599-623` — extend there, not per-tag.

## EU4 lifts (`tools/eu4.py`)

- Province files: resolve via `vanilla_prov_file()` (`tools/eu4.py:199-208`), keep undated head only (`strip_dated`, `tools/eu4.py:1260-1273`), keep tech-group `discovered_by` only (`take_group_visibility`, `tools/eu4.py:519-529` + `undated_group_visibility`). Drop tag discoveries and dead-tag cores (`strip_dead_cores`, keep `TAGS+HLR`). Reassign with `patch()` (`tools/eu4.py:381-475`), which drops the previous living owner's cores.
- Sea (`sea_starts` in `map/default.map`), wasteland (`impassable` in `map/climate.txt`), lakes (`lakes` in `map/default.map`) are copied verbatim; build asserts no overlap with our land. Everything else unowned gets a visibility-only stub (vanilla title comment + tech-group lines) reusing vanilla's exact filename.
- Map topology: `load_areas` / `load_region_areas` / `load_provinces` (`tools/eu4.py:1444-1515`) scrape `map/area.txt`, `map/region.txt`, `history/provinces/` into `tools/cache/provdata.json` via `step_probe`.
- Country definitions: `load_vanilla_countries()` (`tools/eu4.py:890-908`); `step_vanilla_countries` copies verbatim and swaps only the `color = {...}` line from the CK3 title colour. History files must reuse vanilla's exact filename (`hist_name`, `tools/eu4.py:1310-1324`) or vanilla merges back in; keep top-level fields + 867.1.1 block only (`strip_non_867`).
- Full-file vanilla copies by exact filename (engine override): `common/religions/00_religion.txt`, `common/cultures/00_cultures.txt`, `common/defines.lua`, the four `gfx/interface/*religion*.dds` strips + `interface/countryview.gfx` / `ledger.gfx` / `provinceview.gfx` (frames 29→32). Re-sync all eight religion files on patches; validate guards key set, sprite lists, TGA targets, frame counts (`tools/validate.py:1058-1117`).
- Events/decisions: vendor every vanilla file with tag-specific blocks cut out (`step_events`, `step_filter_decisions`, `tools/eu4.py:1011-1124`; detection = 3-letter tag tokens outside comments). Generic entries stay byte-identical in same-filename files. Hand-curated formation dummies (`VANILLA_FORMATION_FILES`, `tools/eu4.py:944-955`) are skipped by the filter. Our own files use non-vanilla names and are never touched.

## CK3 lifts (`tools/ck3.py`, `tools/culturelift.py`, `tools/histgen.py`)

- Holders: `holder_at_exact()` (`tools/ck3.py:104-125`) takes the latest block ≤ 867.1.1; an exact-date holder overrides a carried one. `resolve()` (`tools/ck3.py:296-328`) fails loudly when a title has no 867 holder — fix the title or set `ruler_title` (SAR precedent), never invent a ruler.
- Loc: `_loc_index()` (`tools/ck3.py:257-277`) scans `localization|localisation/english/**/*.yml` with `key:.."val"`, first-wins. `loc(title)` + `loc(title_adj)` give name/adj. CK3 spellings preferred; map-visible names must be Latin-1 only (no ž, nothing above U+00FF).
- Colours: `load_title_colors()` (`tools/ck3.py:167-226`) walks `common/landed_titles` for `color = {r g b}` or `hsv{h s v}` (converted via hsv_to_rgb×255). Used for country definitions (`histgen.lifted_color`) and `addtag.py` (aborts when the title has no colour).
- Rulers: `ck3_block()` (`tools/ck3.py:691-732`) emits the 867.1.1 monarch/heir with birth/death dates, skills (`stewardship/diplomacy/martial/3` → 1-6), CJK `_[0-9A-F]{4}` suffix stripped, heir = eldest living son→brother→daughter→sister. `step_ck3 --fix` rewrites drift; `no_heir_sync` opts a tag out of heir checks.
- Dynasty: `resolve_dynasty()` (`tools/ck3.py:280-293`) tries `dynasty=` then `dynasty_house=` (with `HOUSE_NAME_OVERRIDE`); a character with neither gets no dynasty in the file — never invent one.
- Cultures: `holder_culture()` walks father/real_father/mother ≤ 3 gens (`tools/culturelift.py:194-241`); `ensure_culture()` maps via `CK3_TO_EU4` and lifts only keys with a `LIFT_SPECS` entry (anchor + display + CK3 `name_lists` file/list). Anything else returns None so the caller keeps the land culture.

## Encodings

- Game-facing output is cp1252 via `tools/enc.py:87-97` (`encname`: passthrough, `_SPECIAL` fold, NFKD, slug fallback) with the `pdx` error handler. Localisation is English-only UTF-8 with BOM — verify bytes after writing; `tools/locfmt.py` normalizes (BOM, LF, one leading space, one trailing newline). Vanilla-key renames (e.g. catholic → Chalcedonian) must live in `localisation/replace/`.
- After any lift: `python3 tools/build.py && python3 tools/validate.py` — both green. Validate checks CK3 ruler/dynasty sync, dead cores, tech visibility, religion keys/strips, and BOM glyphs.
