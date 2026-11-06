---
name: cl-remove-tag
description: Task - delete a tag from Charlemagne's Legacy (or merge it into another) without leaving stale rows, files or flags behind.
---

# Remove or merge a tag

Never delete only the DB row: the build does not purge a removed tag's generated files.

1. **Land first.** A landed tag's provinces go to another tag (`cl-assign-provinces`: `addtag.py --to NEW PID... --take`),
   or the tag is dissolved by an event (see `cl-events`). A releasable is merged by moving its `seed_cores` pids to the
   survivor (`cl-releasables`).
2. **Relations and users.** Other tables that name it: `diplomacy`, `rivalries`, `friendships`, `wars`/`war_sides`,
   `tags.forms`/`decision` of starters, `formable_renames`, `core_deny`, `seed_cores`, `releasables`. `retag.TABLES` is the
   list. Do not remove a formable's own code this way (`formables.tag`); that is a formable change (`cl-formables`).
   Grep hand-written files for the code: `grep -rnw CODE --include=*.txt --include=*.yml --include=*.py .`
   (events, modifiers, on_actions, missions, `common/government_names`, docs).
3. **Rows.**
   ```python
   import sqlite3, sys; sys.path.insert(0, "tools")
   import retag
   c = sqlite3.connect("tools/tags.db")
   for table, col in retag.TABLES:
       c.execute(f"delete from {table} where {col}=?", ("CODE",))
   c.commit()
   ```
   Also delete its `tag_reforms` rows (included in `TABLES`) and, if it owned a capital shared with others, check nothing
   else references the province as a capital.
4. **Files:** `history/countries/CODE - *.txt`, `common/countries/<its country file>`, `gfx/flags/CODE.tga` (only if it is a
   placeholder: `python3 tools/placeholder_flags.py --list`; a real flag is the user's: ask).
5. **Base-game code freed:** if it was a reused base-game tag, remove the code from `VANILLA_REUSE` in `tools/checks/tags.py`
   (validate "no accidental vanilla tag reuse"), and the vanilla country file returns as a landless base-game tag.
6. `python3 tools/tagloc.py write; python3 tools/build.py; python3 tools/validate.py; python3 tools/selfcontained.py`, update
   `AGENTS.md`, commit, check CI.
