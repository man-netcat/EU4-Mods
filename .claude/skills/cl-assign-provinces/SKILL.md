---
name: cl-assign-provinces
description: Task - give provinces to a tag, move them between tags, or fix a province that sits with the wrong tag against CK3's 867 owner, in Charlemagne's Legacy. Covers addtag.py --to, capitals, cores, forts, and the CK3-owner rule.
---

# Assign provinces

Ownership is the `tag_provinces(tag, pid)` table (and `tag_areas` for whole areas). Never edit `history/provinces/` (the
build wipes and rewrites it).

## The rule

A province belongs to the tag of the **sovereign of its CK3 county's 867 holder**, with that holder's vassals folded in -
unless the realm has a separate tag for the vassal's duchy (governors, `cl-subjects`). When the data and the checks
disagree, **move the province to its CK3 owner's tag**, not the other way round (the user's standing instruction).
Find the owner:

```python
import sys; sys.path.insert(0, "tools")
import state867 as S, provfaiths as pf
cn = pf.PROVINCE_COUNTY[pid]; h = S.holder(cn); sov, top = S.sovereign(h)
print(cn, h, S.primary(h), "sovereign", sov, top)      # then find the tag whose title/ruler is that sovereign
```

`lieges.governor_province_mismatches()` (validate) lists the BYZ/ARB provinces that sit wrongly; `lieges.py` checks lieges.
`python3 tools/audit_provinces.py` is the whole-map audit (read-only unless `--apply`): `--classify` gives each hit its evidence,
`--apply [PID,..]` moves the trusted ones (name-matched pairing plus geography) or exactly the listed PIDs, keeps every tag
alive and re-seats a lost capital. Read `tools/PROVINCE_AUDIT.md` first: the pairing is an approximation (homonyms, several
provinces to one county), so **decide per hit whether the pairing or the owner is wrong**. Wrong pairing: add the pid to the
audit block in `tools/provfaiths.py` and run `provfaiths.py apply`; wrong owner: `--apply PID`. Never bulk-apply the
untrusted classes; ask the user. validate fails if the hit count exceeds `BACKLOG` (`tools/checks/provinces.py`): lower it
when you work hits off.

## Move

```bash
python3 tools/addtag.py --to TAG PID [PID ...] --take      # --take when another tag owns them
```

- For a province that no tag owns yet and whose vanilla file has no culture/religion, pass `--culture/--religion`
  (documented exceptions: ask). Existing `provinces` rows keep the culture and faith already in the DB.
- The previous owner's cores are dropped at build. A province may carry only its owner's core, plus `seed_cores`
  releasables; never add a core by hand (validate "no dormant cores").
- If the moved province was a tag's **capital**, point that tag at another of its provinces, or validate fails
  ("holds its mod capital"):
  `python3 -c "import sqlite3;c=sqlite3.connect('tools/tags.db');c.execute(\"update tags set capital=? where tag=?\",(PID,'TAG'));c.commit()"`
- A province that is a `seed_cores` or `formable_provinces` entry keeps its meaning; check that a formable's requirement
  land, a start-date war's `goal_province`, or an event list (the Meerssen partition lists LOT's provinces) still agrees.

## Province facts

- Culture and faith of an owned province follow its CK3 county (`provfaiths.py`: `python3 tools/provfaiths.py` audits,
  `... apply` writes the expected values into the DB; do not hand-set them).
- Every owned province must be paired with a CK3 county in `provfaiths.PROVINCE_COUNTY` (a curated table); a new province
  without a pair fails validate.
- Forts exist only where `provinces.fort` is set (the stone-walled cities listed in AGENTS.md); the build strips the rest.
- Development, trade goods and buildings come from the base game's province files and are not changed by moves.

Then `build.py`, `validate.py`, and update any paragraph in `AGENTS.md` that lists the province. Check CI.
