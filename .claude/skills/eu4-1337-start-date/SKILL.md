---
name: eu4-1337-start-date
description: Build and validate the "1337 Start Date" EU4 mod (generated from EU5's 1337 setup) in a cloud session, and what may be hand-edited.
---

# 1337 Start Date

An EU4 mod starting 1337.4.1, generated from EU5's 1337 setup. Read `1337 Start Date/PLAN.md` first.

- **Never hand-edit** `history/`, `common/countries`, `common/country_tags/1337_tags.txt` and its localisation file
  (`localisation/1337_countries_l_english.yml`): change `tools/` or `tools/data/*.json` and rebuild.
- Environment: the base games come from the reference repo (see `cl-build-validate`, setup steps 1-3). `EU4_GAME` is the
  reference's `eu4`; EU5 is found at `<reference>/eu5` automatically, or set `EU5_GAME` to its `eu5` directory.

```bash
cd "/home/user/EU4-Mods/1337 Start Date/tools"
python3 fuzzy_aliases.py && python3 loc2prov.py && python3 tables.py   # only after changing mapping inputs (data/aliases.json ...)
python3 build.py && python3 validate.py                                # must end ALL CHECKS PASSED
```

- Stdlib only. Output is deterministic; CI (`.github/workflows/1337-start-date.yml`) regenerates, validates and fails if the
  committed output differs, so commit the regenerated files with the change.
- `python3 tools/audit_regions.py europe` lists the low-confidence province mappings (PLAN.md, Europe).
- Log each historical correction of EU5 in `tools/corrections.md`.
- Check CI after every push as in `cl-build-validate`, but for the workflow named "1337 Start Date".
