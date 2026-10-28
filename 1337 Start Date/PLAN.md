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
- Ideas: EU5 has no national ideas. New tags get the base game's group ideas (culture group, government, tech group)
  or its default ideas, as every minor base-game tag does; base-game tags keep their own.

## Known gaps / TODO (generated output is a first pass, not playtested)

1. Province mapping: 2622/3357 land provinces by name/hierarchy (fixed `eu4_geo` reading area colours as provinces, plus ~70 hand aliases for Europe and the Near East); ~735 unmapped keep their vanilla owner only if
   that tag is in the 1337 table (plus `VANILLA_PROXY` in build.py: Ming->Yuan etc.), else are unowned.
   Hand aliases go in `tools/data/aliases.json`; review `data/loc2prov_unmatched.json`.
2. Tags are matched by name + `ALIASES` in tagmap.py; ~384 are new tags with generated codes (no flags yet).
3. EU5 accepted cultures, estates/land shares, ideas for new tags, flags, monarch names lists.
4. Religion: Baltic and Finnic paganism are the mod's own religions (`common/religions/1337_religions.txt`, added to the vanilla `pagan` group; they borrow the Norse/shamanism icon frames, so the owner should check in-game that the group merges). Faiths EU4 lacks (Judaism, Jain, Cathar, Bosnian Church...) map to the nearest vanilla religion in `tools/tables.py` `RELIGION_HAND`, then `python3 tools/tables.py` rewrites `data/cr_map.json`.
5. Governments for new tags copy the vanilla pattern of the area, overridden by EU5 type (tribe/horde/republic/theocracy).
6. Possible historical errors to review in EU5 data are logged in `tools/corrections.md` (empty so far).
