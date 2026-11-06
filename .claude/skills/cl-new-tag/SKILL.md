---
name: cl-new-tag
description: Task - build a new landed tag in Charlemagne's Legacy (a realm that owns provinces at the 867 start). Covers picking the CK3 title, the code, running addtag.py, names, flag, relations, and the checks. For landless tags see cl-releasables and cl-formables.
---

# Build a new tag

Prerequisite: `cl-rules` (CK3 is the source of truth; ask before any exception) and the environment of `cl-build-validate`.

## 1. Decide the facts from CK3, not from memory

- **The CK3 title:** a real title with an 867 holder and a colour. Rank follows its tier (c=1, d=2, k=3, e=4, h=5);
  selfcheck fails a different rank, and a tag without `ck3_title`. `ruler_title` is deprecated (only DAI/DNI/SAR-style
  precedents). Check the holder: `python3 -c "import sys;sys.path.insert(0,'tools');import state867 as S;h=S.holder('d_x');print(h,S.primary(h),S.liege_holder(S.primary(h)))"`.
- **Its land:** the provinces whose CK3 county falls under that holder's realm at 867 (`provfaiths.PROVINCE_COUNTY`,
  `state867`; `cl-ck3-lifting`). A vassal count or duke folded into a realm belongs to that realm's tag; a title that has
  its own tag only when the user wants one (governors, releasables).
- **The code:** three capital letters. If the tag's name equals a free base-game tag's name, use that tag
  (`cl-retag`, rule `cl-rules`): `python3 tools/retag.py suggest N` after creation lists them. Otherwise a code that is free
  in the database and among the base game's tags (`addtag.vanilla_tags()`); `addtag.py` refuses a base-game code.

## 2. Create it

```bash
cd "/home/user/EU4-Mods/Charlemagne's Legacy"
python3 tools/addtag.py TAG ck3_title PID [PID ...] --tech GROUP [--take] [--capital PID] [--rank N] \
        [--name X --adj X] [--file "Name.txt"] [--gov monarchy]
```

- `--tech` is mandatory: the owner's technology group unless 867 reality says otherwise.
- The first PID is the capital unless `--capital`; the capital must be one of the PIDs.
- `--take` reassigns provinces another tag owns (without it the tool stops and names the owners).
- Culture and religion come from the 867 holder (`culturelift.py`, `ruler_default`); `--culture/--religion` are
  documented exceptions - ask the user first.
- `--file`: country file name; it must differ from every base-game country file name (e.g. "Name County.txt").
- Writes `tags`, `provinces` rows for new PIDs, `tag_provinces`, the `feudalism_reform` row and a loc pair.

## 3. Finish

```bash
python3 tools/tagloc.py write            # name and adjective from CK3
python3 tools/placeholder_flags.py       # placeholder flag (cl-flags)
python3 tools/retag.py suggest 0         # reuse a base-game tag if the name matches (except LIT/BOH/CAS)
python3 tools/build.py && python3 tools/validate.py
```

Then: relations (`cl-subjects`), government title ladder if the culture is new (`python3 tools/culturetitles.py TAG`),
and a paragraph in `AGENTS.md` if the tag follows a decision. Commit the regenerated output with the DB change and check CI.

## Checks that will bite

Culture/faith must match the 867 ruler's (`synctags.py` lists drift); capital owned by the tag; relation limit; lieges
against CK3 (`python3 tools/lieges.py`); names equal to what `tagloc.py` lifts; every province paired to a CK3 county
(`provfaiths.PROVINCE_COUNTY`) with that county's culture and faith.
