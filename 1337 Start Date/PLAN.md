# 1337 Start Date - plan

A standalone EU4 mod that starts in April 1337 (EU5's `bookmark_1337` date).
Same philosophy as vanilla EU4: provinces, tags, ideas, missions, events.
EU5 is the *source of historical data*, not of mechanics. Where EU5 is
historically wrong, we correct it (log each correction in `tools/corrections.md`).

## Status

- Scaffold, bookmark (default, 1337.4.1), START_DATE define, loc: done.
- `history/` is now **generated** by `python3 tools/build.py` (then `python3 tools/validate.py`,
  must end with ALL CHECKS PASSED). Never hand-edit `history/`, `common/country_tags/1337_tags.txt`,
  `common/countries/`, `localisation/1337_countries_l_english.yml`; change `tools/` or `tools/data/*.json`.
  Env: `EU4_INSTALL` (real install, default /mnt/data/SteamLibrary/...), `EU5_GAME`.
- Generated: province owner/controller/cores/culture/religion/hre; country base (capital, culture,
  religion, rank, 1337 monarch + eldest-son heir from EU5 characters); 384 new tags (registration,
  colour, graphical culture, loc, history); alliances/vassals/tributaries/guarantees from `12_diplomacy`;
  HRE membership and emperor (UBV, Louis IV) from `15_international_organizations`.
- Vanilla tags without an EU5 1337 counterpart stay as dormant files (pre-1444.11.11 entries dropped).
- Development: `development_targets` ranks the name-matched provinces by EU5 pop and hands them the sorted vanilla
  totals (floor: half the vanilla total), keeping each province's tax/production/manpower proportions. First pass,
  not playtested. Mission trees are still vanilla (none for new tags).
- Economy (`economy_targets`): trade goods from the EU5 raw material of a province's name-matched locations (weighted,
  rare goods heavier; `GOODS`), `fort_15th` from EU5 castles/walls/strongholds, `shipyard` from wharves/docks/arsenals,
  `center_of_trade = 1` on EU5 market towns lacking one. Provinces on shared location pools keep vanilla values.
  EU4's own history sets almost no other buildings, so there is nothing else to port.

## Progress on step 1 (loc2prov, no map geometry - the owner vetoed pixel/coordinate mapping)

`python3 tools/loc2prov.py` -> `tools/data/loc2prov.json` (EU4 province -> EU5 locations)
and `loc2prov_unmatched.json`. Tiers: location key/display name, EU5 province/area
node name, hand `aliases.json`, then area-fallback (EU4 area -> dominant EU5 area's unclaimed
locations). Matches filtered by EU4-region/EU5-region compatibility.
Result: 3008 of 3356 land provinces; 1180 of those are area-fallback (mostly New World/Africa/Asia).
Europe and the Middle East are almost fully name-matched; ~20 European aliases still to hand-resolve.

`tools/eu5setup.py` parses EU5 `10_countries.txt` (2351 country blocks, owner/control/core per location).
Finding: EU5 tag codes clash with EU4 codes for different states (CHI, LAN, FLO, UBV, ...);
only ~200 of 571 provincial owners share both code and name. Tags must therefore be mapped by
**name** (plus an alias table: Egypt=Mamluks, Jochi=Golden Horde, ...), never by code, and new
states get collision-free generated codes.

## Source data (EU5, read-only)

`Europa Universalis V/game/main_menu/setup/1337/`:
`10_countries.txt` (ownership/control/cores per location), `05_characters`,
`04_dynasties`, `12_diplomacy` (alliances, vassals, unions), `16_wars`,
`13_religion`, `15_international_organizations` (HRE etc.), `14_development`.

## Pipeline (tools/, Python, DB-driven like Charlemagne's Legacy)

1. **loc2prov**: map each EU5 location to an EU4 province. EU5 has ~13.8k
   locations vs ~4.9k provinces, so many-to-one: owner of a province = owner of
   its dominant (by area/pop) locations. Built by rasterising EU5
   `locations.png` and EU4 `provinces.bmp` onto a shared lat/lon grid
   (needs a hand-checked anchor set for the two projections).
2. **tags**: EU5 1337 country -> EU4 tag. Same code where both exist and
   are the same state; otherwise new tags (1337 had many states 1444 lacks:
   Ilkhanate successors, Chagatai/Jalayirids, Serbian Empire, Trebizond,
   Naples, Aragon-Sicily, etc.; and 1444 tags that don't yet exist: OTT as a
   tiny beylik, Timurids, ...). Reserve a 3-letter prefix range for new tags.
3. **provinces**: owner/controller/core, culture/religion (from EU5 pops,
   majority), development/trade goods kept vanilla but scaled down (see below).
4. **countries**: government, religion, culture, capital, tech group, rulers
   (EU5 characters -> EU4 monarch/heir with plausible stats), dynasties.
5. **diplomacy/wars**: alliances, vassals, unions, march/ties from `12_diplomacy`;
   only wars truly ongoing in 1337 (e.g. none/Scottish Independence tail,
   Reconquista campaigns, Byzantine civil-war aftermath).

## Not-EU5 decisions (keep EU4 simple)

- Keep EU4's three monarch points, ideas, mission trees, estates; do not port
  pops, markets, production methods, laws, levies.
- CORRECTION to the first draft: do NOT scale development down. Western Europe's population peaked
  just before the Black Death, so 1337 France/England/Italy/Low Countries should be at least vanilla level.
  Use EU5 pop totals (`popdata.location_pops`) to retune development per province later.
  The Black Death (1346-53) is an event chain, not a start condition.
- Institutions: none embraced at start (feudalism-equivalent only).
  Renaissance spawns ~1450-1500 in Italy; Printing press stays Rhineland-ish.
- Tech: start at tech 3-5 for the best, group lag adjusted.

## Historical-accuracy filter on EU5 data (to review after import)

Flag and fix, for example: wrong rulers/regents, dynasties placed in the wrong
realm, borders that fit 1444 or 1356 better than 1337, religions of
border/steppe peoples, vassal relationships that did not exist yet.

## Build/validate

`python3 tools/build.py` (to write) regenerates `history/`; never hand-edit
generated output. Playtest is by the owner; paste `error.log` back.


- Wars: `step_wars` writes the 5 EU5 wars running in 1337 to `history/wars` (dated 1337.3.1) and the 10 truces as
  `add_truce_with` in country files; validate checks them.

## Tag granularity (EU4's spirit, not one tag per EU5 county)

- `tagmap.fold_small_subjects`: a subject (12_diplomacy) that is not a base-game tag and holds <= `FOLD_MAX` (2)
  EU4 provinces gets no tag; its provinces, control and cores pass to its overlord (e.g. the Polish duchies).
  New tags 395 -> ~285. Independent single-province states stay (EU4 has many of those too).
- `tagmap.partition_shared_pools`: EU4 provinces matched to the same pool of EU5 locations share the pool's owners
  in proportion to pop instead of all taking the majority owner (this is how Navarre keeps a province).
  EU5 owners holding an EU4 province: 504 -> ~540 of 1566; the rest are mostly rural Asian/African/American
  counties and subjects folded into overlords.
- Rivals/friends: `step_rivals` writes `historical_rival` (20_rivals) and `historical_friend` (alliances); the
  1444 ones in vanilla country files are stripped.

## Rulers

`chars.country_rulers`: the country's `ruler`, else its open-ended ruler_term, else (in a regency) the heir who reigns
under it; heir = the block's `heir`, else the eldest son; queen = the ruler's living spouse. Compound EU5 names
(`name_stephen.name_uros`) are resolved. Countries whose EU5 ruler is `random` (~275 of ours) have none in the data,
so EU4 generates one at start. Vanilla tags without land of ours (`step_dormant`) take the ruler of the same-named EU5
country (49 so far).

## Subjects and diplomacy

`step_diplomacy` (history/diplomacy/1337_diplomacy.txt): EU5 vassal/fiefdom/dominion/samanta/tusi -> `vassal`; appanage and
familial_governor -> `dependency` appanage; tributary -> `dependency` tributary_state; hanseatic_member -> alliance (not
a subject). Subjects of a folded tag re-attach to its overlord; one overlord per subject; no alliance with the overlord;
validate checks types, cycles and land. `celestial_empire.txt` overrides the base game's so the Yuan, not the Khalkha
khan, hold the mandate. Personal unions: EU5 has no union object; one ruler holding several crowns is a union. The ruler's own country
(character `tag`) is the senior, the others become `union` juniors unless they are subjects or were folded (9 so far:
Hainaut-Holland, Moscow-Novgorod/Nizhny/Kostroma/Vladimir, Hungary-Croatia, Bohemia-Luxembourg, Naples-Provence,
Sweden-Norway). Base-game relations that were running before 1337 and involve such tags are shipped removed
(`drop_base_game_relations_at_start`, e.g. the 1299 Hainaut-Holland alliance), lifted from the base game by the build.

## Names

New tags: `localisation/1337_countries_l_english.yml`. Base-game tags the mod reuses take EU5's name and adjective for their
state through `localisation/replace/1337_countries_l_english.yml` (only where it differs from the base game's), as in
Charlemagne's Legacy; both files are written by `step_tags`.

## Estates, institutions, ideas

- Institutions: `step_institutions` ships the base game's `common/institutions/00_Core.txt` with Feudalism's history rule
  wrapped: provinces matched to EU5 locations follow EU5's 08_institutions (present if any location has `feudalism`,
  absent otherwise; ~1300 / ~490 provinces), the base game's culture/tech-group rule decides the rest. Legalism and
  meritocracy have no EU4 counterpart; the other EU4 institutions spawn by date as usual.
- Estates: EU5's privileges and estate setup do not map onto EU4's, so estates are EU4's defaults per government
  (reform) for every tag. The 1444 `change_estate_land_share` / `set_estate_privilege` / estate loyalty lines of base-game
  country files are stripped so no tag starts with a 1444 estate set-up.
- Ideas: EU5 has no national ideas. `tools/ideas.py` builds a 7-idea set (+ traditions and ambition) for each new tag with
  >= 3 provinces or >= 25 development (54 of them) from themed modifier lists chosen by government, culture group,
  religion group, coast and wealth. A modifier is only used if the base game's idea files use it and takes the median
  value the base game gives it; validate fails on any modifier outside that set. Smaller new tags get the base game's group
  or default ideas; base-game tags keep their own.

## Support content (what a vanilla start date has)

- Bookmark roster generated from the start's strongest tags (`step_bookmark`); electors from EU5's HRE (`elector = yes`,
  the base game's stripped); royal marriages from foreign consorts; accepted cultures from where a realm's development
  lives (`step_accepted`, the base game's 1444 lists stripped); placeholder flags for the new tags (`tools/flags.py`,
  never overwrites an existing file).

## Technology

EU5's `starting_technology_level` (3 for most, 0-2 for steppe, Siberian and Amerind states) is lifted by `step_technology`:
the base game is on time at 1444 holding level 3 (year 1440), so a start 107 years earlier holds level 1. Every group's
`start_level` becomes `max(0, level - 2)` (`common/technology.txt`), the years of levels 0-3 move to 1325/1340/1370/1410
(`common/technologies/*.txt`, so the next level is researchable instead of 80 years "ahead of time"), and a country whose
EU5 level differs from its group's gets `add_adm/dip/mil_tech` in a 1337.3.1 block (48 do). All derived from the base game's
files at build time.

## Age of Traditions

`tools/ages.py`: `common/ages/00_traditions.txt` (start 1337, ends when the base game's Age of Discovery starts in 1400): five
objectives lifted from the Age of Discovery, four abilities of our own (modifiers checked against the base game's idea
modifiers), the per-age scripted-effect hook, a window in a copy of `interface/ages_view.gui` and a popup sprite. The
window and popup use the Discovery pictures and sound until the age has its own art (`gfx/interface/ages/`); the age
bar still shows the base game's four icons.

## Consistency

`step_capitals` moves a capital that fell to another owner onto the realm's most developed province (5 so far; validate
checks it). Base-game states EU5 types differently (monarchy / republic / theocracy only, never tribal) take EU5's government
with the generic reform (17: the Italian signorie as republics, bishoprics as theocracies, Genoa as a monarchy).
The base game's backstory wars dated 1414-1443 (Hunger War, Wars of Lombardy, ...) are not removed: they run on their
own dates as history between 1337 and 1444, with whatever tags then exist.

## Known gaps / TODO (generated output is a first pass, not playtested)

1. Province mapping: 2622/3357 land provinces by name/hierarchy; ~735 unmapped keep their vanilla owner only if that tag is
   in the 1337 table (plus `VANILLA_PROXY` in build.py), else are unowned. Hand aliases: `tools/data/aliases.json`;
   review `data/loc2prov_unmatched.json`.
2. The new tags' flags are plain heraldic placeholders; EU5's coats of arms are not renderable from text.
3. Mission trees, events and decisions for 1337-1444 history are not written; base-game scripts
   keyed to 1444 may misfire. Starts that need the owner's playtest: `error.log`.
4. Religion: see above (Baltic/Finnic pagan own religions; verify the pagan group merges in-game).
5. Possible historical errors in EU5's data are logged in `tools/corrections.md` (empty so far).
