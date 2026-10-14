# PLANNING.md — parked plans (do not execute without asking)

## Fort audit (parked)

Goal: review all 186 vanilla `fort_15th` persistences for 867
appropriateness. Most are 15th-century-level anachronisms kept by the
parity convention; known-good: Constantinople's Theodosian Walls.
Known-removed: Budjak/Akkerman (no fortress there in 867), stripped via
`provinces.no_fort` + `strip_fort` — reuse that mechanism per province.

## Feudal vassal gameplay (parked)

Goal: heavier emphasis on vassals for the feudal era — many more tags as
vassals without constant rebellions. Andalusia work comes first.

### Premise check (from vanilla files, this install)

There is NO direct "vassal count → liberty desire" tax. A swarm is
punished by four indirect mechanics:

1. **Power pooling** — vanilla vassals are `relative_power_class = 2`:
   each vassal weighs the *combined* strength of all fellow vassals
   against the overlord. This is the real "many vassals rebel" engine.
2. **Diplomatic slots** — vassals eat one relation each (base ~4);
   over the cap bleeds diplomatic power monthly.
3. **Correlated shocks** — overlord war exhaustion, mercantilism and
   prestige hit every vassal's desire at once, so swarms tip together.
4. No annexation backlash here (`LIBERTY_DESIRE_ANNEXATION = 0`).

Relevant vanilla references: `common/subject_types/00_subject_types.txt`
(`base_liberty_desire`, `relative_power_class`, `takes_diplo_slot`,
`can_be_annexed`; vassal pools, march −15, appanage +35(!), tributary
−5/no-slot/no-pool), `common/defines.lua` (`LIBERTY_DESIRE_*`,
`HIGH_LIBERTY_DESIRE = 50`, `DIPLOANNEX_LIBERTY_THRESHOLD = 50`).

### Options

- **A. Light tuning** (cheap, global side effects): our `defines.lua`
  is a full copy — more base upkeep, gentler relative-power weight,
  higher rebellion threshold. Calms the whole world, not just feudals.
- **B. Feudal subject type** (right shape, needs in-game testing):
  `copy_from = vassal` with negative base desire,
  `relative_power_class = 1` (no pooling), optionally no dip slot and
  no annexation. Placed at start via `history/diplomacy` (supported;
  mid-game creation via diplomats is the "not very functional" part).
- **C. Feudal reforms** (flavor + progression): our reforms file covers
  monarchies only; a feudal track (+relations, −desire, +contribution).

### Tensions (decide before building)

1. **Formations need owned land** — vassal land does not count toward
   `num_of_owned_provinces_with`. A full swarm blocks formables; keep
   requirement zones directly held or accept the block.
2. **Khazar patchwork uses tributaries regardless** — `tributary_state`
   is already swarm-stable (−5, no slot, no pooling).

### Recommendation

B for heartland vassals + tributaries for the steppe + C later.
A only if the whole world should be calmer (not recommended).

### Open questions for the user

1. Target density: 3–5 vassals per overlord, or a real swarm (8–12)?
2. Prototype the custom type now (needs in-game testing) or tune first?
