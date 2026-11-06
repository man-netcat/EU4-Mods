---
name: cl-add-tag
description: Add a landed tag to Charlemagne's Legacy, move provinces between tags, or give a province to its CK3 owner. Covers addtag.py, code choice, names, flags, and the checks that follow.
---

# Add a tag / move provinces

Every realm is one row in `tools/tags.db` (`tags`, `tag_provinces`, `provinces`, `tag_reforms`...). Never create a tag
by writing country files. Landed tags hold provinces at the start; for landless ones see `cl-releasables`,
`cl-formables`.

## New landed tag

```bash
cd "/home/user/EU4-Mods/Charlemagne's Legacy"   # EU4_GAME and CK3_GAME exported (cl-build-validate)
python3 tools/addtag.py TAG ck3_title PID [PID ...] --tech GROUP [--take] [--capital PID] [--rank N] \
        [--name X --adj X] [--file "Name.txt"] [--gov monarchy] [--culture K --religion K]
```

- `TAG`: three capital letters, free in the database **and** among the base game's tags (`addtag.py` refuses a base-game
  code unless `--reuse`). Derive it from the name; if a name equals a free base-game tag's name, use that tag instead (`cl-retag`).
- `ck3_title` must be a real CK3 title with an 867 holder and a colour; rank follows its tier (c=1, d=2, k=3, e=4, h=5)
  and selfcheck fails a mismatch. No title, no tag.
- `--tech` is mandatory (take the owner's group unless 867 reality says otherwise).
- `--take` reassigns provinces that another tag owns; without it the tool aborts. The first PID is the capital unless `--capital`.
- Culture and religion are lifted from the 867 holder (`culturelift.py`); `--culture/--religion` are documented exceptions:
  ask first.
- `--file`: the country file name; the tool aborts when it equals a base-game country file name (pick another, e.g. "Name County.txt").
- It writes the DB rows, the `feudalism_reform` row and a loc pair before the `HLR` line of
  `localisation/replace/countries_l_english.yml` (the build rewrites that file from CK3 anyway).

Afterwards, in this order:

```bash
python3 tools/tagloc.py write              # names and adjectives lifted from CK3 ("rewritten"/"unchanged")
python3 tools/placeholder_flags.py         # a placeholder flag for every tag and formable without one
python3 tools/build.py && python3 tools/validate.py
```

Then give the tag its relations (`cl-subjects`) and update `AGENTS.md`.

## Move provinces

```bash
python3 tools/addtag.py --to TAG PID [PID ...] --take
```

Reassigning land drops the previous owner's cores at build. If the moved province was a tag's capital, set a new capital
in the DB (`update tags set capital=PID where tag='XXX'`) or validate fails ("holds its mod capital").

**Which tag gets a province:** follow CK3's 867 chain. The sovereign of the county's holder owns it; a vassal count or duke
folded into a realm belongs to that realm unless the realm has a tag for that duchy. Helpers: `state867.holder(county)`,
`state867.sovereign(holder)`, `provfaiths.PROVINCE_COUNTY[pid]` (see `cl-ck3-lifting`). Validate's province checks
(`lieges.governor_province_mismatches` for BYZ and ARB) name the provinces that sit wrongly.

## After a change, check

`tagdb.selfcheck` runs on import; `validate.py` checks ownership, capitals, culture/faith of rulers, names, flags (WARN),
lieges, relation limits, dormant cores. Nothing else is needed for a new tag unless it joins formables or diplomacy.
