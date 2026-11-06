---
name: cl-releasables
description: Add, review or regenerate the releasables of Charlemagne's Legacy - dormant county tags that wake by rebels, by a CK3-dated independence event, or when the Karolingian Empire forms. Use when adding more, changing the criteria, or debugging one.
---

# Releasables

A releasable is a **landless tag tied to a CK3 county title**. The county's provinces stay with their owner; the tag's core
is seeded on them (`seed_cores`), so rebels or a manual `release` can create the country. They live in the
`releasables(tag, hre)` table; `tagdb` adds them to `DORMANT` automatically (landless tags that are not in `DORMANT`
fail selfcheck).

## Criteria (user, 4 Nov 2026)

A county qualifies when, on a European tag's land (Iberia, France, Low Countries, isles, Germany, Italy, Scandinavia,
Poland, Baltic, Ruthenia, Carpathia, Balkans; `liftstates.region_pids`): its 867 holder (`state867.holder`) is **not that
tag's ruler**, rules **no tag of his own**, has a **county as his top title** (`state867.primary`) and has a **liege**
(`state867.liege_holder`). **One tag per count:** all of a count's counties go on one tag whose title is his top county.
Validate enforces it (`lieges.releasable_problems`, "releasables are counts with lieges"). The first 16 were picked by
hand from a CK3 scan of counties held independently for 50+ years; the scan is noisy (a missing `liege =` reads as
independent), so judge candidates, do not trust it blindly.

## Add one

```bash
python3 tools/addtag.py TAG c_county PID [PID ...] --tech GROUP --dormant [--hre] [--capital PID] [--file "Name County.txt"]
```

`--dormant` requires every PID to belong to a tag already (it seeds cores, it takes nothing); `--hre` marks German, Low
Country and Italian land (the Karolingian-Empire release uses it). Then, in order: `python3 tools/retag.py suggest 0`
(reuse a base-game tag where the name matches, `cl-retag`), `python3 tools/tagloc.py write`,
`python3 tools/placeholder_flags.py`, `build.py`, `validate.py`.

For many at once, call `addtag.main([...])` in-process from a script (`contextlib.redirect_stdout` to keep output short)
and report any that fail; a code is free only if it is neither in `tags` nor a base-game tag (`addtag.vanilla_tags()`).

## What the build writes (`tools/steps/releasables.py`)

`events/KarReleasables.txt` and `localisation/kar_releasables_l_english.yml`, generated, never hand-edited:
- `kar_releasables.N` per tag that has an **independence year**: `independence_years()` returns, per title, the first year
  of a ten-year stretch (868-1100) in which CK3's holder rules independently with the county as his top title. The
  owner of the province (`is_year = Y`, MTTH 24 months, once) may release the tag (AI 20%) or take +5 unrest (AI 80%).
  A count who is a vassal all his life gets no event, only the cores.
- `kar_releasables.100` (HLR): `kar_form_hre` in `steps/empire.py` schedules it a year after the Karolingian Empire forms;
  the emperor may free every `hre` tag whose provinces he owns (AI 50%).
The vanilla Holy Roman Empire (members, free cities, princes) does not exist in this mod (every province is `hre = no`):
released tags are plain independents. Say so rather than promising membership.

## Remove or merge one

Delete its rows from `seed_cores`, `releasables`, `tag_reforms`, `tags` (merging: first move the seed provinces to the
surviving tag), then delete `history/countries/CODE - *.txt`, `common/countries/<file>`, `gfx/flags/CODE.tga` (placeholder
only; check `placeholder_flags.py --list`), and rebuild.

Unplayed in-game: the `release` effect on these tags and the HRE hook are untested; report them so.
