---
name: cl-lift-region
description: Task - turn a region's CK3 867 states into tags (liftstates.py), then finish names, titles, flags and checks, in Charlemagne's Legacy.
---

# Lift a region

`python3 tools/liftstates.py REGION` plans; `... REGION apply` writes. Region keys are in `REGIONS` in `liftstates.py`
(seasia, china, maritime, westafrica, eastside, rebalance, manchuria, balhaekorea, india, or add one: a list of EU4 region
names, province ids, or `"@TAG"` meaning every province the tag owns now).

What it does: every EU4 province of the region that `provfaiths.PROVINCE_COUNTY` pairs with a CK3 county goes to the state
that county belongs to at 867 (holder's `liege =` chain to the top; the sovereign gets it with its vassals; independent
counts, dukes and tributaries are states of their own). Existing tags with the state's primary title keep their code and
gain or lose provinces; new tags get a free three-letter code made from the name, the ruler's culture and faith.
The province pairing is a curated table, so a region with unpaired provinces must get its pairs first.

After `apply`, in order:
1. `python3 tools/retag.py suggest N` (N = first new seq) and apply what it names (`cl-retag`: names equal to a free
   base-game tag reuse it, except formable collisions).
2. `python3 tools/culturetitles.py TAGS` and `python3 tools/culturalnames.py apply TAGS` (`cl-tag-identity`).
3. `python3 tools/tagloc.py write`, `python3 tools/placeholder_flags.py`.
4. Governors and vassals as the user decides (`cl-subjects`); never assume.
5. `build.py`, `validate.py`, `selfcontained.py`, update `AGENTS.md`, commit, check CI.
