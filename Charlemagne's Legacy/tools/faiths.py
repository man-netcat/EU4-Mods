#!/usr/bin/env python3
"""EU4 religions are CK3 faiths.

Every religion the mod uses is the lift of exactly one CK3 faith: its name,
map colour and icon come from CK3, and a tag's religion is the religion of
the faith its 867 ruler's rite belongs to (rite -> CK3 faith -> EU4 religion;
CK3 groups rites under faiths in common/religion/rite_types). FAITH_RELIGION
below is the one table that says which EU4 religion lifts which faith; a
faith that no tag or province needs may stay unmapped.

Usage (from the mod folder):
    python3 tools/faiths.py            # create missing religions, lift colours
                                       # and names (needs only the text files)
    python3 tools/faiths.py icons      # copy the CK3 faith icons over the religion
                                       # strips and the CK3 rite icons over the
                                       # rite placeholders (needs the CK3 install)
validate runs faiths.verify(): faith mapped, colour and name equal CK3's,
icons present, and by name which icons are still placeholders.
"""
import glob
import os
import re
import sys

from paths import CK3_GAME

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.join(HERE, "..")
REL_FILE = os.path.join(MOD, "common", "religions", "00_religion.txt")
LOC_FILE = os.path.join(MOD, "localisation", "replace", "karolingian_religion_l_english.yml")

# CK3 faith -> the EU4 religion that lifts it.
FAITH_RELIGION = {
    "christian_faith": "catholic",
    "armenian_apostolic": "apostolic",
    "miaphysitism": "coptic",
    "nestorian": "nestorian",
    "bosnian_church": "krstjani",
    "sunni": "sunni",
    "shia": "shiite",
    "kharijite": "ibadi",
    "mahayana_faith": "mahayana",
    "theravada_faith": "buddhism",
    "vajrayana_faith": "vajrayana",
    "confucian_faith": "confucianism",
    "shaiva_faith": "shaivism",
    "vaishnava_faith": "vaishnavism",
    "mazdayasna": "zoroastrian",
    "khurmazta": "khurmazdis",
    "norse_pagan": "norse_pagan_reformed",
    "tengri_pagan": "tengri_pagan_reformed",
    "slavic_pagan": "slavic",
    "baltic_pagan": "romuva",
    "finnish_pagan": "suomenusko",
    "magyar_pagan": "taltosist",
    "north_african_acham_pagan": "achamanism",
    "shinto_faith": "shinto",
    "utaki": "utaki",
    "kamuyism_pagan": "kamuyism",
    "hantuism": "hantuism",
    "shamanism": "shamanism",
    "shangqing_faith": "shangqing",
    "zhengyi": "zhengyi",
    "maitreya_faith": "maitreya",
    "manichaean_faith": "manichaean",
    "moism": "moism",
    "dab_qhuas": "dab_qhuas",
    "haymanot": "haymanot",
    "waaqism_pagan": "waaqism",
    "kushitism_pagan": "kushitism",
    "kabarism": "kabarism",
    "rabbinic_faith": "jewish",
    "siberian_pagan": "siberian",
    "bon_faith": "bon",
    "kiratism": "kiratism",
    "bimoism": "bimoism",
    "satsana_phi": "satsana_phi",
    "jain_faith": "jainism",
    "shakta_faith": "shaktism",
    "smartism": "smartism",
    "sedism": "sedism",
    "melieism": "melieism",
    "rrmeaism": "rrmeaism",
}

# Religions this module creates (cloned block, group, sibling to sit after, description)
NEW_RELIGIONS = {
    "shaivism": ("hinduism", "dharmic", "hinduism",
                 "The worship of Shiva, Lord of Yogis and of destruction and renewal, with its ascetics and temples across the subcontinent."),
    "vaishnavism": ("hinduism", "dharmic", "shaivism",
                    "The worship of Vishnu and his avatars, carried by temple and pilgrimage across the subcontinent."),
    "achamanism": ("animism", "pagan", "animism",
                   "The old faith of the Berber and Guanche peoples of the Maghreb and the Atlantic islands, with its holy places and ancestral customs."),
    "utaki": ("animism", "pagan", "achamanism",
              "The faith of the Ryukyu islands and southern Kyushu, with its sacred groves, the utaki, where the noro priestesses commune with the kami."),
    "kamuyism": ("animism", "pagan", "utaki",
                 "The faith of the Ainu and the peoples of Hokkaido and Sakhalin, who honour the kamuy, the spirits dwelling in animals, mountains and tools."),
    "hantuism": ("animism", "pagan", "kamuyism",
                 "The faith of the Austronesian peoples of Taiwan, where the hantu, the ancestral spirits, watch over the village and the hunt."),
    "shangqing": ("confucianism", "eastern", "shinto",
                  "The Highest Clarity tradition of the Daoists, with its revelations of the immortals and the scripture of the Mao Mountain."),
    "zhengyi": ("confucianism", "eastern", "shangqing",
                "The Way of Orthodox Unity, descended from the Celestial Masters, whose priests heal the sick and keep the registers of the spirits."),
    "maitreya": ("confucianism", "eastern", "zhengyi",
                 "The hope of the coming Buddha Maitreya, kept by the lay societies of the Chinese plains."),
    "manichaean": ("zoroastrian", "zoroastrian_group", "khurmazdis",
                   "The dualist faith of Mani, spread along the Silk Road and kept in the Uyghur lands and the ports of the south."),
    "moism": ("animism", "pagan", "hantuism",
              "The folk faith of the Zhuang and the peoples of the southern hills, led by its mo priests."),
    "dab_qhuas": ("animism", "pagan", "moism",
                  "The faith of the Hmong and the hill peoples of the south, in which the dab, the spirits of house and hill, are honoured."),
    "haymanot": ("jewish", "jewish_group", "jewish",
                 "The Judaism of the Beta Israel of the Ethiopian highlands, kept by their monks and smiths under the mountain kings."),
    "waaqism": ("animism", "pagan", "dab_qhuas",
                "The faith of the Cushitic peoples of the Horn, who honour Waaq, the sky god, and hold their assemblies under the sacred trees."),
    "kabarism": ("jewish", "jewish_group", "haymanot",
                 "The Judaism of the Khazar khagans and their court at Itil, carried along the steppe roads by Radhanite merchants."),
    "bon": ("animism", "pagan", "siberian",
            "The old religion of Tibet, older than the Buddha's teaching, whose priests make offerings to the mountain gods and the spirits of the high plateau."),
    "kiratism": ("animism", "pagan", "bon",
                 "The Mundhum of the Kirati peoples of the eastern Himalayan foothills, who honour their ancestors and the spirits of the hills and rivers."),
    "bimoism": ("animism", "pagan", "kiratism",
                "The faith of the Yi peoples of the south-western mountains, led by their bimo priests, keepers of the ancestral scriptures."),
    "satsana_phi": ("animism", "pagan", "bimoism",
                    "The spirit faith of the Tai peoples, in which the phi, the spirits of house, field and village, are placated by the elders."),
    "siberian": ("animism", "pagan", "kushitism",
                 "The shamanism of the Komi, Khanty and the peoples of the northern forests, who honour the spirits of the river, the bear and the sacred groves of the Urals."),
    "kushitism": ("animism", "pagan", "waaqism",
                  "The ancient faith of the Kushite and Beja peoples of the Nile and the Red Sea hills, whose holy places lie at Aswan and Naqis."),
    "jainism": ("hinduism", "dharmic", "vaishnavism",
                "The path of the Tirthankaras and of ahimsa, kept by monks and lay merchants in the cities and courts of western and southern India."),
    "shaktism": ("hinduism", "dharmic", "jainism",
                 "The worship of the Goddess in her many forms, with its temples and its tantric masters across Bengal, Kashmir and the south."),
    "smartism": ("hinduism", "dharmic", "shaktism",
                 "The tradition of the smriti and of Advaita, which honours five deities as aspects of one and is kept by learned Brahmins."),
    "sedism": ("animism", "pagan", "satsana_phi",
               "The faith of the Meitei of Manipur, who honour Sanamahi and the lai, the spirits of the land, at the lairembi shrines."),
    "melieism": ("animism", "pagan", "sedism",
                 "The ancestral faith of the Qiangic and Tangut peoples of the north-western marches, whose shamans read the stars and keep the rites of their forefathers."),
    "rrmeaism": ("animism", "pagan", "melieism",
                 "The mountain faith of the Qiang of the upper Min valley, a religion of the sacred peaks and the white stones kept by their priests."),
}


# ---- CK3 data ---------------------------------------------------------------

def ck3_rites():
    """{rite: faith} for every rite CK3 defines (None when a rite names none)."""
    out = {}
    for f in glob.glob(os.path.join(CK3_GAME, "common", "religion", "rite_types", "*.txt")):
        text = open(f, encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r"^(\w+)\s*=\s*\{(.*?)^\}", text, re.M | re.S):
            fm = re.search(r"^\s*faith\s*=\s*(\w+)", m.group(2), re.M)
            out[m.group(1)] = fm.group(1) if fm else None
    return out


def rite_religion_map():
    """{CK3 rite: EU4 religion} through the rite's faith (rites of unmapped faiths are left out)."""
    return {r: FAITH_RELIGION[f] for r, f in ck3_rites().items() if f in FAITH_RELIGION}


def _rgb(raw):
    if raw.lstrip().startswith("hsv"):  # CK3 colours may be hsv { h s v }
        import colorsys

        h, sat, v = (float(n) for n in raw.replace("{", " ").replace("}", " ").split()[1:4])
        return tuple(int(c * 255 + 0.5) for c in colorsys.hsv_to_rgb(h, sat, v))
    nums = raw.replace("{", " ").replace("}", " ").split()
    if any("." in n for n in nums):
        return tuple(int(float(n) * 255 + 0.5) for n in nums)
    return tuple(int(n) for n in nums)


def ck3_faith(faith):
    """{'name', 'color', 'icon'} of a CK3 faith, from its faith_types block and localisation."""
    blk = None
    for f in glob.glob(os.path.join(CK3_GAME, "common", "religion", "faith_types", "*.txt")):
        t = open(f, encoding="utf-8-sig", errors="replace").read()
        m = re.search(rf"^{faith} = \{{(.*?)^\}}", t, re.M | re.S)
        if m:
            blk = m.group(1)
            break
    if blk is None:
        return None
    col = re.search(r"color\s*=\s*((?:hsv|rgb)?\s*\{[^}]*\})", blk)
    ic = re.search(r"icon\s*=\s*(\w+)", blk)
    name = None
    for f in glob.glob(os.path.join(CK3_GAME, "localization", "english", "**", "*.yml"), recursive=True):
        if "relig" not in f and "faith" not in f:
            continue
        lm = re.search(rf'^ {faith}:\d* "([^"]*)"', open(f, encoding="utf-8-sig", errors="replace").read(), re.M)
        if lm:
            name = lm.group(1)
            break
    if name:
        from enc import encname

        name = encname(name)  # the game drops strings with glyphs outside Latin-1 (Shintōism -> Shintoism)
    return {"name": name, "color": _rgb(col.group(1)) if col else None,
            "icon": ic.group(1) if ic else faith}  # no icon = N: CK3 uses <faith>.dds


def religion_of_faith():
    return {r: f for f, r in FAITH_RELIGION.items()}


# ---- the 00_religion.txt side ----------------------------------------------

def _read(path, enc="cp1252"):
    raw = open(path, "rb").read().decode(enc)
    return raw


def block_span(text, key):
    m = re.search(rf"^\t{re.escape(key)}\s*=\s*\{{", text, re.M)
    if not m:
        return None
    depth, i = 0, m.end() - 1
    while True:
        c = text[i]
        if c == "#":
            i = text.index("\n", i)
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return m.start(), i + 1
        i += 1


def religion_color(text, key):
    sp = block_span(text, key)
    m = re.search(r"^\t\tcolor\s*=\s*\{\s*(\d+)\s+(\d+)\s+(\d+)\s*\}", text[sp[0]:sp[1]], re.M)
    return tuple(int(x) for x in m.groups()) if m else None


def lifted_name(text, key):
    m = re.search(rf'^ {re.escape(key)}:\d* "([^"]*)"', text, re.M)
    return m.group(1) if m else None


def lift():
    """Create the missing religions, then set colour and name of every mapped
    religion to its CK3 faith's. Idempotent."""
    import addreligion

    for key, (src, group, after, desc) in NEW_RELIGIONS.items():
        text = _read(REL_FILE)
        if block_span(text, key):
            continue
        faith = religion_of_faith()[key]
        info = ck3_faith(faith)
        placeholder = _placeholder_icon(key)
        addreligion.main([key, "--clone", src, "--into", group, "--after", after,
                          "--name", info["name"], "--desc", desc,
                          "--color", *map(str, info["color"]), "--faith", placeholder])
    text = _read(REL_FILE)
    loc = open(LOC_FILE, encoding="utf-8-sig").read()
    n_col = n_name = 0
    for faith, key in FAITH_RELIGION.items():
        info = ck3_faith(faith)
        sp = block_span(text, key)
        if sp is None:
            continue  # religion not in the mod's file (verify reports it if used)
        blk = text[sp[0]:sp[1]]
        new = re.sub(r"(?m)^(\t\tcolor\s*=\s*)\{[^}]*\}", r"\g<1>{ %d %d %d }" % info["color"], blk, count=1)
        if new != blk:
            text = text[:sp[0]] + new + text[sp[1]:]
            n_col += 1
        if info["name"] and lifted_name(loc, key) != info["name"]:
            if lifted_name(loc, key) is None:
                loc = loc.rstrip("\n") + f'\n {key}:0 "{info["name"]}"\n {key}_desc:0 "The {info["name"]} faith."\n'
            else:
                was = lifted_name(loc, key)
                loc = re.sub(rf'(?m)^( {re.escape(key)}:\d* )"[^"]*"', lambda m: f'{m.group(1)}"{info["name"]}"', loc, count=1)
                # a description that is only the generated "The <name> faith." follows the name
                loc = loc.replace(f' {key}_desc:0 "The {was} faith."', f' {key}_desc:0 "The {info["name"]} faith."')
                loc = loc.replace(f' {key}_desc:0 "The Shint\u014dism faith."', f' {key}_desc:0 "The {info["name"]} faith."')
            n_name += 1
    open(REL_FILE, "w", encoding="cp1252", newline="").write(text)
    open(LOC_FILE, "w", encoding="utf-8-sig", newline="").write(loc)
    print(f"religions lifted from CK3: {n_col} colours, {n_name} names changed")


def _placeholder_icon(key):
    from PIL import Image, ImageDraw

    scratch = os.environ.get("TMPDIR", "/tmp")
    path = os.path.join(scratch, f"placeholder_{key}.png")
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 61, 61), fill=(200, 200, 200, 255), outline=(255, 255, 255, 255), width=3)
    d.text((24, 26), key[0].upper(), fill=(0, 0, 0, 255))
    im.save(path)
    return path


# ---- icons (needs the CK3 install) ------------------------------------------

def ck3_icon_file(faith):
    info = ck3_faith(faith)
    if not info or not info["icon"]:
        return None
    p = os.path.join(CK3_GAME, "gfx", "interface", "icons", "faith", info["icon"] + ".dds")
    return p if os.path.exists(p) else None


def lift_icons():
    import addreligion

    text = _read(REL_FILE)
    done = 0
    for faith, key in FAITH_RELIGION.items():
        sp = block_span(text, key)
        if sp is None:
            continue
        icon = re.search(r"(?m)^\t\ticon\s*=\s*(\d+)", text[sp[0]:sp[1]])
        src = ck3_icon_file(faith)
        if not icon or not src:
            print(f"  {key}: no icon line or no CK3 icon file for {faith} - skipped")
            continue
        addreligion.replace_frame(src, int(icon.group(1)))
        done += 1
    print(f"{done} religion icons replaced with the CK3 faith icons")
    import rites

    rites.lift_icons(force="--force" in sys.argv)


# ---- verification ------------------------------------------------------------

def verify(used):
    """Errors and warnings for the religions in `used`: each is the lift of one
    CK3 faith (name, colour), and its icon state is reported by name."""
    err, warn = [], []
    text = _read(REL_FILE)
    loc = open(LOC_FILE, encoding="utf-8-sig").read()
    by_rel = religion_of_faith()
    placeholder, unverified = [], []
    for rel in used:
        faith = by_rel.get(rel)
        if faith is None:
            err.append(f"religion '{rel}' is not lifted from a CK3 faith - map it in FAITH_RELIGION (tools/faiths.py) or replace it")
            continue
        info = ck3_faith(faith)
        if info is None or info["color"] is None:
            err.append(f"religion '{rel}': CK3 faith '{faith}' not found in faith_types")
            continue
        if block_span(text, rel) is None:
            err.append(f"religion '{rel}' (CK3 {faith}) has no block in 00_religion.txt - run tools/faiths.py")
            continue
        have = religion_color(text, rel)
        if have != info["color"]:
            err.append(f"religion '{rel}': colour {have} is not CK3 {faith}'s {info['color']} - run tools/faiths.py")
        if lifted_name(loc, rel) != info["name"]:
            err.append(f"religion '{rel}': name {lifted_name(loc, rel)!r} is not CK3 {faith}'s {info['name']!r} - run tools/faiths.py")
        src = ck3_icon_file(faith)
        if _icon_matches(text, rel, _placeholder_icon(rel)):
            placeholder.append(rel)  # still the generated stand-in frame
        elif src is None:
            unverified.append(rel)
        elif not _icon_matches(text, rel, src):
            placeholder.append(rel)
    seen = {}
    for rel in used:
        sp = block_span(text, rel)
        m = re.search(r"(?m)^\t\ticon\s*=\s*(\d+)", text[sp[0]:sp[1]]) if sp else None
        if m:
            seen.setdefault(int(m.group(1)), []).append(rel)
    for n, rels in sorted(seen.items()):
        if len(rels) > 1:
            err.append(f"religions {', '.join(rels)} share icon frame {n} - each lifted faith needs its own frame")
    if placeholder:
        warn.append("religion icons that are placeholders or not CK3's yet (run tools/faiths.py icons locally): " + ", ".join(placeholder))
    if unverified:
        warn.append("religion icons not checked against CK3 (CK3 icon files not on this machine): " + ", ".join(unverified))
    return err, warn


def _icon_matches(text, rel, src):
    import addreligion

    sp = block_span(text, rel)
    icon = re.search(r"(?m)^\t\ticon\s*=\s*(\d+)", text[sp[0]:sp[1]])
    return bool(icon) and addreligion.frame_matches(src, int(icon.group(1)))


if __name__ == "__main__":
    if sys.argv[1:2] == ["icons"]:
        lift_icons()
    else:
        lift()
