---
name: cl-retag
description: Change a tag's three-letter code everywhere, or move a tag onto the base-game tag it stands for, in Charlemagne's Legacy. Covers retag.py, the "same name means same tag" rule, and the cases where it must not be applied.
---

# Retag

```bash
python3 tools/retag.py OLD NEW [OLD NEW ...]   # then: tagloc.py write; placeholder_flags.py; build; validate
python3 tools/retag.py suggest MIN_SEQ         # "OLD NEW OLD NEW ..." for tags with seq >= MIN_SEQ whose name is a free base-game tag's name
```

- `NEW` must be unused in the database. It is either a **base-game tag** (a deliberate reuse: the tag takes the vanilla
  country file name and the vanilla technology group, and `NEW` is appended to `VANILLA_REUSE` in `tools/checks/tags.py`)
  or **any free code** that is no base-game tag (a plain rename).
- It rewrites every table that names the tag (`tags`, `tag_areas`, `tag_provinces`, `tag_reforms`, `tag_suppress`,
  `diplomacy`, `formables`, `formable_renames`, `core_deny`, `rivalries`, `friendships`, `wars`, `war_sides`,
  `seed_cores`, `releasables`), the loc pair, the `tag = OLD` gates in `zz_kar_government_names.txt`, the flag file
  (renamed, never overwritten), deletes the old `history/countries/OLD - *.txt`, and sweeps the hand-kept docs and flag
  tools (`SWEEP` in `retag.py`: AGENTS/README/PLANNING/FLAG_NOTES/coaflags.py), then lists any other file that still names OLD.
- Hand-authored events, modifiers and on_actions are **not** swept: grep for the old code (`grep -rnw OLD .`) and fix by hand.

## The rule

A tag whose name equals a free base-game tag's name reuses that tag, whatever its government (the base game's `RVA` is
named "Dortmund", `JAI` "Malta"; the name in the base game's localisation decides, not the country file). Run
`retag.py suggest 0` after adding tags.

**Do not apply** where the vanilla tag is already one of our formables: the suggestions `LTU->LIT`, `BHM->BOH`,
`CST->CAS` stay unapplied (Lithuania, Bohemia, Castile are the formables). Check `select tag from formables`.

## Stale files after a retag

Rebuild and `git status`: the old code's generated country files, flag and history files should be gone or renamed. A
merged-away or deleted tag leaves `history/countries/CODE - *.txt`, `common/countries/<file>`, `gfx/flags/CODE.tga`
behind (the build does not purge them): delete them. A base-game tag freed this way comes back as a landless vanilla tag;
remove its stale entry from `VANILLA_REUSE` when nothing uses it, or validate's "no accidental vanilla tag reuse" fails.
