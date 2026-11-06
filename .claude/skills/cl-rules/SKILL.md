---
name: cl-rules
description: Standing rules for Charlemagne's Legacy (the generated CK3-867 EU4 mod). Read before changing anything in "Charlemagne's Legacy/" - it says what may be hand-edited, what must go through tags.db and the build, and what needs the user's say-so first.
---

# Charlemagne's Legacy: standing rules

The mod is generated. Read `Charlemagne's Legacy/AGENTS.md` for the long form (parts are older than this skill: the
verifier now lives in `tools/checks/`, the build in `tools/steps/`, and the vanilla-reuse guard `VANILLA_REUSE` is in
`tools/checks/tags.py`, not `validate.py`; the machine paths at its top are the author's, not the cloud's).

## What you may edit

- **Source of truth:** `tools/tags.db` (SQLite) and the code in `tools/`. Change those, rebuild, commit the
  regenerated output together with the change that caused it.
- **Hand-authored files** (never regenerated): own events (`events/IberianInstability.txt`, `IberianKingdoms.txt`,
  `LotharingianPartition.txt`, `FallOf*.txt`...), `missions/Reconquista.txt`, `common/event_modifiers/kar_*`,
  `common/on_actions/{Iberian,Slavic,Magyar}OnActions.txt`, hand-written localisation, `AGENTS.md`, `README.md`.
- **Generated, never hand-edit:** `history/`, `common/countries/`, `common/country_tags/00_karolingian_custom.txt`,
  `decisions/Form*.txt` and `decisions/KarolingianHRE.txt`, `localisation/replace/countries_l_english.yml`,
  `events/KarReleasables.txt`, vendored vanilla events/decisions (same names as the base game's), the cultures and
  religions files, and the files `tools/vanillapatch.py` writes. A hand edit is lost on the next build.
- **Never touch base-game files.** `gfx/flags/*.tga` that are not placeholders are the user's own work: never overwrite
  or delete one without asking. Never reuse a base-game flag.

## Rules the user has set (keep following them)

- **CK3 is the only source of truth.** Names, rulers, cultures, faiths, lieges, titles and holders are lifted from CK3's
  867 data by the build; nothing of CK3's is stored by hand. If the resolver disagrees with CK3's data, suspect the
  resolver. Where history (not CK3) supplies something, say so and get the user's OK first (Meerssen split, governors).
- **Never carve an exception** (allowlist, override table, hand-set deviating value) without asking the user.
- **Never assume formable requirements** (land, starters, percent, capital, rank, CK3 title): ask.
- **A tag whose name equals a free base-game tag's name reuses that tag**, whatever its government (`cl-retag`),
  except where that vanilla tag is already one of our formables (LIT, BOH, CAS).
- **No dormant cores:** a province is cored by its owner alone, bar the `seed_cores` releasables.
- **No subject adds force limit or manpower to its overlord;** troops come from development alone.
- **Provinces follow their CK3 holder:** when the check says a province sits with the wrong tag, move it to its CK3
  owner's tag (`cl-add-tag`), not the other way round.
- **Commit and push to the branch the session names; open no pull request unless asked.** After every push, check CI
  and report the result (`cl-build-validate`).
- **Cloud sessions cannot** run EU4 or CK3, bake coat-of-arms flags, or update the reference repo. Say which of your
  results are untested in-game; the owner validates in-game and pastes `error.log`.
- Stdlib plus `requirements.txt` (sqlalchemy, pillow, numpy) only. Do not hardcode machine paths; `tools/paths.py`
  reads `EU4_GAME`, `CK3_GAME`, `EU4_MODS_DIR`, `PATRUM_SCUTA`.
- Be honest in reports: if a check or CI job failed or has not finished, say so with the evidence.
