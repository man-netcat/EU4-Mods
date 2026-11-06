---
name: cl-events
description: Writing hand-authored events, modifiers, on_actions and localisation for Charlemagne's Legacy - file locations, encodings, the effect and trigger patterns already used (release, cede_province, vassalize, break_union), and which validate checks guard them.
---

# Authoring content

Hand-authored files are listed in `cl-rules`. Generated ones (`events/KarReleasables.txt`, `decisions/Form*.txt`) are not
edited. Everything unplayed must be reported as untested; the owner playtests and pastes `error.log`.

## Files and encodings

- Events: `events/<Name>.txt`, `namespace = <ns>`, ids `<ns>.N`. Write script as **cp1252** (keep it ASCII where possible;
  generated files use cp1252, vendored vanilla events utf-8).
- Localisation: `localisation/<name>_l_english.yml`, **UTF-8 with BOM**, first line `l_english:`, entries ` key:0 "text"`
  (`\n` for newlines). Validate fails a BOM-less file. Tag names use `[TAG.GetName]`, not baked names. Latin-1 only for
  map-visible names (the map font lacks U+0100 and above).
- Modifiers: `common/event_modifiers/kar_*.txt`. on_actions: our own additive files in `common/on_actions/` (same-key
  blocks coexist). Missions: `missions/Reconquista.txt` (the `missions` folder is replace_path'd).
- Keep new event ids unique across the mod and never fire a base-game event id that the filters dropped: validate's
  "nothing fires a missing event" scans the mod's own files (events, decisions, missions, common) and the base-game files
  that still load.

## Patterns that exist and work in the files

- Scheduled by date: `trigger = { tag = X  date = 869.8.9 }` (true from that date) with `mean_time_to_happen = { days = 3 }`
  and `fire_only_once = yes`; `is_year = Y` for year gates; follow-ups with `country_event = { id = x.4 months = 12 }`.
- Player/AI choice: `option = { name = ns.N.a  ai_chance = { factor = 100 } ... }`; give the AI the historical choice.
- Province effects: a bare province-id scope **takes no `limit` child** (the engine rejects the block and drops the effects
  around it; vanilla never writes it). Condition on ownership in an `if`:
  `if = { limit = { 91 = { owned_by = ROOT } } 91 = { remove_core = ROOT cede_province = FRA add_core = FRA } }`;
  claims: `91 = { add_permanent_claim = ROOT }` inside the same kind of `if`. Area scopes (`x_area = { limit = ... }`) do take
  limits. Validate's "no per-pid limits" fails any `PID = { limit = ... }` in our own events, scripted effects and on_actions
  (one-line or multi-line).
- Country effects: `release = TAG`, `break_union = TAG` (in the overlord's scope), `TAG = { grant_independence = yes }`, then
  `NEWLIEGE = { vassalize = TAG }`, `FRA = { country_event = { id = ... days = 10 } }`.
- Guard anything that depends on a tag existing: `if = { limit = { exists = FRA } ... }`.
- Choose the player-facing option so that the AI takes the historical branch; the player may defy.

## Guards

Add a validate check when a content file duplicates data that lives elsewhere (the Lotharingian partition's province lists
are compared with LOT's land in `checks/diplomacy.py`); do not add notes for one-offs (AGENTS.md workflow).
