---
name: cl-new-war
description: Task - add a start-date war (history/wars) to Charlemagne's Legacy, with the engine pitfalls that already crashed the game once.
---

# A start-date war

Wars are rows, not files: `wars(slug, title, cb, goal, goal_tag, date, goal_province)` and
`war_sides(war, tag, side)` with `side` = `attacker` or `defender`. `step_wars` writes `history/wars/<slug>.txt` and
deletes stale ones; never hand-write the files (`history/wars` is replace_path'd: only these load).

```python
import sqlite3
c = sqlite3.connect("tools/tags.db")
c.execute("insert into wars values(?,?,?,?,?,?,?)", ("kar_x", "Name of the War", "cb_conquest", "take_claim", None, "867.1.1", 231))
for tag, side in (("ASU", "attacker"), ("ADU", "defender")):
    c.execute("insert into war_sides values(?,?,?)", ("kar_x", tag, side))
c.commit()
```

Rules (selfcheck and validate enforce most):
- **Goal:** conquest-family goals (`take_claim`, `take_border`) need `goal_province` (a segfault in
  `CWar::AddAttacker`/`CProvince::AddAsClaim` came from `tag =` there); throne and independence goals
  (`defend_capital_independence`, `humiliate`...) use `goal_tag`. Exactly one of the two is set.
- **Casus belli:** a real CB: the base game's `common/cb_types/00_cb_types.txt` or our own file in `common/cb_types/`
  (`cb_magyar_migration` is ours). Validate: "preset wars use live tags and real CBs".
- **Sides:** live tags only (landed tags, not dormant), no subject fighting its overlord (all existing wars use proven
  mechanics only).
- **Date:** `YYYY.M.D` on or before the start (the Andalusian rebellion is 866.1.1).
- A war needs the attacker to be able to win on paper; the Magyar war needed a general, a reform and mercenaries to be
  playable (AGENTS.md): check balance with `cl-balance` before adding one.
- Claims the war uses are written by the Reconquista claims rule or another province-file rule, not by the war.

`build.py` then `validate.py`; report the war as untested in-game.
