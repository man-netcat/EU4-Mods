#!/usr/bin/env python3
"""common/religions/00_religion.txt and its localisation and interface sprites, lifted.

EU4's own religions file is the base. Every religion the mod adds is a clone of
a vanilla religion (a block copied under a new key, in a place of its group),
and every religion that stands for a CK3 faith takes that faith's colour and
name; the Christian-group faiths whose rules differ from their parent carry a
few line edits (EXTRAS). The religion icon strips are numbered in ICON_ORDER
(vanilla's frames come first). Nothing of either game is kept in the repository:
the files are rewritten whenever they differ, before anything reads them.

    python3 tools/religions.py          # rewrite
    python3 tools/religions.py --check  # exit 1 if stale
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import EU4_GAME  # noqa: E402

MOD = os.path.join(HERE, "..")
OUT = os.path.join(MOD, "common", "religions", "00_religion.txt")
LOC = os.path.join(MOD, "localisation", "replace", "karolingian_religion_l_english.yml")
VANILLA = os.path.join(str(EU4_GAME), "common", "religions", "00_religion.txt")
INTERFACE = os.path.join(MOD, "interface")
VANILLA_INTERFACE = os.path.join(str(EU4_GAME), "interface")

# religion -> (clone of, group, listed after, line edits (old, new) on the clone, description).
# The religions for CK3 faiths EU4 lacks are in faiths.NEW_RELIGIONS (plain clones);
# these differ from the parent they clone.
_DREAMTIME_TAIL = (
    "\t\t\n\t\tfetishist_cult = yes\n\t\theretic = { WAGYLKOOP MOORAMOORA GINGARRURNDE }\n",
    "\t\tprovince = {\n\t\t\tlocal_missionary_strength = 0.02\n\t\t}\n",
)
_DREAMTIME_SECONDARY = (
    "\t\t\tshock_damage = 0.1\n\t\t\thostile_attrition = 2\n",
    "\t\t\tmerc_maintenance_modifier = -0.1\n\t\t\tgalley_power = 0.2\n",
)


def _dreamtime(country_line):
    return (
        ("\t\t\tshock_damage_received = -0.05\n\t\t\tdiplomatic_reputation = 1\n",
         "\t\t\t" + country_line + "\n"),
        _DREAMTIME_SECONDARY,
        _DREAMTIME_TAIL,
    )


EXTRAS = {
    "apostolic": ("coptic", "christian", "coptic", (), "The Armenian Apostolic Church of Etchmiadzin, Miaphysite out of Chalcedon like the Copts, and no part of their communion."),
    "nestorian": ("coptic", "christian", "apostolic", (
        ("\t\t\tdefensiveness = 0.15\n\t\t\ttolerance_own = 1\n",
         "\t\t\ttolerance_heathen = 1\n\t\t\tglobal_trade_power = 0.05\n"),
        ("\t\t\tsiege_ability = 0.1\n\t\t\tdefensiveness = 0.1\n", "\t\t\tglobal_trade_power = 0.05\n"),
        ("\t\t\torthodox\n", "\t\t\torthodox\n\t\t\tcatholic\n"),
        ("heretic = { ZAMIKAELITES STEPHANITES EUSTATHIANS }", "heretic = { MESSALIANS }"),
        ("holy_sites = { 358 1227 2313 1234 419 }", "holy_sites = { 379 410 2313 537 2218 }"),
    ), "The Church of the East, severed from the communion of the empire since Ephesus, kept by the Patriarch of Baghdad and carried east along the Silk Road by merchant missionaries."),
    "romuva": ("dreamtime", "christian", "nestorian", _dreamtime("defensiveness = 0.15"), "The old Baltic faith of Dievas, Perkunas and Gabija, kept beneath the sacred oaks."),
    "suomenusko": ("dreamtime", "christian", "romuva", _dreamtime("hostile_attrition = 1"), "The old Finnish faith of Ukko, Tapio and the spirits of forest and water."),
    "slavic": ("dreamtime", "christian", "suomenusko", _dreamtime("land_forcelimit_modifier = 0.10"), "The faith of Perun and Veles, of the old gods worshipped in groves and on hilltops."),
    "krstjani": ("animism", "christian", "slavic", (
        ("\t\t\tglobal_unrest = -1\n", ""),
        ("\t\t\ttolerance_own = 2\n\t\t\tloot_amount = 0.25\n",
         "\t\t\tmerc_maintenance_modifier = -0.1\n\t\t\tgalley_power = 0.2\n"),
        ("\t\t\n\t\theretic = { SNAKE_CLAN }\n", ""),
    ), "Long forgotten by Catholic and Orthodox alike, the Krstjani of the Bosnian highlands are more permissive than their better-known compatriots, but lack formal structure."),
    "taltosist": ("dreamtime", "christian", "krstjani", _dreamtime("cavalry_power = 0.10"), "The old Magyar faith of the táltos, seers who ride between sky and steppe."),
    "khurmazdis": ("zoroastrian", "zoroastrian_group", "zoroastrian", (), "The old royal Zoroastrianism of Khwarezm: to Khurmazt, lord of the fire altars of Khiva and Gurganj, worshipped by the Afrigids and their people."),
}

# the religions that take a frame of their own on the icon strips, after vanilla's
# (coptic keeps its vanilla block but gets a new frame)
ICON_ORDER = (
    "romuva",
    "suomenusko",
    "slavic",
    "krstjani",
    "taltosist",
    "apostolic",
    "coptic",
    "nestorian",
    "khurmazdis",
    "shaivism",
    "vaishnavism",
    "achamanism",
    "utaki",
    "kamuyism",
    "hantuism",
    "shangqing",
    "zhengyi",
    "maitreya",
    "manichaean",
    "moism",
    "dab_qhuas",
    "haymanot",
    "waaqism",
    "kushitism",
    "kabarism",
    "siberian",
    "bon",
    "kiratism",
    "bimoism",
    "satsana_phi",
    "jainism",
    "shaktism",
    "smartism",
    "sedism",
    "melieism",
    "rrmeaism",
    "bilikuism",
    "kaharingan",
    "tolotang",
    "aluk",
    "dayawism",
    "roog_sene",
    "siguism",
    "akom",
    "bidaism",
    "orisa",
    "bori",
    "ngaiism",
    "mu",
    "mazdakism",
    "khurramism",
    "afridunism",
    "zunism",
)

# interface sprites whose frame counts the mod changes besides the religion strips
SPRITE_FRAMES = {
    "provinceview.gfx": {"GFX_resource_icon": 34, "GFX_resource_icon_small": 34,
                         "GFX_resource_icon_transparent": 34},
}
INTERFACE_FILES = ("countryview.gfx", "ledger.gfx", "provinceview.gfx", "countrydiplomacyview.gfx")


# ---- text plumbing -----------------------------------------------------------

def _read(path):
    return open(path, encoding="cp1252", errors="replace").read().replace("\r\n", "\n")


def block_range(text, key):
    return re.search(r"(?m)^\t%s = \{.*?^\t\}(?=\n)" % re.escape(key), text, re.S)


def _clone(text, key, src, group, after, edits):
    sm = block_range(text, src)
    if not sm:
        raise SystemExit(f"religions: clone source {src} for {key} not found")
    block = re.sub(r"^\t%s = \{" % re.escape(src), "\t%s = {" % key, sm.group(0), count=1)
    for old, new in edits:
        if old not in block:
            raise SystemExit(f"religions: edit for {key} does not apply: {old!r}")
        block = block.replace(old, new, 1)
    am = block_range(text, after)
    if not am:
        return None  # the sibling is not placed yet
    return text[:am.end()] + "\n\n" + block + text[am.end():]


def _set_line(text, key, name, value):
    """Set `name = value` (a single-line value) in the religion's own block."""
    m = block_range(text, key)
    blk = m.group(0)
    new, n = re.subn(r"(?m)^(\t\t%s\s*=\s*).*$" % re.escape(name), lambda x: x.group(1) + value, blk, count=1)
    if not n:
        raise SystemExit(f"religions: {key} has no {name} line")
    return text[:m.start()] + new + text[m.end():]


def vanilla_frames():
    """Frames of the religion strip in the base game (what ICON_ORDER continues)."""
    t = _read(os.path.join(VANILLA_INTERFACE, "countryview.gfx"))
    m = re.search(r'name = "GFX_icon_religion"[^{}]*?noOfFrames\s*=\s*(\d+)', t)
    return int(m.group(1))


def religion_text():
    import faiths

    text = _read(VANILLA)
    pending = {k: (v[0], v[1], v[2], v[4] if False else ()) for k, v in EXTRAS.items()}
    pending.update({k: (v[0], v[1], v[2], ()) for k, v in faiths.NEW_RELIGIONS.items()})
    edits = {k: v[3] for k, v in EXTRAS.items()}
    while pending:
        progressed = False
        for key in list(pending):
            src, group, after, _e = pending[key]
            new = _clone(text, key, src, group, after, edits.get(key, ()))
            if new is not None:
                text = new
                del pending[key]
                progressed = True
        if not progressed:
            raise SystemExit(f"religions: cannot place {sorted(pending)} (their sibling is missing)")
    for faith, key in faiths.FAITH_RELIGION.items():
        info = faiths.ck3_faith(faith)
        if block_range(text, key) and info and info["color"]:
            text = _set_line(text, key, "color", "{ %d %d %d }" % info["color"])
    base = vanilla_frames()
    for i, key in enumerate(ICON_ORDER, 1):
        text = _set_line(text, key, "icon", str(base + i))
    import rites

    return rites.patch_text(text)


DESC_NONE = ("catholic",)  # the base game's own description stays


def religion_loc(text):
    import faiths

    descs = {k: v[3] for k, v in faiths.NEW_RELIGIONS.items()}
    descs.update({k: v[4] for k, v in EXTRAS.items()})
    lines = ["l_english:"]
    for faith, key in faiths.FAITH_RELIGION.items():
        info = faiths.ck3_faith(faith)
        if not block_range(text, key) or not info or not info["name"]:
            continue
        lines.append(f' {key}:0 "{info["name"]}"')
        if key not in DESC_NONE:
            lines.append(f' {key}_desc:0 "{descs.get(key) or "The " + info["name"] + " faith."}"')
    return "\n".join(lines) + "\n"


def strip_frames(name, px):
    """Frames of an image strip the mod ships (width / frame size), or None when the
    image is not there (images are made by a local run, not by the text build)."""
    import struct

    path = os.path.join(MOD, "gfx", "interface", name)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as fh:
        head = fh.read(24)
    return struct.unpack("<I", head[16:20])[0] // px if head[:4] == b"DDS " else None


# sprite -> (strip file, frame size): the sprites that follow a strip of ours
STRIP_SPRITES = {
    "GFX_icon_religion": ("icon_religion.dds", 64),
    "GFX_country_icon_religion": ("country_icon_religion.dds", 64),
    "GFX_religion_icon_strip": ("icon_religion.dds", 64),
    "GFX_icon_religion_small": ("icon_religion_small.dds", 32),
    "GFX_province_view_religion": ("province_view_religion.dds", 32),
    "GFX_government_rank_strip": ("government_rank_strip.dds", 40),
}


def interface_texts():
    """The interface files: the base game's, with the frame count of each sprite that
    uses one of our strips set to that strip's frames (left alone where the image is
    absent, as in a package built from the text alone), and the other fixed counts."""
    out = {}
    for fn in INTERFACE_FILES:
        t = _read(os.path.join(VANILLA_INTERFACE, fn))
        for name, (strip, px) in STRIP_SPRITES.items():
            n = strip_frames(strip, px)
            if n:
                t = re.sub(r'(name = "%s"[^{}]*?noOfFrames\s*=\s*)\d+' % re.escape(name),
                           lambda m: m.group(1) + str(n), t)
        for name, n in SPRITE_FRAMES.get(fn, {}).items():
            t = re.sub(r'(name = "%s"[^{}]*?noOfFrames\s*=\s*)\d+' % re.escape(name), lambda m: m.group(1) + str(n), t)
        out[os.path.join(INTERFACE, fn)] = t
    return out


def targets():
    text = religion_text()
    t = [(OUT, text, "cp1252"), (LOC, religion_loc(text), "utf-8-sig")]
    t += [(p, s, "cp1252") for p, s in interface_texts().items()]
    return t


def write(check=False):
    stale = []
    for path, text, enc in targets():
        old = None
        if os.path.exists(path):
            old = open(path, encoding=enc, errors="replace", newline="").read()
        if old != text:
            stale.append(path)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding=enc, errors="replace", newline="") as f:
                    f.write(text)
    return stale


_done = False


def ensure():
    global _done
    if not _done:
        _done = True
        write()


if __name__ == "__main__":
    check = "--check" in sys.argv
    stale = write(check)
    for p in stale:
        print(("stale: " if check else "wrote ") + os.path.relpath(p, MOD))
    sys.exit(1 if (check and stale) else 0)
