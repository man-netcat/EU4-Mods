---
name: add-war
description: Add a preset start-date war to Charlemagne's Legacy without tripping the conquest-goal crash
---

# Add a preset start-date war

One file per war in `history/wars/` (replace_path — no vanilla content loads there). Precedents: Alfonso's invasion (ASU vs ADU over Andalusia), the Andalusian Rebellion (PRT+TOL vs ADU for independence), the Magyar migration (MGY vs BUL/TRA/VSG under the custom `cb_magyar_migration`). No subjects fight overlords — use proven mechanics only. See `AGENTS.md` metadata section, `tools/models.py:182-202`, `tools/tagdb.py:383-394`, `tools/eu4.py:861-887`, `tools/validate.py:1196-1224`.

## Workflow

1. Insert the DB rows: `wars(slug,title,cb,goal,goal_tag,goal_province,date)` plus `war_sides(war,tag,side)` with `side` attacker/defender. Exactly one of `goal_tag`/`goal_province` (xor, enforced by `selfcheck`); every side must be a live tag; both sides need at least one entry.
2. Crash lesson (Oct 2026, SIGSEGV in `CWar::AddAttacker`→`CProvince::AddAsClaim`): conquest-family goals (`take_claim`, `take_border`) must use `province = <claimed pid>` — vanilla never uses `tag` there and the claim lookup segfaults without it. Throne/independence-capital goals use `tag = <country>`. The writer (`tools/eu4.py:871-874`) emits `province=` iff `goal_province` is set, else `tag=` — pick the right column, never both.
3. The `goal_province` for a conquest goal must actually be claimed (claims are written by `patch()`/`core_deny` rules); the CB must exist in vanilla `common/cb_types/00_cb_types.txt` or our own additive `common/cb_types/` dir (keep the `cb_` prefix; add a loc pair). To forbid land-taking, point the war at a humiliate-table wargoal (`humiliate`: gold + humiliate only) via a custom CB file instead of scripting the deal.
4. The build writes `history/wars/<slug>.txt` as `name` + `war_goal = { type / casus_belli / province|tag }` + `<date> = { add_attacker / add_defender }`. Never hand-edit it.
5. Victory behaviour beyond the peace deal (basin-wide transfers, tag changes) does not live in the CB: hook `on_war_won` from an additive `common/on_actions/` file (same-key blocks coexist across files; carry only the guard) and put the shared body in a `common/scripted_effects/` file both paths call. Precedent: `MagyarOnActions.txt` + `MagyarEffects.txt`. Emergent states are released Jerusalem-style (seed cores, then `release = TAG`, then configure in-scope) — never pre-seeded as land-holders, never rebels: list them in tagdb `DORMANT`.
6. Run `python3 tools/build.py && python3 tools/validate.py` — validate guards live sides and real CBs. Confirm firable in-game when the setup is novel.
