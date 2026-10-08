---
name: eu4-mission-trees
description: Use when writing, editing, or reviewing EU4 mission trees or mission files (missions/*.txt, `<TAG>_missions`, `slot =`/`generic =`/`ai =` mission slots, `required_missions`, `provinces_to_highlight`, `on_action`-style `on_change_tag_effect` mission swapping). Covers basegame mission structure, tag binding, icon and localisation requirements, and how to derive missions from a form-decision's province requirements.
---

# EU4 Mission Trees

Reference for authoring mission trees in Europa Universalis IV. Verified
against basegame 1.37 (`/home/rick/Paradox/Games/Europa Universalis IV`).

## Where missions live

Missions go in a `missions/` folder at the mod root. There is **no index
file and no registration entry** - the engine loads every `.txt` in
`missions/` and picks a slot's tree by its `potential`. Adding a file is
enough; nothing else in the mod needs to mention it.

## Slot structure

Each top-level block in a mission file is one **slot**. A country gets slot
1 first, then slot 2, and so on.

```
<prefix>_missions_<name> = {
	slot = 1
	generic = no
	ai = yes
	potential_on_load = { ... }   # evaluated at load, before potential
	potential = { ... }
	has_country_shield = yes

	<mission_id> = { ... }
}
```

- `generic = no` - a named tree, not the filler tree every country gets.
- `ai = yes` - the AI will attempt it. Set `no` for player-only trees.
- `has_country_shield = yes` - draws the country shield on the tree.
- `potential` - **this is the tag binding.** The tree only appears for a
  country matching it.
- `potential_on_load` - for DLC checks, so the tree is correct immediately
  on load rather than after the first tag change.

### Tag binding

```
potential = {
	has_dlc = "Emperor"
	OR = {
		tag = SAX
		tag = THU
		tag = SXN
	}
	NOT = { map_setup = map_setup_random }
}
```

- Use `was_tag = X` alongside `tag = Y` to keep a tree when a country
  form-decision does `change_tag` (see "Tag changes" below).
- Guard with `NOT = { map_setup = map_setup_random }` so the tree does not
  appear on random maps.
- **Only add `has_dlc` if the content genuinely needs that DLC.** A tree for
  a DLC-free decision must stay DLC-free, or it will be invisible in a
  vanilla install. Cross-check the target decision for a `has_dlc` gate
  before adding one.

## Mission structure

```
<mission_id> = {
	icon = <icon_name>
	position = <int>
	required_missions = { <ids> }
	provinces_to_highlight = { ... }
	trigger = { ... }
	effect = { ... }
	ai_weight = { factor = <int> }
}
```

- `position` is a grid hint, **not** a strict sequence. Basegame trees skip
  numbers freely (`EMP_Burgundian_Missions.txt` uses 2,4,4,5,6,6,6,7), and
  parallel branches share a number. Siblings at the same position render side
  by side. Gaps are fine; only `required_missions` defines real order.
- `required_missions = { }` empty means the mission is available at the start.
- `icon` must resolve to `gfx/interface/missions/**/<name>.dds`. A missing
  icon yields a broken tree, so verify every icon path before shipping.
- Every id in `required_missions` must exist in the same file. A dangling id
  silently breaks the tree.

## Trigger vs provinces_to_highlight

`trigger` decides completion. `provinces_to_highlight` only decides what the
map shading shows, so it must mirror the trigger or the player sees a
completed mission still shaded as unconquered.

Complete-area pattern (the form-decision shape):

```
provinces_to_highlight = {
	area = savoy_dauphine_area
	NOT = { owned_by = root }
	NOT = { is_core = root }
}
trigger = {
	savoy_dauphine_area = {
		type = all
		owned_by = ROOT
		is_core = ROOT
	}
}
```

- `type = all` inside a scope means every province in it must match. This is
  the right check when a form decision demands the whole area.
- `num_of_owned_provinces_with = { value = N area = X }` is the right check
  when a threshold is acceptable, or when counting through subjects.
- `num_of_provinces_owned_or_owned_by_non_sovereign_subjects_with` counts
  vassal-held land too - only use it if the decision does as well.
- `NOT = { country_or_non_sovereign_subject_holds = ROOT }` excludes land
  held by anyone but the root.

`root` and `ROOT` are both used in vanilla. Match the surrounding file.

## Effects

Common engine-native effects, all confirmed present in basegame missions:

| Effect | Use |
|--------|-----|
| `add_permanent_claim = ROOT` | hand out the claim that makes the next mission reachable |
| `add_prestige = N` | default reward |
| `add_dip_power` / `add_adm_power` / `add_mil_power = N` | reward by domain |
| `add_stability = 0.05` | small, not more than ~0.1 per mission |
| `add_manpower = N` | reward for a war mission |
| `set_government_rank = N` | raise rank on a capstone |
| `add_country_modifier = { name = ... duration = N }` | temporary buff |
| `add_accepted_culture = <culture>` | bare value, no braces |
| `add_nationalism = -N` | inside a per-province scope |
| `add_province_modifier = { name = ... duration = N }` | per-province, needs a defined modifier |

### Claim hand-off pattern

A conquest tree that targets a form decision must keep the player able to
reach it. Grant the claim for the *next* stage in the current mission's
effect, guarded so it never double-applies:

```
effect = {
	next_area = {
		limit = {
			NOT = { is_core = ROOT }
			NOT = { is_permanent_claim = ROOT }
		}
		add_permanent_claim = ROOT
	}
}
```

Without this the tree dead-ends: the player completes a mission and has no
claim to start the next one.

## Localisation

Missions need two keys per mission, in a `localisation/*_l_english.yml`:

```
<mission_id>_title:0 "Short imperative title"
<mission_id>_desc:0 "Prose, 2nd person plural."
```

- Keys are the **mission id**, not the slot name.
- The mod convention is 2-space indent under `l_english:`, files UTF-8
  **with BOM**. Appending must preserve the BOM - check with
  `head -c3 file | od -An -tx1` expecting `ef bb bf`.
- Use `[Root.GetName]`, `[Root.GetRootAdjMP]` etc. for dynamic text.
- Basegame splits these across themed files (`scandinavia_l_english.yml`,
  `emperor_missions_l_english.yml`); a mod can use one file for all its
  missions.

## Deriving a tree from a form decision

When the tree's goal is "conquer everything needed to form X", the decision
is the specification. Read its `allow` block and turn each requirement into
one mission:

1. List every area/province the decision requires owned **and** cored.
2. Make one mission per area, in an order that is survivable: own home
   ground, then the neighbour that unlocks the rest, then the remote fronts.
3. The opening mission should establish the starting province, since a
   released tag may hold a core it does not yet own.
4. Have each mission's effect grant claims for the next stage.
5. The capstone mission's `trigger` should **mirror the decision's `allow`
   block exactly**. If the decision needs all 16 provinces across 4 areas,
   the capstone checks all 16 and nothing weaker.
6. Do not re-implement formation in the mission. Let the player take the
   decision; the mission's job is to make it available and reward the state
   that permits it.

## Tag changes and mission swapping

`change_tag = ARS` in a decision **does not** carry missions over. To avoid
a tag ending up with no tree:

- Add `was_tag = <old>` to the new tree's `potential`, alongside
  `tag = <new>`.
- In the decision effect, use:
  ```
  on_change_tag_effect = yes
  swap_non_generic_missions = yes
  if = {
      limit = {
          has_custom_ideas = no
          NOT = { has_idea_group = <TAG>_ideas }
      }
      country_event = { id = ideagroups.1 }
  }
  ```
  A `<TAG>_ideas` group also does **not** follow `change_tag`; that event is
  the vanilla mechanism for swapping it in.

## Validation checklist

Run before shipping:

```
# braces balance
python3 - <<'EOF'
import re
s = re.sub(r'#.*', '', open("missions/<FILE>.txt", encoding="utf-8").read())
d = 0
for ch in s:
    d += (ch == '{') - (ch == '}')
print("depth", d)
EOF
```

- Every `required_missions` id exists in the file.
- Every `icon` resolves to a `.dds` under `gfx/interface/missions/`.
- Every `<mission_id>_title` and `_desc` exists in localisation.
- Every `area =` exists in basegame `map/area.txt` as `<name>_area = {`.
- Every `province_id =` / bare province scope exists in
  `history/provinces/<id> - *.txt`.
- Every area used in an effect is real (`piedmont_area`, `lombardy_area`,
  `po_valley_area` are not the only valid ones - check).
- Localisation files still carry their BOM.
- `git diff --check` clean.

## Basegame files worth reading

- `missions/SCA_Swedish_Missions.txt` - compact, area-per-mission, good
  template. `provence_area`/`savoy_dauphine_area` conquest plus Italian
  claims is nearly the same shape.
- `missions/EMP_Burgundian_Missions.txt` - `emp_bur_cisjurania` is the
  vanilla Arles-adjacent mission and a direct model for an Arles tree.
- `missions/EMP_Savoyard-Piedmontese_missions.txt` - Savoy/Piedmont area
  conquest with claims.
- `missions/01_Generic_European_Missions.txt` - the generic filler tree
  (`generic = yes`), for comparison against a named tree.
