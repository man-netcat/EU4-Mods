---
name: cl-vanilla-scripts
description: How Charlemagne's Legacy filters the base game's events, decisions and other script - which are cut and why, how missing event references are stripped, replace_path rules, and vanillapatch edits. Use when an event, decision or error.log line about vanilla script needs fixing.
---

# Vanilla scripts in an 867 world

Two ways base-game content reaches the mod, both in `tools/` and both regenerated every build:

1. **Vendored copies** with the unfit parts cut (`steps/vanilla_scripts.py`, `steps/eventrefs.py`): same file names as
   the base game, so the mod's copy overrides vanilla's.
2. **Edits to a base-game file** (`tools/vanillapatch.py`, `PATCHES[path] = [(context lines, old lines, new lines), ...]`):
   the game's own copy is read at build time and patched; a context that no longer matches stops the build, so a game
   update is noticed. Subject types, static modifiers, defines and the monarchy reforms are patched this way (our own
   blocks sit between `# BEGIN kar ...` / `# END kar ...` markers that validate expects).

## `descriptor.mod` replace_path

`missions`, `history/*`, `gfx/flags`, `common/government_names`, `common/government_ranks`, `common/cultures`,
`common/bookmarks` are replaced: **no base-game file loads there**. Never vendor base-game files into those folders (a
pass that vendored vanilla missions was reverted), and ignore base-game references in them. The outer
`Charlemagne's Legacy.mod` and inner `descriptor.mod` must carry identical `replace_path` lines; update both.

## Events (`step_events`)

An event is **dropped** when it names a tag (3-letter token outside comments, any tag the base game knows), a culture or
religion the base game defines and the mod does not (`names_lost_key`), a place (province id, `*_area`, `*_region`,
`*_superregion`), a date after 1066 (`LAST_YEAR`), a new-world or early-modern system (`_LATE_SYSTEM`: colonies, trade
companies, institutions, absolutism, gunpowder...), or when it fires a dropped event (cascade); the whole of
`flavorBYZ.txt` goes too (`DEAD_BYZANTINE_EVENT_FILES`). The build prints the counts. Dated generic events before 1066
stay. The aim (user): only purely generic events appropriate for the period remain.

To change what stays: edit the rules (`names_late_or_local`, `_LATE_SYSTEM`, `lost_keys`) or the file sets, rebuild,
read the printed counts, and sample what changed (`git diff --stat`); update `AGENTS.md`.

## Decisions (`step_filter_decisions`)

A decision is dropped when it names a tag, fires a missing event, or sits in `Byzantine_Decisions.txt`
(`DEAD_BYZANTINE_DECISION_FILES`). Formation files in `VANILLA_FORMATION_FILES` and the electorate stubs
(`VANILLA_STUB_DECISION_FILES`) are curated by hand; same-filename files win whole, so dropped keys stay dead.

## Missing event references (`step_dangling` in `steps/eventrefs.py`)

After events are cut, other loading files (on_actions, scripted effects, disasters, rebel types, reforms, incidents,
parliament issues, imperial reforms) may fire events that no longer exist; `dangling()` scans the mod's own files and the
base-game files that still load (not those under `replace_path`, not ones the mod overrides). The step writes an override of each such file
with the dead `country_event|province_event|news_event` calls and dead `events = { }` / `random_events = { }` ids removed.
`eventrefs.dangling()` lists what is left; validate fails if it is not empty ("nothing fires a missing event"). Our own
hand-written content that fires a vendored vanilla event must name an id that survived.

## Pitfalls

- Effect blocks scoped to a bare province id (`123 = { ... }`) take no `limit`: use `if = { limit = { 123 = { ... } } }`.
- Same-key localisation conflicts resolve base-game-side: vanilla renames must live in `localisation/replace/`.
- After editing a parser in `ck3.py`, bump `_CACHE_VERSION`; never edit `tools/cache/` by hand.
