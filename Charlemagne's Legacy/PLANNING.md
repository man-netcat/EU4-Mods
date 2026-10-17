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

## Abbasid decline disaster (parked)

Goal: nerf the Abbasids via a break-up disaster, modeled on the vanilla
`decline_of_mali` (`common/disasters/decline_of_mali.txt` +
`events/flavorMAL.txt`.9–23) — progress/can_start/can_stop/modifier/on_start/
on_end/on_monthly pattern, `progress = { modifier = { factor = 100 } }` to
tick fast, the ARB tag as `potential`.

History for flavor: 867 is mid-"Anarchy at Samarra" (861–870, four caliphs
deposed/murdered in nine years, treasury broke, Turkish guard in command);
Ya'qub al-Saffar took Nishapur in the start year; Tulunid Egypt stops
tribute from 868/878; Zanj revolt 869–883 devastates Lower Iraq; the last
true revival is al-Mu'tadid–al-Muktafi (892–908); the Buyids take Baghdad
in 945 and passive decline follows (the caliphate's nominal end is 1258).

Beats, in order:
1. `on_start`: stability −1 ("the Anarchy has begun").
2. **Tulunid breakaway** (the first monthly event, fire-once guarded):
   fires for ARB; `every_subject_country = { limit = { tag = EGY }
   grant_independence = yes }` — quiet, NO war (the vanilla
   Japan/Georgian-crisis precedent; historically Ahmad ibn Tulun simply
   withheld the kharaj and the mutinous caliphate never marched). If a war
   flavor is ever wanted instead, fire the event for EGY with an
   independence-declaration option.
3. **Zanj revolt**: `spawn_rebels = { type = peasant_rebels size = 3 }`
   (rebel-spawn effect verified in vanilla `flavor_mal.16`) in Lower
   Iraq: Basra 408, Hillah 409, Wasit 2312.
4. Optional further beats (pick among): Kharijite riders in the Jazira
   (`noble_rebels` in Arbil 4293), treasury collapse (pay the army vs
   arrears: lose ducats vs discipline/manpower hit), more breakaways.

Prerequisites not yet in the tree:
- `diplomacy` row `ARB -> EGY vassal` (Tulunids as caliphal vassals at
  start; EGY already displays "Tulunids", holder is Ahmad ibn Tulun).
- Disaster + event files: `common/disasters/AnarchyAtSamarra.txt`,
  `events/AnarchyAtSamarra.txt` (both non-vanilla names), loc in a
  `karolingian_*_l_english.yml` file (BOM), ids `namespace = kar_anarchy`
  with house `kar_anarchy_N_title/_desc/_a` keys (MagyarSettlement style),
  `grant_independence`/`spawn_rebels` scopes as above.

Open questions for the user (decide before building):
1. What ends the disaster: `can_end = { stability = 1 }`-style threshold,
   or a scripted "al-Mu'tadid revival" event?
2. Progress speed (Mali ticks within months; maybe gate on ruler/lack of
   claims instead)?
3. Which optional beats make the final chain?
4. Does ARB keep any claim/CB on Egypt after the break?

Toolchain note: tags no longer take manual `--culture/--religion` for
values that the 867 ruler already provides (addtag now lifts both from
the ruler; manual args are a documented exception only).
