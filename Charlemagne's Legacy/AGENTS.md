# AGENTS.md — instructions for working in this repo

Read this before touching anything. The mod is fully generated: almost every
 gameplay file is output, and hand-editing output is destroyed on the next build.

## Paths on this machine

- Mod: `~/.local/share/Paradox Interactive/Europa Universalis IV/mod/Charlemagne's Legacy`
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
  `tag_suppress`, `diplomacy`, `rivalries`, `friendships`, `core_deny`,
  `cultures`, `religions`.
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
   pulls CK3 name/colour, takes the 867 holder's CK3 culture as the tag
   culture (lifting it via `tools/culturelift.py` when we lack the key —
   only mapped keys with a lift spec; `--culture` still overrides), and
   inserts `tags`/`provinces`/`tag_provinces`/
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
   Two distinct paths, never mixed: a user-named charge SVG from
   `/home/rick/Downloads/charges/` pasted on a flat tincture (placed by
   hand, not through `coaflags.py`), or a CK3 CoA bake via
   `tools/coaflags.py` (title/dynasty block, shader, tincture canon).
   Uncommitted `gfx/flags/*.tga` are the user's own work by default: never
   overwrite or delete a flag without permission.
6. `python3 tools/build.py && python3 tools/validate.py` — both green.
7. If the CK3 title has no 867 holder the build fails loudly: the title
   must be wrong for 867. `ruler_title` is deprecated - every tag MUST sit
   on a real CK3 title; selfcheck fails a tag without `ck3_title`, and its
   declared `rank` must equal the title's tier (c=1, d=2, k=3, e=4, h=5).

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
  the Empire). A fifth, `home_capital`, requires the firing tag's capital
  to sit inside the requirement land instead of holding a fixed capital
  (Denmark, and Norway/Sweden when they come); it excludes `own_capital`.
  A sixth, `exclusive`, makes listed starters mutual rivals: each may fire
  only once the others are gone (Galicia-Volhynia: Halych/Volodymyr).
  HLR's custom decision stays handwritten; the table records the correspondence.
  FIN's same-tag kingdom is custom the same way (`decisions/FinlandKingdom.txt`:
  crown in place below kingdom rank, or proclaim when FIN is gone); no
  formable row, the triggers are hardcoded specs like the HRE one.
  ROM's restoration is custom too (`decisions/FormROM.txt` carries vanilla's
  behaviour at hegemony rank); HLR fires it through its tag, BYZ starts it.
- Iberian formables (lifted from CK3's de jure counties under e_spain, 75%, own capital):
  LEO k_leon (ASU, GAL), CAS k_castille (CST, BGS, VLL), ARA k_aragon (ARG, GTH),
  POR k_portugal (PRT; its capital Lisboa lies in k_badajoz de jure, so 227 is added to the land),
  VAL k_valencia (MLR), BDJ k_badajoz (TOL), SPA e_spain (ADU, NAV; kings only).
  A tag has one `forms`, so Asturias takes Leon and cannot also take Spain. Leon is LEO, not LON
  (vanilla London). `events/IberianKingdoms.txt` still crowns Leon and Portugal by event.
  ARA BDJ CAS SPA VAL carry placeholder flags (`tools/placeholder_flags.py`: tag colour on one diagonal, black on the other,
  never overwrites; delete one to bake the real flag; `placeholder_flags.py --list` and validate list every flag still a placeholder). LEO.tga is a copy of the old LON.tga.
- Iberia leans native: `events/IberianInstability.txt` (four one-shot events that fray the Emirate of Cordoba: Muladi,
  Berber, Mozarab, succession; modifiers in `common/event_modifiers/kar_iberia_modifiers.txt`) and
  `missions/Reconquista.txt` (hand-written Reconquista trees for ASU/LEO, NAV and CST: claims, vigour, prestige). Never playtested.
- A formable may carry rows on `formable_renames` (former tag or culture
  -> loc key shown via `override_country_name`, most-specific first;
  GBR fired by welsh becomes Prydain — the Armenia pattern).
- `formables.percent` (NULL = all) enacts at that share of the requirement
  land, rounded up; `formables.own_capital` additionally requires holding
  the formable's `capital` (which lives on the base `Tag`, like the
  capital of a landed tag) and moves the seat there on formation
  (`set_capital`, Somalia precedent). Validate checks the enacted value, the land
  and the capital line in the decision file.
- Tags come in three flavours: `LandedTag` (starts on the map),
  `FormableTag` (requirements, no land), `ReleasableTag` (stub, unused).
- When the base game has its own formation decision for a formable tag,
  the starters suppress it via `tag_suppress` (HUN/POL/ENG/ICE/IRE do;
  SAR/VOL/WLS/HLR have no vanilla counterpart). Neutralization is by
  same-filename dummy (`VANILLA_FORMATION_FILES`): duplicate keys coexist
  across files, so stubs in our own files never win — and anything else in
  those vanilla files dies with them.
- New formables need exact requirements (land, starters, percent, capital,
  rank, CK3 title): if the request doesn't give them, ask first — never
  assume them.

## Rites (religious schools)

CK3's rites are EU4 religious schools in every religion group the mod uses
(christian, muslim, eastern, dharmic, pagan, zoroastrian_group - 52 rites).
The Islamic rites REPLACE the base game's Islamic schools (same keys for
hanafi/hanbali/maliki/shafii/ismaili/jafari/zaidi, so vanilla scripts keep
working). `tools/rites.py` holds the tables (RITES: group, key, CK3 rite,
name, desc, one modifier, placeholder colour; RITE_RELIGIONS: which EU4
religion follows each rite) and `build.py` regenerates from it: one
`religious_schools` block per group between BEGIN/END RITES markers in
`common/religions/00_religion.txt`, `common/static_modifiers/karolingian_rites.txt`,
`common/scripted_effects/karolingian_rites.txt`, `interface/karolingian_rites.gfx`
and `localisation/replace/karolingian_rites_l_english.yml` - edit the tables,
never those outputs.

Tags inherit their 867 CK3 holder's religion AND rite: a country starts with
the school of its holder's `rite` (`religious_school = X_school` in country
history), and validate fails when the tag's EU4 religion is not one of the
rite's religions (fix `tags.db`, never add a fallback or exception). Validate
also fails when a religion the mod uses (tags or provinces) has no rites, when
a ruler has no rite / a rite without a school, when an output was hand-edited,
or when a religion icon is missing, out of range or blank in the four strips.
Rite icons `gfx/interface/icon_rite_<key>.tga` are generated PLACEHOLDERS only
when missing (validate lists them by name as warnings): drop the real CK3 rite
icons in under the same names and they are kept; a missing file fails.
In-game text says "Rite" / "Clergy" / "Cleric"; the engine's shared school UI
strings (also used by Islam) are left alone.
The rule moved three tags onto their ruler's religion: KTN (Khitans) mahayana
(avatamsaka rite), DNI (Kizilyedisan) taltosist (magyar_pagan), KSG (Kashyar)
khurmazdis (khurmazta); the older "Khitan tengri" note below no longer holds for KTN.

## Religions are CK3 faiths

A religion IS a CK3 faith under CK3's own key (`christian_faith`, `sunni`, `norse_pagan`); there is no
CK3->EU4 table. `common/religions/00_religion.txt` is written by `tools/religions.py`: one block per faith
tags.db names, each copying the mechanics of a base-game block (`religions.TEMPLATE`, `EDITS`), in the group
CK3's religion family gives. A tag's religion is the faith its 867 ruler's rite belongs to (rite -> faith via
CK3's `rite_types`; `culturelift.FAITH_TO_RELIGION` is derived) - no approximations: Balhae's Vinaya rite is Mahayana, not Theravada). Name and map
colour come from CK3's faith (`python3 tools/faiths.py` sets them and creates
missing religions by cloning a block, e.g. shaivism/vaishnavism from hinduism
and achamanism from animism, with a placeholder icon frame); the icons are the
CK3 faith icons and need the CK3 install: run `python3 tools/faiths.py icons`
locally (overwrites each religion's frame in the four strips and replaces the
placeholder rite icons `gfx/interface/icon_rite_<key>.tga` with CK3's rite icons,
resized to 64x64; a rite icon that is no placeholder is kept unless `--force`). Validate fails on
a used religion that is not a lifted faith, a wrong colour or name, a shared
icon frame, a missing/blank icon, and lists placeholder icons by name. A faith
nobody needs may stay unmapped (qarmatian); map it when a tag or province needs it.

## Province religions audited against CK3 counties

`tools/provfaiths.py` pairs EU4 provinces with CK3 counties (curated, a region at
a time - Japan so far) and validate fails when a paired province's religion is
not its county's faith (county capital barony `rite` in
`history/provinces` -> faith). `python3 tools/provfaiths.py`
prints the audit, `... apply` writes the expected religions to `tags.db`.
Provinces it cannot pair with certainty (`UNMAPPED`) are listed, never guessed.
The old `provmap.json` auto-matches were wrong for eight Japanese provinces
(Kyoto, Awa, Aki, Mino, Kai, Okinawa, Dewa, Ugo) and are corrected there.

## Lifting a region's 867 states

`tools/liftstates.py REGION [apply]` turns a region into tags: every EU4 province in
`provfaiths.PROVINCE_COUNTY` goes to the state its CK3 county belongs to at 867 -
the holder's `liege =` chain followed to the top, the top liege (the sovereign)
receiving the province with all its vassals folded in; independent counts and
dukes are states of their own, and so are tributaries (`tributary_of`, which is no
`liege =`; their suzerain is only a relationship). `state867.py` does the grouping.
The province pairing is name inference, a curated table per region (India: 251
provinces; the four with no county of that name go to the nearest province's county - no province stays uncolonized). New tags get codes
from their names, the tag religion and culture follow the ruler, province religions
follow the CK3 county's faith. Afterwards: `culturetitles.py TAGS` for the title
ladders, `culturalnames.py apply TAGS`, build, validate.
A state that is a base-game country keeps that country's code: `tools/retag.py NEW VANILLA`
moves a tag (every table, the loc pair, tag-gated title blocks, VANILLA_REUSE) onto the
vanilla tag (BEL -> BNG, Bengal); it renames the tag's flag file with it (and refuses only if the
target flag already exists). Delete the old code's generated history/common country files after.

Base-game flags are never reused, in any situation: `gfx/flags` is replace_path'd, a tag
that takes a vanilla code (BNG, SND ...) has no flag until it gets its own, `flag_from` (copy
a vanilla flag) is gone from the build and validate fails on it, and validate fails where the
install is present if a flag file equals one of the base game's.

## Standing conventions

- Provinces follow CK3: every owned province is paired with a CK3 county (`provfaiths.PROVINCE_COUNTY`)
  and takes that county's CK3 culture and faith (as they are); the Azores, which CK3 lacks, keep their own.
  Japan's `japanese` (shown Yamato) and `togoku` (shown Emishi) cultures follow the same rule. The
  `norse_pagan_reformed`, `slavic`, `romuva` and `suomenusko` religions are lifted from CK2/CK3
  faiths (867 unreformed names/colours/icons; descs are ours). They live in
  `common/religions/00_religion.txt`, a full vanilla copy with the three
  appended to the pagan group (Norse-clone mechanics, small thematic
  country bonus, no personal deities). Engine file-override is by exact
  filename, so per the wiki recipe the four vanilla DDS strips are
  extended in place (same filenames, uncompressed 32-bit RGBA exactly
  like vanilla) with the new icons as frames 30-32, and
  `interface/countryview.gfx` (three sprites) plus `interface/ledger.gfx`
  and `interface/provinceview.gfx` (one each) are full vanilla copies
  with `noOfFrames` 29→32 — miss any strip/sprite and icons shift (the
  classic bug). Re-sync all eight files against the
  base game on patches; validate guards the vanilla key set, both sprite
  lists, the TGA targets and the frame counts.
  `common/subject_types/00_subject_types.txt` is an exact-filename vanilla
  copy with only one gameplay edit: vassal `max_government_rank` 1→0 — the
  engine clamps subjects down to their subject type's cap, and CK3-true
  vassals hold duchy titles (rank follows titles, not vassalage); unions and
  tributaries inherit vanilla's no-limit. Re-sync on patches; validate guards
  the delta.
  New religions go in via `tools/addreligion.py` (block clone, loc,
  registry, CK3 icon decode onto all four strips by row, gfx frame
  counts - one idempotent call; hand-edit only what it cannot do).
  Steppe + Khitan + Avar remnant `tengri_pagan_reformed`; Magyars
  `taltosist` — CK3's own faith (pagan group, CK3 name/colour/icon) on
  Etelköz;
  Armenia/Georgia highlands `coptic`; central Bosnia (140, 3002)
  `krstjani` — CK3's own Bosnian-Church faith (christian group, CK3 name,
  colour, icon and desc) under Slavic RSK/ZAH; Muslims `sunni`;
  rest `catholic`, displayed as Chalcedonian
  (`localisation/replace/karolingian_religion_l_english.yml` — note:
  same-key loc conflicts resolve vanilla-side on this install, so vanilla
  renames must live in `localisation/replace/`). The Christian set is
  closed at `catholic` + `krstjani` + `apostolic` + `nestorian`: no
  Latin/Byzantine rite splits (Carolingian/Roman/Ambrosian
  were in communion in 867; splitting would gut the papacy/HRE/crusade
  mechanics, all keyed to the single entry — rites belong in the school
  mechanic if ever; the Church of the East and the Armenian Apostolic
  Church were never in communion, so they stand outside the closure). Where CK3's
  ruler differs from the population the tag keeps the ruler faith on foreign
  land: YRK/KIE/NOV Norse tags on catholic/slavic land, CRT Sunni tag on
  catholic Crete, MRW Sunni tag on coptic Erzurum. Per-province refinement later.
  Tags take their **867 holder's CK3 culture** instead (`culturelift.py`
  maps and lifts on demand; a starter whose ruler culture misses the
  formable gate fails `selfcheck` — drop the starter link or keep the
  land culture).
- Culture government titles lift from CK3 via `tools/culturetitles.py`.
  Rerunning `python3 tools/culturetitles.py` bare is the routine pass:
  it covers **every tags.db tag** (rank, `ck3_title`, culture and
  ruler faith read from the DB; `selfcheck` enforces `ck3_title` and
  `rank == the title's tier`). Tags an already-written block covers
  (a trigger naming the tag, the culture key or the culture group;
  `default_*`/`muslim_monarchy`/`hre_county` never count) are skipped —
  deliberate hand flavor wins. The rest group per our culture key
  (tags.db `culture` may hold a CK3 id *or* the lifted EU4 key; the
  resolver reverse-maps and disambiguates collisions through the 867
  title holder's own CK3 culture) into
  `<key>_titles` blocks — trigger `primary_culture = key`, or a tag
  OR-list when the key is not one of ours — inserted into
  `zz_kar_government_names.txt` before `muslim_monarchy`, with
  `<CULTURE>_<TIER>[_MALE/_FEMALE]` loc appended to
  `title_names_l_english.yml` (fresh keys only). A tag whose pick-set
  diverges (title-bound specials, religion split) gets its own
  `<key>_<TAG>_titles` block with suffixed keys, placed first.
  CK3's government gate is read from the title's own history at 867
  (Byzantine themes are administrative, so their Greek counts read
  Tourma while feudal Greek Napoli reads County/Count); titles CK3
  leaves to the engine fall back to the EU4 government mapping
  (tribal→tribal, theocracy→ecclesiastical ids, republic→republic,
  muslim monarchies clan+feudal, the rest feudal); `--govs` merges
  extras (Roman heirs). The build writes the resolved government into
  country history as a `kar_gov_*` start flag, so a culture spanning
  several CK3 governments (greek: feudal vs administrative) gates its
  shared ladder on it.
  Gates that cannot be verified in EU4 scope (contract flags, faiths,
  `de_jure_liege`) are skipped, never guessed; rites resolve to their
  parent religion; heirs print SHAHZADE at ranks 2+ for islam realms
  and HEIR otherwise; consorts reuse the ruler form; missing slots fall
  back to vanilla keys. Re-running is idempotent. Hand-polish only what
  lift output lacks (rare heir/consort specks — CK3's spouse rules are
  culture-specific, e.g. korea, and stay unlifted).
- Ranks: 1 county, 2 duchy, 3 kingdom, 4 empire, 5 hegemony (Tang only).
  `MAX_GOV_RANK`, `common/government_ranks/`, `RANK_1..RANK_5` loc and the
  rank-5 rungs in every `government_names` block must stay in sync.
- `government_names` is first-match-wins: specific blocks (abbasid, muslim,
  byzantine, papacy, armenian, magyar principality, norse, tribal chiefdoms,
  russian principalities, petty kingdoms, gaelic, welsh, brythonic petty
  kingdoms, croatian…) must precede their defaults. It and
  `government_ranks` are `replace_path`ed — the only gov files that load.
- History/provinces/countries/diplomacy/wars/advisors/missions/cultures plus
  `gfx/flags` and `common/bookmarks` (single 867 bookmark, keys already in
  `karolingian_bookmark_l_english.yml`) are all `replace_path`ed: no vanilla content loads there.
- Vanilla events load as-is except tag-specific ones: `step_events` vendors
  every vanilla event file into `events/` with any event naming a tag cut
  out (detection is automatic: 3-letter tag tokens outside comments). Our
  own event files use non-vanilla names and are never touched. Effect
  blocks scoped to a bare province id (`1943 = { ... }`) take no `limit`
  child (the engine rejects the block and drops surrounding effects —
  this killed the first settlement): condition province work with
  `if = { limit = { 1943 = { ... } } }` (Brazil precedent) or use area
  scopes, which do take limits (GOT/Norway precedent).
- Same for vanilla decisions (`step_filter_decisions`, hand-curated
  formation dummies excepted): tag-specific decisions go, generic ones
  stay byte-identical in same-filename files.
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
  tags via rebels/release). Reassigning land drops the previous living
  owner's cores (`patch()`), and judged-dormant claims go in `core_deny`
  (holder, owner) pairs, enforced by validate. Dormant cores for future
  releasables live in `seed_cores` (Dublin on Sudreyjar-held Dyflin:
  rebels or a manual release wake it, no scripted path needed). Forts exist only where the
  database says so (`provinces.fort`, stone-walled cities still garrisoned
  in 867: Constantinople, Rome, Alexandria, Damascus, Thessaloniki, Xi'an,
  Belgrade, Diyarbakir, Toledo, Jerusalem, Antioch, Baghdad) — everything
  else is stripped, capitals included unless specifically listed; validate
  enforces both directions. Targeted conquest claims
  use the same writer: ASU/NAV on Andalusi Iberia, ASU on Porto/Braganca,
  MGY on the HUN basin (CK3's Hungarian-migration CB as claims plus the
  existing HUN path). MGY fights under the MGY-only
  `magyar_horse_lords_reform` (tier-1: cavalry power and cost, flat force
  limit aiming ~20 total, maintenance cover; first-pass numbers for the
  balance pass) and marches behind the starting general
  Kurszán (6 shock, dead 904); formation strips the reform for feudalism,
  so settled Hungary keeps the standard pick. Etelkoz is Magyar-held at
  the start (MGY's demesne on all six provinces); three Pecheneg tags
  (YED, ODS, DNI, under CK3's
  d_yedisan, c_odessa and c_lower_dniepr shares) hold nothing until the
  migration releases them Jerusalem-style (tagdb DORMANT: cores seeded on
  the abandoned demesne, then `release` creates the countries - DNI's
  duchy has no 867 holder so it rules through c_odessa, the SAR
  ruler_title precedent; YED shares Almos's line with MGY, which is
  mechanically inert). HUN's sole starter MGY is kingdom-ranked, so the
  formable carries `rank_required = 3` (the Scandinavia kings-only pattern;
  the generic non-kingdom gate would leave Hungary unformable). `rank_required = -1`
  drops the rank gate entirely (ARM: its kingdom-ranked starter APR forms a kingdom). The AI
  forms through `magyar_settlement.2` (same file), which mirrors the
  decision's effect the moment its conditions hold; the player fires the
  decision by hand. Settling is one effect, not an MTTH event:
  `kar_magyar_settlement_effect` (basin flips, dormant releases, steppe
  flips) runs at the end of the crown effect and of `FormHUN`, so every
  path settles in the same tick it crowns: Avar basin provinces turn
  magyar/taltosist and the steppe host pecheneg/tengri_pagan_reformed
  (CK3's two culture flips); the demesne is released to them there (1943,
  1944 and 4540 to YED, 282 to ODS, the old capital 283 and 2406 to DNI;
  each release is guarded on its cores and backed by Funj-style cedes, so
  lost land degrades gracefully), so HUN keeps the Basin only,
  unconditionally. An MGY victory over a basin
  holder fires `magyar_settlement.3` through `on_war_won`
  (`common/on_actions/MagyarOnActions.txt`, an additive merge with
  vanilla's on-actions carrying only our guard), which completes the basin
  held by BUL and its vassals TRA, VSG and TEM (Balaton stays out) and
  crowns at once; the shared crown body lives in
  `common/scripted_effects/MagyarEffects.txt`. Formation fires the
  settlement deterministically (`country_event` at the end of the effect
  and of `FormHUN`, never the MTTH alone). The settlement also repairs
  Hungary to magyar/taltosist if anything flipped it, and strips HUN and
  dead MGY cores off the released land. All vanilla `release` precedents
  free a single tag; three releases in one effect is uncharted - if only
  the first successor appears in-game, split them into chained events.
- Localisation: English only, UTF-8 **with BOM** (the game ignores BOM-less
  files — verify bytes after writing). Generated files are cp1252.
- Decision `desc` fields are pure flavour in vanilla style ("Let us…"):
  never mention province counts or province names there. Formable
  decisions carry no bespoke tooltips (HLR alone keeps its own, plus HUN's
  migration tooltip); they
  reference the generated trigger plainly, and validate checks the
  trigger's land against the requirement table.
- Never touch base-game files. Never touch `tools/cache/` contents by hand
  (safe to wipe; bump `_CACHE_VERSION` in `ck3.py` when changing a parser).

## Metadata discipline (has bitten before)

- `Charlemagne's Legacy.mod` (outer) and `Charlemagne's Legacy/descriptor.mod`
  (inner) must carry the **same** `replace_path` lines — update both, and
  never edit either while the game/launcher is running (it rewrites the
  outer file and drops the lines).
- Empty replace-dirs (`missions/`, `history/advisors/`)
  need `.gitkeep` files or git drops them. `history/wars/` instead holds
  our preset start-date wars, one file per war (CK3's Iberia opens at
  war: Alfonso's invasion ASU vs ADU over Andalusia, with ASU claims on
  Porto/Braganca written by the Reconquista claims rule; the Andalusian
  Rebellion independent PRT+TOL vs ADU for independence; the Magyar
  migration MGY vs BUL/TRA/VSG under the custom `cb_magyar_migration`
  (humiliate's peace table: gold and humiliate only, so no land changes
  hands in the deal and the settlement event allocates everything)
  — no subjects fight overlords, so all use proven mechanics). The opening
  war would be unwinnable on paper (dev 17 against 207), so MGY marches
  behind Kurszán (6 shock) under the horse-lords reform, and musters on
  `on_startup` with a 500-ducat chest plus tradition for instant
  mercenaries - regular stacks on day one, no MTTH, no rebels. A bespoke
  all-cavalry `merc_magyar_horse` company (tag-gated, first-pass rate and
  bonus) gives them unique swords to hire. Unique special cavalry
  (`magyar_horse_regiment` + `create_unit_forcelimit_percentage` at 100%
  in the same `on_startup`, Cossack pattern) musters beside them, for a
  ~30-strong host all told (Ibn Rustah's 20,000 horse, rounded up).
  Validate guards live sides
  and real CBs. Crash lesson (Oct 2026, SIGSEGV in
  `CWar::AddAttacker`→`CProvince::AddAsClaim`, see `crashes/` dumps):
  conquest-family goals (`take_claim`, `take_border`) need
  `province = <claimed pid>` — vanilla never uses `tag` there and the
  claim lookup segfaults without it; throne/independence-capital goals
  use `tag = <country>`. The table carries both (`goal_tag` xor
  `goal_province`, enforced by selfcheck).
- New CK3 title syntax (hyphenated keys like `d_tao-klarjeti`, `han_XXXX`
  holders, single-line birth/death blocks, commented loc values) is handled
  in `ck3.py` — extend there, not per-tag.

## Workflow

- More doing, less thinking. No bloat: don't add validate notes for
  one-offs; do add guards for recurring bug classes (dead cores, tag
  collisions, unrenderable glyphs, invalid religion keys).
- Never carve an exception (override table, allowlist, hand-authored
  deviating value) without consulting the user first — if the resolver
  disagrees with the data, suspect the resolver, not the data.
- Commit only when explicitly asked, with prose subjects. The tree should
  be left clean.
- Test evidence beats theory: game logs, `git diff` on generated output
  (optimisations must leave it byte-identical), and in-game confirmation.
- When verifying whitespace-sensitive edits, read the bytes back (repr),
  don't trust tool echoes — tabs and escapes have been mangled in transit
  before. Conditional generated blocks must anchor mid-line
  (`...10{magyar_swap}`, value starting in `\n`): a conditional on its own
  template line emits a blank line when empty.

## Tag names are derived from CK3 at build time (`tools/tagloc.py`)

No CK3 text is stored: the build step "lift tag names from CK3" writes every
tag's name and adjective into `countries_l_english.yml` as CK3 shows the title
at 867.1.1. Order: (0) dynasty-named realms (duchy or higher, holder of
Arabic/Berber/Iranian heritage, government with `dynasty_named_realms = yes`,
title not opted out: "Abbasids", "Samanids"); (1) the latest dated `name =` /
`set_title_name =` in `history/titles` (WEST_FRANCIA, NEUSTRIA, dynn_title_tang);
(2) the cultural name for the holder's culture; (3) the title's own loc.
`$key$` resolved, steppe people suffix, folded to EU4's font. The only per-tag
choices are the `STYLE` table (Great Tang, The Papacy, Balhae). Never hand-edit
the loc lines. `python3 tools/tagloc.py [TAG..]` explains a name; validate
fails on a stale line. The dynasty rule is inferred (CK3's culture gate for
dynasty-named realms is engine code): fix the rule, not single tags.

## Regions lifted by name inference

`tools/liftstates.py` has one entry per lifted region (`china`, `maritime`, `westafrica`,
`eastside`, `manchuria`, `seasia`, `india`); each needs its provinces in `provfaiths.PROVINCE_COUNTY`.
After `apply`: `python3 tools/retag.py suggest SEQ` lists tags whose name is a free
base-game tag (then `retag.py OLD NEW ...`, which also takes the vanilla tech group and
removes the old code's history), `python3 tools/synctags.py apply` moves every tag onto its
ruler's culture and faith, `python3 tools/provfaiths.py apply` fixes province religions,
`python3 tools/culturetitles.py TAG..` adds the title ladders validate asks for, and a CK3
faith the file lacks is added through a `religions.TEMPLATE` entry and a
`rites.RITES` row. Provinces in places CK3 does not cover (Madagascar, Mozambique and the
Zambezi, South Africa, Kongo, the Great Lakes, Cameroon and Gabon, Yakutia to Kamchatka) stay
unowned, like the New World and Australia.

## Korea: Silla, its breakaways and Goryeo

KOR is the Goryeo formable (`e_goryeo`, shown as "Goryeo" via the `cn_goryeo` style key, rank 4,
75% of the Korea region, kingdom rank required). Silla is SLL (`k_silla`). The dormant tags HUB
(Hubaekje, `k_baekje`, ruler through `c_sangju`, the Gyeon seat) and TAE (Taebong, `k_goguryeo`,
ruler through `d_gaeseong`, the Wang seat) are the formable's starters. The disaster
`common/disasters/FallOfSilla.txt` starts for SLL in 892; `events/FallOfSilla.txt` releases HUB
(892) and TAE (901) from the provinces Silla holds in their lands and starts an independence war
each (the Dutch-revolt pattern). Unplayed in-game: check error.log after the first run.

## Balhae and the Jurchen tribes

`common/disasters/FallOfBalhae.txt` starts for BHE from 926 (faster with instability, war or a Khitan
empire) and `events/FallOfBalhae.txt` releases six dormant Jurchen tribes (WNN Wanyan, JIA Jiagu, TNO
Tangkuo, NIP Nipanggu, ADI Adian, HEN Helandian: CK3's 1066 holders of the Balhae counties) from the
provinces Balhae holds in their lands, each with an independence war. They are DORMANT and are, with
TIE and HUI, the listed starters of the JIN (Great Jin) formable. Their culture follows the 867 holder
of their seat (Korean/Mohe), not Jurchen, so JIN gates on its starters, not on the Manchu culture.
Balhae's Korean-side provinces are paired in `provfaiths.py` (Taeju, West Amnok, Namhae, Fengzhou).

## Mongolia: kingdoms and the Mongol Empire

The e_mongolia kingdoms with several tags are formables over their own tags' provinces (listed
starters, below kingdom rank): OTU Ötüken (Onon, Khaldun, Khiltsaiz, Kizilkhentii), GOI Gobi
(Wuguguo, Tataria, Abga, Ongi, Dadaels, Kherulendada, Akhulun), BRT Buryatia (vanilla tag; Vitim,
Dauria, Kotera, Chuya), ANA Angara (Eülge, Tulun, Bura). Tuva has no tag; Khakassia is the Kirghiz
Khanate. MGE (e_mongol_empire, vanilla tag) unites them: Mongol culture, kingdom rank, 75% of their
21 provinces, started by the Shiwei Mongol tags. A Great Yuan formable (e_great_yuan, by a split from
the Mongol Empire) is planned, not built.

## The Kirghiz Khaganate

KGZ is CK3's `e_kirghiz_khanate` (held from 840; the title is vacated on 925.1.2), so its 30 provinces
from the Ob to Uliastai are right. `common/disasters/FallOfKirghiz.txt` starts for KGZ from 925
(faster with a Khitan empire, instability or war); `events/FallOfKirghiz.txt` releases the dormant
NIN (Naimania, Naiman culture; a starter of the Mongol Empire, which Naiman may form), OVO
(Övörkhangai, Kerait), ARI (Arkhangai, Mongol), TUV (Tuva) and SIB (Sibir, vanilla tag)
and cedes the Dzungarian counties to DZG; the Kirghiz keep Khakassia and the Ob country.

## The fall of Tang and Dai Viet

TNG (`h_china`) holds Vietnam, the Gansu corridor and the Yan passes at 867; CK3's 1066 holders
(`state867` run at 1066.9.15) say what leaves. `common/disasters/FallOfTang.txt` starts for TNG from
874 (faster with instability, war or after 900) and `events/FallOfTang.txt` does three things:
releases the dormant DAI (Dai Viet, vanilla tag, `k_viet`, 7 provinces) in 907 with an independence
war; cedes Hexi's three counties (698, 701, 4223) to HEX in 907; cedes the Sixteen Prefectures and the
Khitan administration counties (696, 697, 702, 1816, 2136, 4194) in 936 to the first of LIO, KIN, KTN
that exists. DAI is Vietnamese/Mahayana through `ruler_title c_hai_dong` (Khuc Thua Du holds it at 867;
`k_viet` itself is a Han governor); the validator accepts a tag whose culture/faith follows either its
`ck3_title` or its `ruler_title` holder. New Dhyana rite (Mahayana school) in rites.py. CK3 has no
Ten Kingdoms and no Song tag (the Tang line ends 907, Song starts 960); a Song rename is not built.
Unplayed in-game: check error.log after the first run.

DNM is the Dai Viet empire formable (`e_viet`, rank 4, Vietnamese culture, kingdom rank required,
75% of the 8 provinces 613 1016 2371 2372 4819 4820 4821 610, capital Thang Long owned); DAI is its
only starter. A formable rename can now key on a province (`formable_renames.province`): a former
that owns Hue (2373) is named Dai Nam through the vanilla EU4 key DAI_NAM (the Nguyen empire of
1839, which joined the Red River to the south); the other renames key on tag or culture.

## The script-only rule and CI

The repository ships the script and CK3-independent data; everything that comes from CK3 or EU4 is
lifted by `tools/build.py`. `python3 tools/selfcontained.py` copies only `tools/` and `descriptor.mod`
into an empty folder, builds there, checks every generated text file equals the repository's, then lays
the hand-authored files (events, loc, ...) over the build and runs the validator. It must end
`SELF-CONTAINED`. Lifted by the build now: tag names (`tagloc.py`, the whole
`replace/countries_l_english.yml`), the cultures file and its loc (`cultures.py`), the religions file, its
loc and the interface sprite frame counts (`religions.py`, with `rites.py` for the schools).

Still images made only by a local run, with CK3 and EU4 installed (the text build and CI skip them):
the religion icon strips (`gfx/interface/*religion*.dds`), the government-rank strip, the rite icons
(placeholders until `python3 tools/faiths.py icons`) and the flags (`gfx/flags`, the user's own).
Generating the strips from EU4's strips and CK3's faith icons is the next step; then untrack the
generated output.

`.github/workflows/charlemagnes-legacy.yml` runs two jobs: **validate** (build, validate, and fail if
the committed files differ from the build output) and **self-contained** (the script-only check). Both
need a `REFERENCE_REPO_TOKEN` repository secret with read access to `man-netcat/eu4-ck3-reference`.

## The upload package

`python3 tools/build.py --release [--zip] [--out DIR]` (or `tools/release.py`) writes `../dist/<mod>/`
(+ `.zip`, + a `.mod` launcher) holding only the script and the mod's own files: `tools/`, the hand-
authored events, disasters, decisions, loc and common files, `descriptor.mod` (no machine path, no flag
replacement) and an `INSTALL.md`. Everything the build writes, every image under `gfx/`, and any
file that is an edited copy of a base-game file is left out. The release fails if a base-game file's
bytes appear in the package, or an edited base-game copy is not produced by the build. Installers run
`python3 tools/build.py` once with their own EU4 and CK3 and get the rest. Base-game files the mod edits
(`defines.lua`, the monarchy reforms, subject types) are `tools/vanillapatch.py` edits applied to the
game's own copy; the hand-written government-title blocks and their loc are `tools/data/`, and the CK3
title ladders are lifted on top of them every build (`culturetitles.step_government_names`). CI builds
the package as an artifact.

### Province pairing for the whole Old World

All 2,247 owned provinces except the Azores are paired with a CK3 county in `provfaiths.PROVINCE_COUNTY`:
region tables from the earlier lifts, a block of exact name matches (EU4 name = a CK3 county or barony
name, unique, in the de jure kingdom of its EU4 area), and hand-paired blocks per region for the EU4
names CK3 does not use. The pairing is by place, so several EU4 provinces may share one county.
`provfaiths.py apply` writes each province's religion and culture from the county; validate fails when
a paired province differs, or when an owned province is unpaired. Faiths CK3 has and EU4 lacked are
lifted as new religions (Mazdakism, Khurramism, Afridunism, Zunism) with their rite schools; the
rabbinic Judaism rites were added for the Khazar counties.

### Culture and religion groups

Culture groups are EU4's own (vanilla scripts name them), kept where they match CK3 and fixed where they
do not: `cultures.HERITAGE_GROUPS` lists the groups each CK3 heritage may sit in, and validate fails for a
culture outside them (`cultures.heritage_misfits()`). East Slavic is back as its own group (Russian,
Novgorodian, Ryazanian, ...; Romanian alone stays Carpathian), Goths are Germanic, Slovien and Carantanian
West Slavic, Pictish Brythonic, Hebrew and Aramaic Semitic, Bashkir and Buryat Altaic, Gondi Dravidian.
Religion groups follow CK3's religion family: `faiths.CK3_RELIGION_GROUP` maps each CK3 religion to a
group, every other pagan-family religion is `pagan`, and validate fails when a lifted religion sits
elsewhere (`faiths.group_misfits()`). The Baltic, Finnic, Slavic and Magyar faiths and Shinto therefore
sit in the pagan group (Shinto is moved out of eastern by `religions.MOVE_RELIGIONS`), and their rite
schools with them.

### Which cultures the file keeps

A culture IS a CK3 culture under CK3's own key; there is no map. `tools/cultures.py` writes one entry per
culture `tags.db` names (provinces, tags, formables, renames), grouped by CK3 heritage, with CK3's name
list and loc. Every base-game culture is dropped, so vanilla scripts naming one log errors until we
replace them. Validate fails on a culture that is not a CK3 culture.
