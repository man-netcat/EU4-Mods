# HRE Releasables - Design Constraints

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

When you remove a country, remove it from every file above. Keep the flag
file. The game ignores unused flag files.

## Tags in this mod

39 countries. All tags are unique to the base game and to this mod.

Country list: DOB DOR ERF FDA FRB FRC FRE GOR GRN GTN HOY JMT JUL KRB KZN LGN
LIM MRB MST MTZ NAM NMB OSL PSG PST RAV STG STR SYE TCK TES TSR URW VDN VID WRM
ZEA ZUR ZWE
