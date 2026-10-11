# AGENTS.md — instructions for working in this repo

Read this before touching anything. The mod is fully generated: almost every
 gameplay file is output, and hand-editing output is destroyed on the next build.

## Paths on this machine

- Mod: `~/.local/share/Paradox Interactive/Europa Universalis IV/mod/The Karolingians`
  (run all tool commands from here)
- EU4 base: `/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV`
- CK3 base: `/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game`
- Game logs (user's sessions): `~/.local/share/Paradox Interactive/Europa Universalis IV/logs/`
  (`error.log` is per-launch; invaluable for in-game debugging)

## Toolchain

```bash
python3 tools/build.py      # regenerate everything (~2 s warm, ~40 s cold)
python3 tools/validate.py   # all checks, must pass before anything ships
```

- `tools/tags.db` (SQLite) is the source of truth. Tables: `tags`,
  `provinces`, `tag_provinces`, `tag_areas`, `tag_reforms`, `tag_form_areas`,
  `tag_suppress`, `diplomacy`, `cultures`, `religions`.
- `tagdb.py` loads/validates the DB (`selfcheck()` runs on import).
- `eu4.py` writes provinces, countries, flags (clones only), decisions,
  diplomacy, triggers. `step_provinces` **wipes** `history/provinces/` first.
- `ck3.py` resolves 867 rulers/holders/colours from CK3 data (parsed CK3 is
  cached as mtime-keyed pickles in `tools/cache/` — never commit that dir).
- `histgen.py` builds country-history text. `build.py` orchestrates.
- `models.py` is the SQLAlchemy schema, `db.py` the connection,
  `enc.py` transliterates names into cp1252.

## Adding a tag (checklist)

1. Pick a free 3-letter code — check **tab-tolerantly**
   (`grep -rn "^XXX\s*="`, vanilla uses tabs!) or the build collides silently
   with a wrong vanilla tag (this happened with BER/Berry once).
2. Run `python3 tools/addtag.py TAG ck3_title PID...` — it checks the code,
   pulls CK3 name/colour, inserts `tags`/`provinces`/`tag_provinces`/
   `tag_reforms` and the loc pair (`--rank/--capital/--tech/--take` as needed;
   `--to TAG` appends land to an existing tag, `--culture/--religion`
   override vanilla values, e.g. english provinces take anglosaxon).
3. Vanilla tags (SRV, ARM, KRA…) need no registration/flag/loc — but add the
   code to `VANILLA_REUSE` in `validate.py` or the collision guard fails.
   New tags are auto-registered in `00_karolingian_custom.txt` on rebuild.
4. Loc pair in `localisation/replace/countries_l_english.yml` (before HLR).
   Diacritics: Latin-1 only on map-visible names (óáúðþ fine, **no ž** —
   the map font lacks everything above U+00FF). CK3 spellings preferred.
5. Flags: never clone placeholders — missing flags must stay visibly missing
   (validate only WARNS). See `tools/FLAG_NOTES.md` for palette and layout;
   render Illustrator SVGs with inkscape (cairosvg chokes), verify visually.
6. `python3 tools/build.py && python3 tools/validate.py` — both green.
7. If the CK3 title has no 867 holder the build fails loudly: either the
   title is wrong for 867 or use `ruler_title` (a lower title, SAR precedent).

## Formables

- Formable tags live on `formables` (+ `formable_areas`/`formable_provinces`
  for requirements), not on `tags`: they hold no land at the start date.
- Starters point at them via `tags.forms`/`tags.decision`; all starters of
  one formable share a single decision key and get one shared file
  (`decisions/FormX.txt`). HLR's requirement stays dynamic (`empire_core`).
- Gating comes in four flavours: listed starter tags (Hungary, Volhynia,
  Iceland), a primary `culture` (Wales, Sardinia, Poland, England),
  `culture_group`s (Britannia: british, brythonic and gaelic — gaelic
  displays in-game as Celtic), or a `dynasty` (the Karlings alone restore
  the Empire). HLR's custom decision stays handwritten; the table records
  the correspondence.
- A formable may carry rows on `formable_renames` (former tag or culture
  -> loc key shown via `override_country_name`, most-specific first;
  GBR fired by welsh becomes Prydain — the Armenia pattern).
- `formables.percent` (NULL = all) enacts at that share of the requirement
  land, rounded up; `formables.own_capital` additionally requires holding
  the formable's `capital` (which lives on the base `Tag`, like the
  capital of a landed tag). Validate checks the enacted value, the land
  and the capital line in the decision file.
- Tags come in three flavours: `LandedTag` (starts on the map),
  `FormableTag` (requirements, no land), `ReleasableTag` (stub, unused).
- When the base game has its own formation decision for a formable tag,
  the starters suppress it via `tag_suppress` (HUN/POL/ENG/ICE do;
  SAR/VOL/WLS/HLR have no vanilla counterpart).
- New formables need exact requirements (land, starters, percent, capital,
  rank, CK3 title): if the request doesn't give them, ask first — never
  assume them.

## Standing conventions

- Provinces keep **vanilla culture/religion** (standing rule, no exceptions).
- Ranks: 1 county, 2 duchy, 3 kingdom, 4 empire, 5 hegemony (Tang only).
  `MAX_GOV_RANK`, `common/government_ranks/`, `RANK_1..RANK_5` loc and the
  rank-5 rungs in every `government_names` block must stay in sync.
- `government_names` is first-match-wins: specific blocks (abbasid, muslim,
  byzantine, papacy, armenian…) must precede their defaults. It and
  `government_ranks` are `replace_path`ed — the only gov files that load.
- History/provinces/countries/diplomacy/wars/advisors/missions/events/cultures plus
  `gfx/flags` and `common/bookmarks` (single 867 bookmark, keys already in
  `karolingian_bookmark_l_english.yml`) are all `replace_path`ed: no vanilla content loads there.
- No history besides 867.1.1 anywhere: country files keep top-level fields
  plus the 867 ruler block only (`strip_non_867`); every province file keeps
  its undated head only, plus our 867 block on owned land.
  Province/country files must reuse vanilla's **exact filenames** or vanilla's
  version merges back in. Sea tiles are copied verbatim from vanilla
  (`sea_starts`); wasteland the same from the `impassable` block of vanilla
  `map/climate.txt` and lakes from the `lakes` block of vanilla
  `map/default.map` (`waste_ids()`/`lake_ids()` — grey/water, always-visible,
  owned by nobody, so the build asserts no overlap with our land; only tech-group
  `discovered_by` lines survive, dead tags are dropped); every other vanilla
  province gets a visibility-only file (vanilla title comment plus its
  tech-group `discovered_by` lines, gameplay data later); owned provinces
  keep their vanilla tech-group `discovered_by` too, so visibility matches
  the base game everywhere; dead-tag cores are stripped (cores respawn
  tags via rebels/release).
- Localisation: English only, UTF-8 **with BOM** (the game ignores BOM-less
  files — verify bytes after writing). Generated files are cp1252.
- Decision `desc` fields are pure flavour in vanilla style ("Let us…"):
  never mention province counts or province names there. Formable
  decisions carry no bespoke tooltips (HLR alone keeps its own); they
  reference the generated trigger plainly, and validate checks the
  trigger's land against the requirement table.
- Never touch base-game files. Never touch `tools/cache/` contents by hand
  (safe to wipe; bump `_CACHE_VERSION` in `ck3.py` when changing a parser).

## Metadata discipline (has bitten before)

- `The Karolingians.mod` (outer) and `The Karolingians/descriptor.mod`
  (inner) must carry the **same** `replace_path` lines — update both, and
  never edit either while the game/launcher is running (it rewrites the
  outer file and drops the lines).
- Empty replace-dirs (`missions/`, `history/wars/`, `history/advisors/`)
  need `.gitkeep` files or git drops them.
- New CK3 title syntax (hyphenated keys like `d_tao-klarjeti`, `han_XXXX`
  holders, single-line birth/death blocks, commented loc values) is handled
  in `ck3.py` — extend there, not per-tag.

## Workflow

- More doing, less thinking. No bloat: don't add validate notes for
  one-offs; do add guards for recurring bug classes (dead cores, tag
  collisions, unrenderable glyphs, invalid religion keys).
- Commit only when explicitly asked, with prose subjects. The tree should
  be left clean.
- Test evidence beats theory: game logs, `git diff` on generated output
  (optimisations must leave it byte-identical), and in-game confirmation.
- When verifying whitespace-sensitive edits, read the bytes back (repr),
  don't trust tool echoes — tabs and escapes have been mangled in transit
  before.
