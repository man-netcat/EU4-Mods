# Formable Nation Template

Step-by-step guide for adding a new formable nation to **Yet Another More Formables Mod**.

Each formable needs files across 6 directories. Use existing formables as reference — **Pakistan** is the simplest example (no events, no culture changes).

---

## 1. Country Tag

**File:** `common/country_tags/more_formables.txt`

Add a new line with your 3-letter tag and country filename:

```
PAK = "countries/Pakistan"
```

Tag must be unique across ALL EU4 tags (vanilla + mods). Check `common/country_tags/` in the base game to avoid conflicts.

---

## 2. Country Definition

**File:** `common/countries/<CountryName>.txt`

Defines colors, unit types, leader names, ship names. Template:

```
graphical_culture = westerngfx     # or easterngfx, asiangfx, etc.
color = { R G B }
revolutionary_colors = { R G B }
historical_idea_groups = { ... }
historical_units = { ... }
monarch_names = { "Name #number" = weight ... }
leader_names = { ... }
ship_names = { ... }
```

Key choices:
- **graphical_culture**: `westerngfx` (Europe), `easterngfx` (Eastern Europe/Russia), `asiangfx` (East/Southeast Asia)
- **historical_units**: Must match the tech group of the forming nation (e.g., `indian_*` for Indian tech, `western_*` for Western, `eastern_*` for Eastern)
- **color**: RGB 0-255. This is the map color.
- **monarch_names**: Format is `"Name #dynasty_num" = weight`. Higher weight = more frequent. Negative weight = female names.

---

## 3. History File

**File:** `history/countries/<TAG> - <CountryName>.txt`

Starting government, religion, culture, tech. Only needed for nations that EXIST at game start (1444). If the nation is only formed via decision, this file is still required but can be minimal:

```
government = monarchy
religion = catholic
culture = bosnian
capital = 140     # province ID
addAcceptedCulture = croatian
admiral_names = { ... }
general_names = { ... }
ruler_names = { ... }
heir_names = { ... }
queen_names = { ... }
}

startup_monarch = {
    name = "Name"
    dip = 3
    adm = 3
    mil = 3
    female = no
    birth_date = 1400.1.1
    death_date = 1465.1.1
    heir = {
        name = "Heir"
        birth_date = 1430.1.1
        claim = 95
    }
}
```

If the tag is only formed via decision (never exists at start), you still need the file with at minimum:
```
government = monarchy
capital = <province_id>
```

---

## 4. Decision

**File:** `decisions/<formable_name>_decisions.txt`

One file per formable group (e.g., all Slavic formables share one file, Pakistan has its own).

Structure:
```
country_decisions = {
    form_<name> = {
        major = yes
        potential = { ... }     # When to SHOW the decision
        provinces_to_highlight = { ... }  # What provinces glow on map
        allow = { ... }         # Requirements to click it
        effect = { ... }        # What happens when formed
        ai_will_do = { factor = 1 }
    }
}
```

### potential block (visibility):
```
NOT = { has_country_flag = formed_<name>_flag }   # prevent re-forming
NOT = { exists = <TAG> }                          # tag must not exist
OR = { primary_culture = <culture> ... }           # who can form it
is_colonial_nation = no
```

### allow block (requirements):
```
is_at_war = no
is_free_or_tributary_trigger = yes
adm_tech = <number>          # tech requirement
owns_core_province = <id>    # key provinces
```

### effect block (formation):
```
change_tag = <TAG>
set_government_rank = <2 or 3>
add_prestige = 25
set_country_flag = formed_<name>_flag
# Add permanent claims on surrounding areas
<area_name> = {
    limit = { NOT = { owned_by = ROOT } NOT = { is_permanent_claim = ROOT } }
    add_permanent_claim = <TAG>
}
# Offer custom ideas
if = { limit = { has_custom_ideas = no } country_event = { id = ideagroups.1 } }
on_change_tag_effect = yes
```

### Culture vs Territory Formables:
- **Culture-based** (e.g., Slovenia): Require `primary_culture = slovene` + own core provinces
- **Territory-based** (e.g., Pakistan): Require owning cores across multiple culture groups — use `calc_true_if` with areas
- **Both** (e.g., Yugoslavia): Require specific culture AND owning many provinces of that culture group

---

## 5. National Ideas

**File:** `common/ideas/<formable>_ideas.txt`

One file per formable or group. Structure:

```
<TAG>_ideas = {
    start = { <tradition bonuses> }
    bonus = { <ambition bonus> }
    trigger = { tag = <TAG> }
    free = yes

    <idea_key_1> = { <modifiers> }
    <idea_key_2> = { <modifiers> }
    ...7 ideas total (traditions + 7 ideas + ambition = 9 slots)
}
```

Rules:
- Traditions = 2 modifiers, Ambition = 1 modifier
- 7 ideas in between (some can be empty with `{}` for placeholder)
- Idea keys must be unique across the entire mod
- Prefix with tag to avoid collisions (e.g., `pak_`, `slv_`, `cze_`)

---

## 6. Localisation

**File:** `localisation/english/<formable>_l_english.yml`

All display strings for the formable. Must include:

```yaml
l_english:
 <TAG>:0 "Display Name"
 <TAG>_ADJ:0 "Adjective"
 form_<name>_title:0 "Form <Name>"
 form_<name>_desc:0 "Flavour text for the decision tooltip"
 <TAG>_ideas:0 "<Name> Ideas"
 <TAG>_ideas_start:0 "<Name> Traditions"
 <TAG>_ideas_bonus:0 "<Name> Ambition"
 <idea_key_1>:0 "Idea Name"
 <idea_key_1>_desc:0 "Idea description"
 ... (repeat for all 7 ideas)
```

If the formable has a rename event (like Finno-Ugria → Ugria), also add:
```yaml
 <ALT_NAME>:0 "Alternate Name"
 <ALT_NAME>_ADJ:0 "Alternate Adjective"
```

**Important:** Localisation files MUST be in `localisation/english/` (not `localisation/`) for EU4 1.37+.

---

## 7. Events (Optional)

**File:** `events/<formable>_events.txt`

Only needed if the formable has a rename event or other post-formation events. One namespace per file:

```
namespace = <tag>

country_event = {
    id = <tag>.1
    title = <tag>.1.t
    desc = <tag>.1.d
    picture = DIPLOMACY_eventPicture
    fire_only_once = yes
    trigger = { tag = <TAG> }
    immediate = { }
    option = {
        name = <tag>.1.a
        override_country_name = <ALT_NAME>
    }
    option = {
        name = <tag>.1.b
        # Keep default name
    }
}
```

Add loc for event strings:
```yaml
 <tag>.1.t:0 "Event Title"
 <tag>.1.d:0 "Event Description"
 <tag>.1.a:0 "Option A text"
 <tag>.1.b:0 "Option B text"
```

---

## 8. Culture Changes (Optional)

If the formable merges or renames cultures (like Finno-Ugria):

**File:** `common/cultures/<formable>_cultures.txt`

Defines the new culture group with all the name lists. Use `update_entire_culture_foreign` in the decision effect to migrate existing nations.

---

## 9. Opinion Modifiers (Optional)

**File:** `common/opinion_modifiers/<formable>_opinion_modifiers.txt`

If the formable adds diplomatic bonuses with specific nations:
```
finno_ugric_cousins = {
    opiniom_min = -10
    opiniom_max = 10
    years = 50
}
```

---

## 10. Event Modifiers (Optional)

**File:** `common/event_modifiers/<formable>_modifiers.txt`

Named modifiers applied via decisions/events:
```
ukrainian_identity = {
    prestige = 0.5
    legitimacy = 0.5
}
```

---

## Checklist for New Formable

- [ ] 3-letter tag chosen (check no conflicts)
- [ ] `common/country_tags/more_formables.txt` — tag added
- [ ] `common/countries/<Name>.txt` — country definition
- [ ] `history/countries/<TAG> - <Name>.txt` — starting history
- [ ] `decisions/<name>_decisions.txt` — formation decision
- [ ] `common/ideas/<tag>_ideas.txt` — national ideas (7 ideas)
- [ ] `localisation/english/<name>_l_english.yml` — all loc strings
- [ ] `events/<name>_events.txt` — (optional) rename/formation events
- [ ] `.tga` flag file in `gfx/flags/<TAG>.tga` — 82x32 BMP converted to TGA
- [ ] Test in EU4: tag switch via console `tag <TAG>`, form via decision, check loc
