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
- `common/ideas/*.txt` provides the national ideas.

When you remove a country, remove it from every file above, including
the flag file. Unused flag files are harmless, but the game ships only
with the files that exist, so remove them for a clean removal.

## Tags in this mod

39 countries. All tags are unique to the base game and to this mod.

Country list: DOB DOR FDA FRB FRC FRE GOR GRN GTN HOY JMT JUL KRB KZN LGN
LIM MRB MST MTZ NAM NMB OSL PSG PST RAV REV STG STR SYE TCK TES TSR URW VDN VID
WRM ZEA ZUR ZWE

## Tags that exist in the 1444 start

Ten prince-bishoprics exist on 1444.11.11 as vassals of the state that
owns their capital province. Each bishopric owns its capital province
from `1444.1.1` (the ATH pattern: the province history gives the vassal
`owner` and `controller` in a dated block before the start date). The
overlord keeps its core on the capital, so it can re-integrate the
bishopric or be forced to release it through the normal core-release
flow.

The vassal relation lives in `history/diplomacy/historical_european_tags_vassals.txt`.
Each block declares `first = <overlord>` and `second = <bishopric>` with
`start_date = 1444.1.1` and `end_date = 1821.1.1`, matching the basegame
format for indefinite vassalage (all basegame vassal blocks carry an
end_date, e.g. `second = MAZ` in `Baltic_alliances.txt`).

| Tag   | Bishopric          | Overlord             | Capital |
|-------|--------------------|----------------------|---------|
| DOR   | Dorpat             | LIV (Livonian Order) | 1834    |
| OSL   | Osel-Wiek          | LIV (Livonian Order) | 35      |
| KRB   | Courland           | LIV (Livonian Order) | 39      |
| REV   | Reval              | LIV (Livonian Order) | 36      |
| MRB   | Merseburg          | MAG (Magdeburg)      | 4741    |
| FDA   | Fulda              | WBG (Wurzburg)       | 4774    |
| VDN   | Verdun             | BAR (Bar)            | 4766    |
| MTZ   | Metz               | LOR (Lorraine)       | 188     |
| STG   | St Gallen          | SWI (Switzerland)    | 1870    |
| FRE   | Freising           | LBV (Bavaria-Landshut)| 4708   |

Each of these tags has a ruler in its `history/countries/` file dated
before 1444.11.11, matching the historical bishop in office at the start
date. All ten use `government = theocracy` and
`add_government_reform = leading_clergy_reform`.

The tags are still releasable: a player who defeats the overlord can
release the bishopric from its capital core. Releasing it restores the
tag to the game as an independent state with its national ideas.
