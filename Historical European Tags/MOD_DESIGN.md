# Historical European Tags - Design Constraints

This document records the design rules for the mod. Follow these rules
when you add, change, or remove a country.

## Core rule: capital provinces

Each country in this mod is a releasable state. It must be releasable from
a province that is NOT the capital of an existing country in the 1444 start.

The rule:

- The province must NOT be the home province of a country that exists on
  1444.11.11.
- The country tag must NOT reuse a tag that the base game already uses.
- The country tag must NOT reuse a tag that another country in this mod
  uses.

Test for a candidate capital province:

1. Find the 1444 owner of the province. Read the owner record in
   `history/countries/`.
2. Check the province owner record for `capital = <province id>`.
3. If the province is the owner capital in 1444, reject the province.

## Why the rule exists

A releasable country takes control of its home province when released. If
that province is the capital of an existing 1444 country, the release
breaks the existing country. So the home province must belong to another
state and must be a non-capital province for that state.

## How a country becomes releasable

A country in this mod becomes releasable because its home province history
adds a core for it:

- `common/country_tags/<file>.txt` maps the tag to a country file.
- `history/countries/<TAG> - <Name>.txt` sets the country start state and
  capital.
- `history/provinces/<province id> - <Name>.txt` adds `add_core = TAG`.
- `gfx/flags/<TAG>.tga` provides the flag.
- `localisation/*.yml` provides the name and adjective.
- `common/ideas/*.txt` provides the national ideas (8 of 74 so far; the rest
  fall back to the generic groups named in their country file).

When you remove a country, remove it from every file above, including
the flag file. Unused flag files are harmless, but the game ships only
with the files that exist, so remove them for a clean removal.

Localisation lives in three files, and the split matters:

- `localisation/historical_european_tags_l_english.yml` - decision, country
  and county strings for tags the mod adds.
- `localisation/historical_european_tags_ideas_l_english.yml` - idea names
  and descriptions.
- `localisation/replace/replace_historical_european_tags_names_l_english.yml` -
  the country name and adjective for every tag, including diacritics
  (Jülich, Göttingen, Racibórz, Franche-Comté). `..._ideas_l_english.yml`
  covers idea names and descriptions, and `..._l_english.yml` covers
  decision, county and title strings.

All three files are UTF-8 **with BOM** and carry accented text directly, so
do not strip the BOM or transliterate names.

## Tags in this mod

74 tags are registered in `common/country_tags/zzz_historical_european_tags.txt`.
All are unique to the base game and to this mod.

```
ALV ARS ATN BRL CGR CIL DOB DOR FAE FDA FRB FRC FRE GOR GRL GRN GTN GTY
GZR HLS HOY JMT JUL KAK KRB KRN KTN KUY KZN LGN LIM LUD LXM MRB MST MTZ
NAM NMB NVO OCC ORA ORK OSL OST PBH PSG PST RAV RCB REV SKN SLA SML STG
STR SXN SYE TCK TPL TSR URG URW VBO VBT VDN VGL VID WEI WRC WRM ZEA ZEM
ZUR ZWE
```

65 of the 74 have at least one core province and are therefore releasable.

Nine tags have no core and exist only as the target of a form decision:

| Tag | Decision | Notes |
|-----|----------|-------|
| ARS | `FormArles.txt` | Kingdom of Arles |
| BRL | `FormBrunswickLuneburg.txt` | Brunswick-Lüneburg |
| OCC | `FormOccitania.txt` | Occitania |
| SXN | `FormSaxony.txt` | Saxony formable |
| GTY | `FormGorzTirol.txt` | Gorz-Tirol |
| LUD | `FormLudowingia.txt` | Ludowingia |
| LXM | `FormLuxembourgMoravia.txt` | Luxembourg-Moravia |
| NVO | `FormNavarreNormandy.txt` | Navarre-Normandy |
| CGR | `FormCatholicGranada.txt` | dormant; see CGR below |

`CGR` is deliberately odd: it has a country file, flag, history and
localisation, but no core. It is not releasable and does not exist at the
start. It is created only by `decisions/FormCatholicGranada.txt`.

14 tags hold more than one core province, which is allowed - a release
gives the vassal all of them:

```
ATN: 377, 2313          FRC: 193, 4764        GZR: 285, 286, 2447
CIL: 327, 2302          GRL: 1104, 1105       KTN: 128, 4759
DOB: 159, 4706          KUY: 1859, 4523, 4524, 4528
ORK: 369, 1978          SKN: 6, 26, 1982, 4165
SLA: 152, 1767, 4756    SML: 3, 4166          TPL: 378, 4297
VGL: 7, 4163
```

## Known gaps

These are unfinished, not intentional. Fix them when touching the file.

- **Only 8 of 74 tags have a national idea group.** `CGR`, `FAE`, `GRL`,
  `KAK`, `ORK`, `REV`, `SLA` and `URG` have a `<TAG>_ideas = {` block in
  `common/ideas/historical_european_tags_country_ideas.txt`. The other 66
  have `<TAG>_ideas:` localisation but no block, so they fall back to the
  generic idea groups listed in their `common/countries/` file. An idea
  group is not required for the game to load, so this is cosmetic.
- **`VBO` has no flag.** `gfx/flags/VBO.tga` is missing.
- **Orphan flags**: `BRU.tga`, `CEU.tga`, `DPH.tga`, `HBS.tga`, `MKR.tga`,
  `RZB.tga` exist with no registered tag.
- **Orphan country files**: `FAE - Faroe.txt`, `GRL - Greenland.txt` and
  `ORK - Orkney.txt` duplicate the correct `Faroe.txt`, `Greenland.txt` and
  `Orkney.txt` and are dead weight.
- **Two mission trees.** `missions/EMP_Saxony_Missions.txt` and
  `missions/HET_FrancheComte_Missions.txt`. Every other tag has none. The
  FRC tree is DLC-free on purpose, because `FormArles.txt` is DLC-free.

## Tags that exist on 1444.11.11

`history/diplomacy/historical_european_tags_vassals.txt` holds these
relations. Each block declares `first = <senior>` and `second = <junior>`
with a `start_date` and an `end_date`, matching the basegame format; every
basegame vassal block carries an `end_date`, e.g. `second = MAZ` in
`Baltic_alliances.txt`.

### Prince-bishoprics and other vassals

Vassals of a secular holder. The overlord keeps the province; the bishop
rules it in the overlord's name until released. Each of these tags uses
`government = theocracy` and `add_government_reform = leading_clergy_reform`,
and its history file dates a ruler before 1444.11.11 to match the
historical prelate.

| Tag   | Bishopric        | Overlord              | Capital | End date |
|-------|------------------|-----------------------|---------|----------|
| DOR   | Dorpat           | LIV (Livonian Order)  | 1834    | 1821.1.1 |
| OSL   | Osel-Wiek        | LIV (Livonian Order)  | 35      | 1821.1.1 |
| KRB   | Courland         | LIV (Livonian Order)  | 39      | 1821.1.1 |
| REV   | Reval            | LIV (Livonian Order)  | 36      | 1821.1.1 |
| ORK   | Orkney           | NOR (Norway)          | 369     | 1821.1.1 |
| MRB   | Merseburg        | MAG (Magdeburg)       | 4741    | 1821.1.1 |
| FDA   | Fulda            | WBG (Wurzburg)        | 4774    | 1821.1.1 |
| VDN   | Verdun           | BAR (Bar)             | 4766    | 1821.1.1 |
| MTZ   | Metz             | LOR (Lorraine)        | 188     | 1821.1.1 |
| STG   | St Gallen        | SWI (Switzerland)     | 1870    | 1821.1.1 |
| GZR   | Gazaria (Genoese)| GEN (Genoa)           | 285     | 1821.1.1 |
| RCB   | Raciborz         | BOH (Bohemia)         | 263     | 1526.8.29 |
| LGN   | Liegnitz         | BOH (Bohemia)         | 4238    | 1526.8.29 |
| WRC   | Wroclaw          | BOH (Bohemia)         | 264     | 1526.8.29 |

The Silesian trio end the day before Mohács, because the Bohemian crown
dissolves at the battle. Basegame ends the HUN-CRO union at `1526.8.30`,
so these are deliberately one day earlier; keep that distinction in mind
before "fixing" them. `FRE` (Freising, capital 4708) is the one remaining
theocracy: the vassal file carries the comment "Freising is independent
with imperial immediacy", so it gets no `vassal` block and starts as a
free imperial immediate.

The overlord keeps its core on the capital province, so it can re-integrate
the bishopric or be forced to release it through the normal core-release
flow.

### Personal unions

| Senior | Junior | Start | End | Why |
|--------|--------|-------|-----|-----|
| MKL | MST | 1444.1.1 | 1821.1.1 | Mecklenburg junior line under the senior line |
| HUN | SLA | 1444.1.1 | 1526.8.30 | Slavonia as a separate kingdom under the Hungarian king |
| POR | ALV | 1444.1.1 | 1779.1.1 | Algarve as a separate crown under Portugal |

Each union ends on a real political event rather than the mod default:

- `SLA` ends at Mohács like the basegame HUN-CRO union.
- `ALV` ends in 1779, when Maria I merged the two titles and styled herself
  "King of Portugal and the Algarves". The day is not recorded precisely, so
  the start of the year is used, as with the Mecklenburg union. Portugal
  deliberately holds no core on the Algarve shore: the union is the only
  thing binding them.

## Slavonia: union junior partner of Hungary

Slavonia (`SLA`) exists on 1444.11.11 as the junior partner of a personal
union with Hungary (`HUN`), mirroring the basegame HUN-CRO union.

- `SLA`'s provinces are 152, 1767 and 4756. Syrmia (4173) stays with HUN.
- The three provinces keep their vanilla cores apart from `add_core = SLA`.
  Croatia's vanilla cores on them are removed, so CRO does not reclaim them.
  The province history files are copies of the vanilla files, so every
  vanilla dated event block (1456 HAB, 1521 TUR, 1526 HAB/TUR) is preserved.
- Ownership uses the ORK landed-subject pattern: the top-level `owner` key
  stays `HUN` and a dated `1444.1.1` block hands `owner`/`controller` to
  SLA. The verifier reads only the top-level `owner`, so SLA correctly
  reports "owns no provinces at start" while the 1444 hand-back makes it
  exist as a union junior.
- `history/countries/SLA - Slavonia.txt` sets `fixed_capital = 1767`,
  culture `croatian` (accepted `serbian`), religion `catholic`, and a dummy
  Habsburg ruler (Ladislaus Postumus) dated `1444.1.1`.
- The national colour is the EU5 map colour for Slavonia (`{ 174 227 95 }`,
  the EU5 `map_croatian` entry). Vanilla EU4 CRO is `{ 104 94 247 }`; the
  EU5 comment claiming "same as in EU4" is inaccurate.

## The Arles form: `FRC` and `ARS`

`FRC` (Franche-Comte) is a normal releasable tag: monarchy, `burgundian`
culture, `catholic`, capital and `fixed_capital = 193` (Franche-Comte), with
cores on 193 and 4764 (Salins). Both are Burgundian in 1444, and BUR's
capital is 192 (Dijon), so 193 satisfies the core rule above.

`ARS` (Arles) is form-only. `decisions/FormArles.txt` lets `FRC`, `DAU`,
`PRO` or `SAV` `change_tag = ARS`, move the capital to 202 (Avignon) and
grant claims on Piedmont, Lombardy and the Po valley - the Italian lands
the kingdom held before the crown passed to the HRE.

Forming Arles requires every province of four areas, owned and cored:

| Area | Provinces | 1444 owners |
|------|-----------|-------------|
| `provence_area` | 201, 202, 2991, 4696 | PRO x3, AVI x1 |
| `bourgogne_area` | 192, 193, 4764 | BUR x3 |
| `savoy_dauphine_area` | 203, 204, 205, 4719 | FRA x2, SAV x2 |
| `romandie_area` | 165, 1867, 1871, 4720, 4721 | SWI x2, SAV x2, GNV x1 |

That is 16 provinces across seven holders. `missions/HET_FrancheComte_Missions.txt`
implements this as one mission per area, in an order chosen so the fronts stay
defensible:

| Mission | Completes | Requires | Grants |
|---------|-----------|----------|--------|
| `frc_secure_the_jura` | own 193 and 4764 | - | claim on 192 Dijon |
| `frc_take_dijon` | `bourgogne_area` (3) | the Jura | claims on Provence + Dauphiné |
| `frc_conquer_dauphine` | `savoy_dauphine_area` (4) | Dijon | claims on the Romandie |
| `frc_take_provence` | `provence_area` (4) | Dijon | claim on 202 Avignon |
| `frc_take_romandie` | `romandie_area` (5) | Dauphiné | claim on 4720 Geneva |
| `frc_crown_of_arles` | all four areas, 16 provinces | all of the above | rank 2, Piedmont/Lombardy/Po claims |

The spine is Dijon (192): FRC holds cores on 193 and 4764, but both are
Burgundian in 1444 and Burgundy holds the third province of `bourgogne_area`,
so the tree cannot reach Arles without taking it.

Every mission grants the claim for the next stage, because a form decision is
unreachable if the player completes a mission and then has no claim to press.
`frc_crown_of_arles` mirrors the `FormArles` allow block exactly and does not
re-implement the formation - the player still takes the decision.

To add a tree for another tag, follow `.opencode/skills/eu4-mission-trees/SKILL.md`.

## CGR: dormant Catholic Granada

`CGR` is a special case: a fully defined country (file, flag, history,
localisation, `CGR_ideas`) that does not exist at the start and has no core.

`decisions/FormCatholicGranada.txt` creates it. The potential allows any
country whose capital province is in vanilla's `iberia_region`, with these
exceptions:

- `NOT = { exists = CGR }` - one crown only.
- `NOT = { tag = SPA }` - Spain is Castile's client, not a Spanish release.
- `NOT = { government = republic }`.
- The root must be free or tributary, own and core 222 (Almeria), 223
  (Granada), 226 (Gibraltar) and 4546 (Malaga), and be at peace. `release`
  cannot hand over an existing tag, hence the `exists` gate.

The effect changes the tag to `CGR`, releases it from the root, grants a
personal union, sets religion catholic, and copies the senior's primary
culture and colour with `change_primary_culture = ROOT` and
`change_country_color = { country = ROOT }`. It accepts `andalucian`.

`decisions/GranadaConfession.txt` handles the two identity shifts in each
direction. Both call `on_change_tag_effect` and require the target tag to
be free:

- `roots_of_the_alhambra`: CGR + Muslim -> `change_tag = GRA`, religion
  sunni, primary culture `andalucian`, accepts `castillian`.
- `embrace_iberian_identity`: GRA + Christian -> `change_tag = CGR`,
  religion catholic, primary culture left alone, accepts `andalucian`.

Notes and gotchas learned while building this:

- Culture effects must use bare values: `change_primary_culture = andalucian`,
  never `= { andalucian }`. Vanilla uses the bare form throughout.
- The culture key is `andalucian`. `andalusian` does not exist.
- `change_tag` fails if the target tag already exists, so every
  tag-changing decision needs a `NOT = { exists = ... }` gate.
- A national idea group does not follow `change_tag`. `FormArles` works
  around this with `swap_non_generic_missions = yes` plus an
  `ideagroups.1` event; the CGR decisions do not swap idea groups yet.
- Eyelet-style colour handling may also want `has_eyalet_color`. Untested
  in game.

## Verifier

`tools/verify_releasables.py` reads `history/countries/` and
`history/provinces/` and checks the design rules. Run it after any change to
a country:

```
python3 tools/verify_releasables.py
```

Current baseline is 74 tags, 54 FAIL, 36 WARN. The failures are mostly
known data-quality items in the basegame province set, not mod errors; the
checks that guard the mod's own rules (decision cultures exist, culture
keys are real, decision areas exist, palette indices in range) all pass.

The verifier does not yet check `region =` references, and it still reports
five genuine primary RGB collisions: `LUD`, `MST`, `DOR`, `OSL` and `KRB`.