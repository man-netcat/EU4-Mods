---
name: cl-tag-identity
description: Task - change what a tag is (name, adjective, culture, religion, ruler, rank, government titles, capital, colour, technology) in Charlemagne's Legacy. Everything comes from CK3; this says which tool or table to use.
---

# A tag's identity

| What | Where it comes from | How to change it |
|---|---|---|
| Name and adjective | CK3 at 867.1.1 (`tagloc.py`: dynasty-named realms, dated `name =`, cultural name, title loc) | never by hand; `python3 tools/tagloc.py [TAG..]` explains a name, `... write` rewrites the loc; a special style goes in the `STYLE` table in `tagloc.py` (ask first); cultural names `python3 tools/culturalnames.py [apply TAG..]` |
| Ruler, dynasty, heir | the 867 holder of `ck3_title` (`ck3.resolve`), written by `histgen`/`steps/countries` | change `ck3_title` (rank must equal its tier), not the ruler; `ruler_title` only as a precedent (DAI, DNI, SAR) |
| Culture, faith, rite | the ruler's CK3 culture and rite (`culturelift.py`, `faiths.py`, `rites.py`) | `python3 tools/synctags.py` lists drift, `... apply` writes it; validate fails drift (DAI follows its `ruler_title`) |
| Government title ladder | CK3's flavorization (`culturetitles.py`) written into `common/government_names/zz_kar_government_names.txt` | `python3 tools/culturetitles.py [TAG..]` is the routine pass; hand blocks in `tools/data/` win |
| Rank | tier of `ck3_title` | `tags.rank` must equal the tier; ranks 1-5 and `MAX_GOV_RANK` stay in sync (`common/government_ranks/`) |
| Capital | `tags.capital`, one of the tag's provinces | SQL update; validate fails a capital the tag does not own |
| Colour | CK3 title colour at creation (`color_r/g/b`) | the build rewrites vanilla realm colours; for ours change the row only with the user's OK |
| Technology group, reforms, country file | `tags.technology_group`, `tag_reforms`, `tags.country_file` | SQL update; a reused base-game tag keeps the base game's tech (`cl-retag`) |
| Religion/culture of provinces | their CK3 county (`provfaiths.py`) | `cl-assign-provinces` |

Edit rows with `python3 -c "import sqlite3;c=sqlite3.connect('tools/tags.db');c.execute(...);c.commit()"` (no `sqlite3`
CLI in the sandbox) and then `tagloc.py write`, `build.py`, `validate.py`. Where the resolver disagrees with CK3, suspect the
resolver and fix it in the tool, never with a per-tag override (ask the user before any exception).
