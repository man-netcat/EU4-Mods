---
name: cl-ck3-lifting
description: Reading CK3's 867 data in Charlemagne's Legacy tools - holders, lieges, sovereigns, cultures, faiths, names, and how to query another date. Use when you need a fact from CK3 or when a lift (names, cultures, religions, lieges, province faiths) looks wrong.
---

# Lifting CK3 data

CK3 is the only source of truth. Nothing of its text is stored; the build lifts it. Parsed CK3 is cached in
`tools/cache/` (mtime-keyed pickles; never edit, safe to delete; bump `_CACHE_VERSION` in `ck3.py` when a parser changes).
Run from `tools/` or the mod folder with `EU4_GAME` and `CK3_GAME` set (`cl-build-validate`).

## The modules

- `ck3.py`: `load_titles()` (title -> [(date head, body)]), `load_chars()`, `holder_at(title, titles)` (uses the module
  global `ck3.DATE`, default 867.1.1), `resolve(tag, titles, chars, dyns, houses)` (a tag's 867 ruler), `loc(key)`.
  New CK3 syntax is handled here, not per tag.
- `state867.py`: `holder(title)`, `liege_holder(title)` (None = independent: CK3 writes every vassalage as `liege =`; `0` or
  none means independent), `titles_of(char)`, `primary(char)` (highest-tier title), `sovereign(char)` (top of the chain),
  `states(province_county)`; `TIER = {b:0, c:1, d:2, k:3, e:4, h:5}`.
- `provfaiths.PROVINCE_COUNTY` (pid -> CK3 county): the curated pairing for every owned province; several provinces may
  share a county.
- `lieges.py`: `lieges()` (per tag, its CK3 liege's realm), `mismatches()`, `governor_province_mismatches()`,
  `releasable_problems()`; `python3 tools/lieges.py` prints liege mismatches.
- Names: `tagloc.py` (`python3 tools/tagloc.py [TAG..]` explains a name; `write` rewrites the loc), `culturalnames.py`,
  `culturetitles.py` (government title ladders). Cultures and faiths: `culturelift.py`, `faiths.py`, `religions.py`,
  `rites.py`, `provfaiths.py [apply]`, `synctags.py [apply]` (tag culture/faith to the ruler's; a DAI drift is known and
  accepted because it follows `ruler_title`).
- `liftstates.py REGION [apply]` turns a region's 867 states into tags (plan first, then apply).

## Query another date

```python
import ck3, state867 as S
def at(date):                       # e.g. "871.1.1"
    ck3.DATE = date
    S._DATE = ck3._date_key(date)
    S._held.clear()                 # titles_of() caches per date
```

Reset the date afterwards. Each call to `S.titles_of` re-indexes every title, so batch your queries per date.
A county whose 867 holder is a vassal count: `S.holder(county)`, then `S.primary(h)` and `S.liege_holder(S.primary(h))`.

## Method notes

- A county is independent only when its holder's top title is a county (or higher) and `sovereign(holder) == holder`;
  a missing `liege =` also reads as independent, so confirm suspicious cases in the title history
  (`ck3.load_titles()[title]`).
- Rulers: validate checks every CK3-mapped ruler against the 867 bookmark and warns on child rulers (regency).
- Where CK3 lacks something (alliances, partitions, Meerssen), the mod uses history only with the user's OK; keep that
  visible in `AGENTS.md`.
