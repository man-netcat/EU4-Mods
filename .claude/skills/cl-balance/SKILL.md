---
name: cl-balance
description: Estimating and tuning what each realm can field in Charlemagne's Legacy - tools/troops.py, the force-limit and manpower model, and the subject-type and static-modifier levers. Use before changing any force limit, manpower or subject-type number.
---

# Balance: troops

```bash
python3 tools/troops.py [N]       # the N largest sovereign tags (default 40)
python3 tools/troops.py --all     # every sovereign tag
python3 tools/troops.py --csv     # the table as CSV
```

Columns: provinces, development, force limit own / from subjects / total, manpower (thousands) own / from subjects /
total, and the "bloc" (own plus every subject's full figure, to show who stands behind a realm).

**Model (a ranking, not in-game numbers):** force limit = (6 `all_nations` + 0.1 per development point, minus 3 for a
subject) x (1 + `land_forcelimit_modifier` of the tag's government reforms); manpower = (10 + 0.25 per manpower
development point) thousand x (1 + `global_manpower_modifier`). A subject adds its own figure times its subject type's
`forcelimit_to_overlord` / `manpower_to_overlord`. Autonomy, buildings, ideas, religion and rank modifiers and the base
game's defines (not in the reference copy) are not modelled; the manpower constants are unverified.

## Rules the user set

- **No subject adds force limit or manpower to its overlord:** `vassal`, `march` and `theme_subject_type` are 0 (the colonial
  types keep vanilla's values). Troops come from development alone. Other sources (the +6 base, reform and religion
  percentages) are open questions: ask before removing them.
- Change numbers only through `tools/vanillapatch.py` (subject types, static modifiers) or the tag database, never in output.
  Validate's "subject types = vanilla copy with only the vassal cap lifted and the vassal force limit cut" expects the exact
  diff list in `checks/diplomacy.py` (`expected_sdiff`); update both together.
- State balance claims as model results, give the figures, and ask when a target ("no Carolingian kingdom above 30") is
  ambiguous: own figure or with vassals.
