---
name: insert-db
description: Insert tag, land, and base-game data into tools/tags.db and let scripts generate code from it
---

# DB first — never hardcode tag data in scripts

`tools/tags.db` is the single source of truth. Scripts (`tools/*.py`) contain generic logic plus engine-fixed constants only (start date 867.1.1, rank tiers c1/d2/k3/e4, file paths, sea/waste/lake engine lists). Any vanilla-specific or mod-specific fact about a tag — land, culture, religion, colour, ruler link, reforms, relations, claims, requirements — goes in the DB, and the scripts generate code from it. Do not add new per-tag/per-area constants to `.py` files; route new cases through the tables below.

## Tables (`tools/models.py`, FKs enforced via `tools/db.py:13-15`)

- `tags(tag,seq,rank,name,capital,culture,religion,ck3_title,ruler_title,government,technology_group,extra,no_heir_sync,color_r/g/b,country_file,historical_score,rev_r/g/b,historical_units,monarch_names,leader_names,ship_names,forms,decision,flag_from,flag_source)` — 159 rows. One row per landed realm.
- `provinces(pid,name,culture,religion)` — 964 rows. FK target: insert before linking.
- `tag_provinces(tag,pid)` / `tag_areas(tag,area)` — land. Explicit pids override areas at build (`tools/eu4.py:102-155`).
- `tag_reforms(tag,pos,reform)` — one `feudalism_reform` row per tag.
- `tag_suppress(tag,key)` — vanilla formation keys this tag neutralizes.
- `formables(tag,name,adj,ck3_title,rank,color_r/g/b,percent,capital,own_capital,culture,dynasty,culture_group,home_capital,rank_required,exclusive)` + `formable_areas` / `formable_provinces` / `formable_renames(formable,culture,tag,name)` — no start land; see the add-formable skill.
- `diplomacy(liege,subject,relation)` / `rivalries(tag,other)` / `friendships(tag,other)` / `core_deny(holder,owner)` — relations and dormant claims.
- `wars(slug,title,cb,goal,goal_tag,goal_province,date)` + `war_sides(war,tag,side)` — exactly one of `goal_tag`/`goal_province`.
- `cultures(name)` / `religions(name)` — lookup tables; insert before a tag references the key.

## Workflow

1. Read the schema in `tools/models.py` and the loader in `tools/tagdb.py:180-314` before writing anything. For landed tags prefer `python3 tools/addtag.py TAG ck3_title PID...` (see the add-tag skill) — it does the INSERTs plus the loc pair correctly. For everything else write a small `sqlite3`/`SQLAlchemy` insert (via `tools/db.py:Session`), respecting FK order: `cultures`/`religions`/`provinces` first, then `tags`, then link rows.
2. Fill every required field: `capital` + `culture` + `religion` (no build-time invention); `ruler_title` only beside `ck3_title`; `forms` only with `decision` pointing at a known formable; `own_capital` only with `capital`; never `own_capital` + `home_capital` together (`tools/tagdb.py:374-475`).
3. When tempted to hardcode (a new area set, tag list, or claim rule in `eu4.py`/`histgen.py`/`validate.py`), stop and model it as rows instead: land → `tag_areas`/`tag_provinces`, dormant claims → `core_deny`, relations → `diplomacy`, requirements → `formable_areas`/`formable_provinces`, renames → `formable_renames`. Grandfathered constants (`IBERIA_AREAS`, `HUN_AREAS`, `FINLAND_AREAS`, `VANILLA_FORMATION_FILES`, `VANILLA_REUSE`) stay; add no new ones.
4. Verify: `python3 -c "import tagdb"` runs `selfcheck()` on import (shared decision per formable, culture/group gates, rename xor, war-goal xor, HLR-only empty land). Then `python3 tools/build.py && python3 tools/validate.py` — both green. Use `git diff` on generated output to confirm refactors stay byte-identical.
5. Never hand-edit generated files (`history/`, `common/countries/`, `common/country_tags/`, `decisions/`, cloned `gfx/flags/`) — they are overwritten. Never touch `tools/cache/`. Commit only when explicitly asked.
