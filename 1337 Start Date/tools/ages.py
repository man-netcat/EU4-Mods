"""An Age of Traditions before the base game's Age of Discovery (1400), as EU5 opens with its own.

Written at build time:
  common/ages/00_traditions.txt          the age: five objectives lifted from the base game's Age of Discovery (their
                                         names and localisation are the base game's) and four abilities of our own whose
                                         modifiers are checked against the base game's idea modifiers
  common/scripted_effects/               the (empty) per-age hook the base game defines for each of its ages
  interface/ages_view.gui                the base game's file with a window for the new age, copied from the Discovery one
  interface/1337_ages.gfx                the new age's popup picture (the Discovery picture until it gets its own)
  localisation/1337_ages_l_english.yml
"""
import re

from paths import EU4_GAME, MOD

AGE = "age_of_traditions"
LIFTED = ("obj_5_centers_of_trade", "obj_30_development_city", "obj_two_unions", "obj_many_vassals",
          "obj_humiliate_rival")
# (ability, modifier, name, description)
ABILITIES = (
    ("ab_trad_feudal_levies", "land_forcelimit_modifier", "Feudal Levies", "The realm's levies answer the call in greater numbers."),
    ("ab_trad_royal_demesne", "global_tax_modifier", "Royal Demesne", "Crown lands and customary dues fill the treasury."),
    ("ab_trad_customary_law", "stability_cost_modifier", "Customary Law", "Settled custom keeps the realm orderly."),
    ("ab_trad_court_of_honour", "diplomatic_reputation", "Court of Honour", "A court of chivalry lends the ruler standing abroad."),
)


def _block(text, start):
    """text of the `{ ... }` block opening at or after index `start`, braces included."""
    i = text.index("{", start)
    depth, j = 0, i
    while True:
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        j += 1
        if depth == 0:
            return text[i:j]


def age_text(mods):
    src = (EU4_GAME / "common/ages/00_default.txt").read_text(encoding="latin-1")
    disc = src[src.index("age_of_discovery = {"):src.index("age_of_reformation = {")]
    objectives = []
    for name in LIFTED:
        m = re.search(rf"(?m)^\t\t{name} = \{{", disc)
        if not m:
            raise SystemExit(f"ages: the base game's Age of Discovery has no objective {name}")
        objectives.append("\t\t" + name + " = " + _block(disc, m.start()).replace("\n", "\n"))
    out = [f"{AGE} = {{", "\tstart = 1337", "", "\tcan_start = {", "\t\talways = yes", "\t}", "",
           "\tpapacy = 1.0", "", "\tobjectives = {", *objectives, "\t}", "", "\tabilities = {"]
    for key, mod, _n, _d in ABILITIES:
        if not mods.get(mod, {}).get("idea"):
            raise SystemExit(f"ages: {mod} is not a modifier the base game's ideas use")
        v = round(sorted(mods[mod]["idea"])[len(mods[mod]["idea"]) // 2], 3)
        out += [f"\t\t{key} = {{", "\t\t\teffect = {", f"\t\t\t\ton_age_ability_taken = {{ age = {AGE} }}", "\t\t\t}",
                "\t\t\tmodifier = {", f"\t\t\t\t{mod} = {v}", "\t\t\t\tnum_of_age_rewards = 1", "\t\t\t}",
                "\t\t\tai_will_do = {", "\t\t\t\tfactor = 10", "\t\t\t}", "\t\t}"]
    out += ["\t}", "}"]
    return "\n".join(out) + "\n"


def gui_text():
    src = (EU4_GAME / "interface/ages_view.gui").read_text(encoding="latin-1")
    m = re.search(r'WindowType = \{\s*name = "age_of_discovery"', src)
    win = src[m.start():m.start() + len(_block(src, m.start())) + (src.index("{", m.start()) - m.start())]
    # the window is the Discovery one (large icon for the current age, small ones for the later), renamed; the sound
    # and the pictures stay the base game's Discovery ones until the age has its own
    new = win.replace("age_of_discovery", AGE).replace(f"upsound = {AGE}", "upsound = age_of_discovery")
    return src[:m.start()] + new + "\n\t\t\n\t\t" + src[m.start():]


def write(mods):
    d = MOD / "common/ages"
    d.mkdir(parents=True, exist_ok=True)
    (d / "00_traditions.txt").write_bytes(age_text(mods).encode("latin-1", "replace"))
    e = MOD / "common/scripted_effects"
    e.mkdir(parents=True, exist_ok=True)
    (e / "1337_age_effects.txt").write_text(f"on_age_ability_taken_{AGE} = {{ }}\n")
    i = MOD / "interface"
    i.mkdir(parents=True, exist_ok=True)
    (i / "ages_view.gui").write_bytes(gui_text().encode("latin-1", "replace"))
    (i / "1337_ages.gfx").write_text(
        'spriteTypes = {\n\tspriteType = {\n\t\tname = "GFX_age_of_traditions"\n'
        '\t\ttexturefile = "gfx/interface/ages/age_of_discovery.tga"\n\t\tloadType = "INGAME"\n\t}\n}\n')
    loc = ["l_english:", f" {AGE}:0 \"Age of Traditions\"", f" {AGE}_short:0 \"Traditions\"",
           f" {AGE}_desc:0 \"Realms are held together by custom, kinship and the oaths of lords.\\nFor a ruler with an eye to the future this age is one of patient consolidation before the world widens.\""]
    for key, _m, name, desc in ABILITIES:
        loc += [f' {key}:0 "{name}"', f' {key}_desc:0 "{desc}"']
    (MOD / "localisation/1337_ages_l_english.yml").write_text("﻿" + "\n".join(loc) + "\n", encoding="utf-8")
    return len(LIFTED), len(ABILITIES)
