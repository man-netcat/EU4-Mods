---
name: verify-build
description: Rebuild, validate, and debug Charlemagne's Legacy with logs and byte-identical diffs
---

# Verify the build

## Workflow

1. From the mod root, run:
   `python3 tools/build.py` (~2 s warm, ~40 s cold) then `python3 tools/validate.py` (~3 s). Both must be green before anything ships. Build phases are listed in `tools/build.py:16-30`; the first failure aborts the run.
2. For refactors/optimisations: `git diff` on generated output must stay byte-identical. Any diff beyond the intended files means the refactor changed behaviour — fix it, do not ship it.
3. For in-game failures: read `~/.local/share/Paradox Interactive/Europa Universalis IV/logs/error.log` (per-launch; invaluable for in-game debugging). Reproduce, fix the source (DB or `tools/*.py` — never hand-edit generated output), rebuild, revalidate, relaunch.
4. When verifying whitespace-sensitive edits (tabs, escapes, BOM), read the bytes back (`repr` / hex), never trust tool echoes — tabs and escapes have been mangled in transit before.
5. Discipline: never edit the `.mod` files while the game/launcher runs (it rewrites the outer file and drops `replace_path` lines); empty replace-dirs need their `.gitkeep`; commit only when explicitly asked, with prose subjects; leave the tree clean. Test evidence (logs, diffs, in-game confirmation) beats theory.
