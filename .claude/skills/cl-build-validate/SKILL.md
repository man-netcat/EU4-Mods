---
name: cl-build-validate
description: Build, validate, self-contain-check, commit, push and check CI for Charlemagne's Legacy in a cloud session - including the one-time reference-repo setup. Use after any change to tools/, tags.db or hand-authored mod files.
---

# Build, validate, push, check CI

Work from `"/home/user/EU4-Mods/Charlemagne's Legacy"`.

## One-time setup in a cloud session

The base games are not on the machine. They come from the private repo `man-netcat/eu4-ck3-reference`.

1. `mcp__claude-code-remote__add_repo` with owner `man-netcat`, repo `eu4-ck3-reference`; clone the command it returns
   next to this repo (`/home/user/eu4-ck3-reference`, shallow, one git operation at a time), then
   `register_repo_root`.
2. `bash "Charlemagne's Legacy/tools/cloud_setup.sh"` (the SessionStart hook in `.claude/settings.json` also runs it):
   installs `tools/requirements.txt` and, when the clone exists, appends `EU4_GAME`/`CK3_GAME` to `CLAUDE_ENV_FILE`.
3. If the variables are not set in your shell (they often are not in a fresh Bash call):
   `export EU4_GAME=/home/user/eu4-ck3-reference/eu4 CK3_GAME=/home/user/eu4-ck3-reference/ck3/game`
   (absolute paths). The 1337 tools find EU5 at `<reference>/eu5` by themselves.

## The loop

```bash
cd "/home/user/EU4-Mods/Charlemagne's Legacy"
python3 tools/build.py        # ~90-130 s in the cloud; stops at the first failing phase
python3 tools/validate.py     # ~55 s; must end "ALL CHECKS PASSED"
python3 tools/selfcontained.py  # ~2-3 min; must end "SELF-CONTAINED: the mod rebuilds from tools/ alone"
```

- `build.py` runs the phases listed in `PHASES` (probe, vanilla patches, tag database check, rites, tag names, government
  titles, province files, country files, empire decision, diplomacy, wars, Magyars, vanilla realm colours, formation
  triggers, releasable events, vanilla events, vanilla decisions, missing-event strip, CK3 ruler check, start-date
  ownership). Read the tail of its output; `BUILD OK` is the success line.
- `validate.py` prints `OK`/`WARN`/`FAIL` lines per check and ends with `ALL CHECKS PASSED` or `N FAILURES`. WARNs
  (placeholder flags, child rulers under regency, "at the limit" relation slots, icons not checked) do not fail it.
  Filter with `python3 tools/validate.py 2>&1 | grep -E "FAIL|ALL CHECKS"`.
- Run `build.py` before `validate.py` after any data change: validate compares the written files with the database.
- Generated output must be committed with the change: CI fails if `git diff` shows the build changed any file.
- Run long commands in the foreground with a generous `timeout` (up to 600000 ms) or in the background; a foreground
  `sleep` is blocked.

## Commit and push

- Branch: the one the session names. `git push -u origin <branch>` (retry only on network errors, 2/4/8/16 s).
- End the commit message with the attribution lines the session's system reminder gives (never invent a session URL).
- Prose subjects; no PR unless the user asks.

## Check CI after every push (the user requires it)

Workflow "Charlemagne's Legacy" (`.github/workflows/charlemagnes-legacy.yml`) runs three jobs:
1. Rebuild from `tools/` alone (`selfcontained.py`), 2. Build + validate + "the committed files are what the build
writes", 3. Build the upload package (`build.py --release`; fails if game material would ship; the slowest, finishes a
few minutes after the other two).

1. Load the tool: `ToolSearch` with `select:mcp__github__actions_list`.
2. `list_workflow_runs` (owner `man-netcat`, repo `EU4-Mods`, `workflow_runs_filter` `{"branch": "<branch>"}`, `perPage` 1).
   Match `head_sha` to your commit.
3. If `status` is `in_progress`, `list_workflow_jobs` (`resource_id` = run id, `workflow_jobs_filter` `{"filter":"latest"}`)
   shows which job is still running. Wait with the `Monitor` tool (`sleep 240; echo ready`); never Bash `sleep`.
4. Report each job's conclusion honestly. A red job: `get_job_logs` (load via ToolSearch), reproduce locally, fix, push, check again.

The CI needs the `REFERENCE_REPO_TOKEN` repository secret; a failure at the reference checkout is a secret problem, not code.
