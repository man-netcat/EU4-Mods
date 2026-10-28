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
- Province development, trade goods, buildings, institutions, estates, ideas/mission trees are still vanilla.

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

## Known gaps / TODO (generated output is a first pass, not playtested)

1. Province mapping: 2622/3357 land provinces by name/hierarchy (fixed `eu4_geo` reading area colours as provinces, plus ~70 hand aliases for Europe and the Near East); ~735 unmapped keep their vanilla owner only if
   that tag is in the 1337 table (plus `VANILLA_PROXY` in build.py: Ming->Yuan etc.), else are unowned.
   Hand aliases go in `tools/data/aliases.json`; review `data/loc2prov_unmatched.json`.
2. Tags are matched by name + `ALIASES` in tagmap.py; ~384 are new tags with generated codes (no flags yet).
3. EU5 accepted cultures, estates/land shares, ideas for new tags, flags, monarch names lists.
4. Religion: Baltic and Finnic paganism are the mod's own religions (`common/religions/1337_religions.txt`, added to the vanilla `pagan` group; they borrow the Norse/shamanism icon frames, so the owner should check in-game that the group merges). Faiths EU4 lacks (Judaism, Jain, Cathar, Bosnian Church...) map to the nearest vanilla religion in `tools/tables.py` `RELIGION_HAND`, then `python3 tools/tables.py` rewrites `data/cr_map.json`.
5. Governments for new tags copy the vanilla pattern of the area, overridden by EU5 type (tribe/horde/republic/theocracy).
6. Possible historical errors to review in EU5 data are logged in `tools/corrections.md` (empty so far).
