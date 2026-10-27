#!/usr/bin/env python3
"""common/religions/00_religion.txt and its localisation and interface sprites: CK3's faiths.

A religion here IS a CK3 faith, under CK3's own key (`christian_faith`, `sunni`, `norse_pagan`). There
is no table between the two games. The file holds one religion per faith a province or tag of
tags.db names, in the group CK3's religion family gives it (faiths.expected_group). EU4 needs
mechanics a faith does not carry (modifiers, conversion rules, the papacy), so each religion is a
copy of a base-game religion block (TEMPLATE) rekeyed to the faith, with the line edits of EDITS
for the few that differ from the block they copy. The faith's colour and name come from CK3; the
icon frames are numbered in ICON_ORDER after the base game's. The base game's own religion blocks
are only ever copied from, never left in the file. Written whenever it differs, before anything
reads it.

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

# faith -> the base-game religion whose block it copies
TEMPLATE = {
    "christian_faith": "catholic",
    "armenian_apostolic": "coptic",
    "miaphysitism": "coptic",
    "nestorian": "coptic",
    "bosnian_church": "animism",
    "sunni": "sunni",
    "shia": "shiite",
    "kharijite": "ibadi",
    "mahayana_faith": "mahayana",
    "theravada_faith": "buddhism",
    "vajrayana_faith": "vajrayana",
    "confucian_faith": "confucianism",
    "shaiva_faith": "hinduism",
    "vaishnava_faith": "hinduism",
    "mazdayasna": "zoroastrian",
    "khurmazta": "zoroastrian",
    "norse_pagan": "norse_pagan_reformed",
    "tengri_pagan": "tengri_pagan_reformed",
    "slavic_pagan": "dreamtime",
    "baltic_pagan": "dreamtime",
    "finnish_pagan": "dreamtime",
    "magyar_pagan": "dreamtime",
    "north_african_acham_pagan": "animism",
    "shinto_faith": "shinto",
    "utaki": "animism",
    "kamuyism_pagan": "animism",
    "hantuism": "animism",
    "shamanism": "shamanism",
    "shangqing_faith": "confucianism",
    "zhengyi": "confucianism",
    "maitreya_faith": "confucianism",
    "manichaean_faith": "zoroastrian",
    "moism": "animism",
    "dab_qhuas": "animism",
    "haymanot": "jewish",
    "waaqism_pagan": "animism",
    "kushitism_pagan": "animism",
    "kabarism": "jewish",
    "rabbinic_faith": "jewish",
    "siberian_pagan": "animism",
    "bon_faith": "animism",
    "kiratism": "animism",
    "bimoism": "animism",
    "satsana_phi": "animism",
    "jain_faith": "hinduism",
    "shakta_faith": "hinduism",
    "smartism": "hinduism",
    "sedism": "animism",
    "melieism": "animism",
    "rrmeaism": "animism",
    "bilikuism": "animism",
    "kaharingan": "animism",
    "tolotang": "animism",
    "aluk": "animism",
    "dayawism": "animism",
    "west_african_roog_pagan": "animism",
    "west_african_pagan": "animism",
    "akom_pagan": "animism",
    "west_african_bidu_pagan": "animism",
    "west_african_orisha_pagan": "animism",
    "west_african_bori_pagan": "animism",
    "ngaiism_pagan": "animism",
    "mu": "animism",
    "mazdakism": "zoroastrian",
    "khurramism": "zoroastrian",
    "afridunism": "zoroastrian",
    "zun_pagan": "animism",
}

# line edits (old text, new text) on the copied block, for faiths whose rules differ from it
EDITS = {
    "nestorian": (
        ("\t\t\tdefensiveness = 0.15\n\t\t\ttolerance_own = 1\n",
         "\t\t\ttolerance_heathen = 1\n\t\t\tglobal_trade_power = 0.05\n"),
        ("\t\t\tsiege_ability = 0.1\n\t\t\tdefensiveness = 0.1\n",
         "\t\t\tglobal_trade_power = 0.05\n"),
        ("\t\t\torthodox\n",
         "\t\t\torthodox\n\t\t\tcatholic\n"),
        ("heretic = { ZAMIKAELITES STEPHANITES EUSTATHIANS }",
         "heretic = { MESSALIANS }"),
        ("holy_sites = { 358 1227 2313 1234 419 }",
         "holy_sites = { 379 410 2313 537 2218 }"),
    ),
    "bosnian_church": (
        ("\t\t\tglobal_unrest = -1\n",
         ""),
        ("\t\t\ttolerance_own = 2\n\t\t\tloot_amount = 0.25\n",
         "\t\t\tmerc_maintenance_modifier = -0.1\n\t\t\tgalley_power = 0.2\n"),
        ("\t\t\n\t\theretic = { SNAKE_CLAN }\n",
         ""),
    ),
    "slavic_pagan": (
        ("\t\t\tshock_damage_received = -0.05\n\t\t\tdiplomatic_reputation = 1\n",
         "\t\t\tland_forcelimit_modifier = 0.10\n"),
        ("\t\t\tshock_damage = 0.1\n\t\t\thostile_attrition = 2\n",
         "\t\t\tmerc_maintenance_modifier = -0.1\n\t\t\tgalley_power = 0.2\n"),
        ("\t\t\n\t\tfetishist_cult = yes\n\t\theretic = { WAGYLKOOP MOORAMOORA GINGARRURNDE }\n",
         "\t\tprovince = {\n\t\t\tlocal_missionary_strength = 0.02\n\t\t}\n"),
    ),
    "baltic_pagan": (
        ("\t\t\tshock_damage_received = -0.05\n\t\t\tdiplomatic_reputation = 1\n",
         "\t\t\tdefensiveness = 0.15\n"),
        ("\t\t\tshock_damage = 0.1\n\t\t\thostile_attrition = 2\n",
         "\t\t\tmerc_maintenance_modifier = -0.1\n\t\t\tgalley_power = 0.2\n"),
        ("\t\t\n\t\tfetishist_cult = yes\n\t\theretic = { WAGYLKOOP MOORAMOORA GINGARRURNDE }\n",
         "\t\tprovince = {\n\t\t\tlocal_missionary_strength = 0.02\n\t\t}\n"),
    ),
    "finnish_pagan": (
        ("\t\t\tshock_damage_received = -0.05\n\t\t\tdiplomatic_reputation = 1\n",
         "\t\t\thostile_attrition = 1\n"),
        ("\t\t\tshock_damage = 0.1\n\t\t\thostile_attrition = 2\n",
         "\t\t\tmerc_maintenance_modifier = -0.1\n\t\t\tgalley_power = 0.2\n"),
        ("\t\t\n\t\tfetishist_cult = yes\n\t\theretic = { WAGYLKOOP MOORAMOORA GINGARRURNDE }\n",
         "\t\tprovince = {\n\t\t\tlocal_missionary_strength = 0.02\n\t\t}\n"),
    ),
    "magyar_pagan": (
        ("\t\t\tshock_damage_received = -0.05\n\t\t\tdiplomatic_reputation = 1\n",
         "\t\t\tcavalry_power = 0.10\n"),
        ("\t\t\tshock_damage = 0.1\n\t\t\thostile_attrition = 2\n",
         "\t\t\tmerc_maintenance_modifier = -0.1\n\t\t\tgalley_power = 0.2\n"),
        ("\t\t\n\t\tfetishist_cult = yes\n\t\theretic = { WAGYLKOOP MOORAMOORA GINGARRURNDE }\n",
         "\t\tprovince = {\n\t\t\tlocal_missionary_strength = 0.02\n\t\t}\n"),
    ),
}

# the base game's religion each faith's template stands for, so references to it inside copied blocks
# (`change_religion = catholic`, conversion lists) point at the faith; others are dropped
VANILLA_FAITH = {
    "catholic": "christian_faith",
    "coptic": "miaphysitism",
    "sunni": "sunni",
    "shiite": "shia",
    "ibadi": "kharijite",
    "mahayana": "mahayana_faith",
    "buddhism": "theravada_faith",
    "vajrayana": "vajrayana_faith",
    "confucianism": "confucian_faith",
    "zoroastrian": "mazdayasna",
    "norse_pagan_reformed": "norse_pagan",
    "tengri_pagan_reformed": "tengri_pagan",
    "shinto": "shinto_faith",
    "shamanism": "shamanism",
    "jewish": "rabbinic_faith"
}

# our descriptions of the faiths; any other faith reads "The <name> faith."
DESC = {
    "armenian_apostolic":
        "The Armenian Apostolic Church of Etchmiadzin, Miaphysite out of Chalcedon like the Copts, and no part of their communion.",
    "nestorian":
        "The Church of the East, severed from the communion of the empire since Ephesus, kept by the Patriarch of Baghdad and carried east along the Silk Road by merchant missionaries.",
    "bosnian_church":
        "Long forgotten by Catholic and Orthodox alike, the Krstjani of the Bosnian highlands are more permissive than their better-known compatriots, but lack formal structure.",
    "shaiva_faith":
        "The worship of Shiva, Lord of Yogis and of destruction and renewal, with its ascetics and temples across the subcontinent.",
    "vaishnava_faith":
        "The worship of Vishnu and his avatars, carried by temple and pilgrimage across the subcontinent.",
    "khurmazta":
        "The old royal Zoroastrianism of Khwarezm: to Khurmazt, lord of the fire altars of Khiva and Gurganj, worshipped by the Afrigids and their people.",
    "slavic_pagan":
        "The faith of Perun and Veles, of the old gods worshipped in groves and on hilltops.",
    "baltic_pagan":
        "The old Baltic faith of Dievas, Perkunas and Gabija, kept beneath the sacred oaks.",
    "finnish_pagan":
        "The old Finnish faith of Ukko, Tapio and the spirits of forest and water.",
    "magyar_pagan":
        "The old Magyar faith of the táltos, seers who ride between sky and steppe.",
    "north_african_acham_pagan":
        "The old faith of the Berber and Guanche peoples of the Maghreb and the Atlantic islands, with its holy places and ancestral customs.",
    "utaki":
        "The faith of the Ryukyu islands and southern Kyushu, with its sacred groves, the utaki, where the noro priestesses commune with the kami.",
    "kamuyism_pagan":
        "The faith of the Ainu and the peoples of Hokkaido and Sakhalin, who honour the kamuy, the spirits dwelling in animals, mountains and tools.",
    "hantuism":
        "The faith of the Austronesian peoples of Taiwan, where the hantu, the ancestral spirits, watch over the village and the hunt.",
    "shangqing_faith":
        "The Highest Clarity tradition of the Daoists, with its revelations of the immortals and the scripture of the Mao Mountain.",
    "zhengyi":
        "The Way of Orthodox Unity, descended from the Celestial Masters, whose priests heal the sick and keep the registers of the spirits.",
    "maitreya_faith":
        "The hope of the coming Buddha Maitreya, kept by the lay societies of the Chinese plains.",
    "manichaean_faith":
        "The dualist faith of Mani, spread along the Silk Road and kept in the Uyghur lands and the ports of the south.",
    "moism":
        "The folk faith of the Zhuang and the peoples of the southern hills, led by its mo priests.",
    "dab_qhuas":
        "The faith of the Hmong and the hill peoples of the south, in which the dab, the spirits of house and hill, are honoured.",
    "haymanot":
        "The Judaism of the Beta Israel of the Ethiopian highlands, kept by their monks and smiths under the mountain kings.",
    "waaqism_pagan":
        "The faith of the Cushitic peoples of the Horn, who honour Waaq, the sky god, and hold their assemblies under the sacred trees.",
    "kushitism_pagan":
        "The ancient faith of the Kushite and Beja peoples of the Nile and the Red Sea hills, whose holy places lie at Aswan and Naqis.",
    "kabarism":
        "The Judaism of the Khazar khagans and their court at Itil, carried along the steppe roads by Radhanite merchants.",
    "siberian_pagan":
        "The shamanism of the Komi, Khanty and the peoples of the northern forests, who honour the spirits of the river, the bear and the sacred groves of the Urals.",
    "bon_faith":
        "The old religion of Tibet, older than the Buddha's teaching, whose priests make offerings to the mountain gods and the spirits of the high plateau.",
    "kiratism":
        "The Mundhum of the Kirati peoples of the eastern Himalayan foothills, who honour their ancestors and the spirits of the hills and rivers.",
    "bimoism":
        "The faith of the Yi peoples of the south-western mountains, led by their bimo priests, keepers of the ancestral scriptures.",
    "satsana_phi":
        "The spirit faith of the Tai peoples, in which the phi, the spirits of house, field and village, are placated by the elders.",
    "jain_faith":
        "The path of the Tirthankaras and of ahimsa, kept by monks and lay merchants in the cities and courts of western and southern India.",
    "shakta_faith":
        "The worship of the Goddess in her many forms, with its temples and its tantric masters across Bengal, Kashmir and the south.",
    "smartism":
        "The tradition of the smriti and of Advaita, which honours five deities as aspects of one and is kept by learned Brahmins.",
    "sedism":
        "The faith of the Meitei of Manipur, who honour Sanamahi and the lai, the spirits of the land, at the lairembi shrines.",
    "melieism":
        "The ancestral faith of the Qiangic and Tangut peoples of the north-western marches, whose shamans read the stars and keep the rites of their forefathers.",
    "rrmeaism":
        "The mountain faith of the Qiang of the upper Min valley, a religion of the sacred peaks and the white stones kept by their priests.",
    "bilikuism":
        "The faith of the Nias and Mentawai islanders and the peoples of the Andamans, who keep the ancestral megalithic cults of their villages.",
    "kaharingan":
        "The faith of the Dayak peoples of Borneo, who honour Ranying and the spirits of river and forest, and keep the secondary funeral of the tiwah.",
    "tolotang":
        "The faith of the Bugis and Makassar peoples and the peoples of eastern Indonesia, who revere Dewata Seuwae and the bissu priests.",
    "aluk":
        "The Aluk To Dolo of the Toraja highlands, whose ancestral cult, funeral feasts and tongkonan houses bind the living to the dead.",
    "dayawism":
        "The faith of the peoples of the Philippines, who honour the anito, the spirits of ancestors and nature, through the babaylan and the datu.",
    "west_african_roog_pagan":
        "The faith of the Serer, who honour Roog Sene, the creator, and keep the pangool, the ancestral spirits of the saltane priests.",
    "west_african_pagan":
        "The faith of the Mande peoples, whose smiths and hunters keep the komo and the boli, the powers of the earth and the ancestors.",
    "akom_pagan":
        "The Akom of the Akan, in which the okomfo priests commune with the abosom, the lesser gods, under the high god Nyame.",
    "west_african_bidu_pagan":
        "The faith of the Soninke and the peoples of the old Wagadu, who keep the cult of Bida, the serpent of the well, for the rains and the gold.",
    "west_african_orisha_pagan":
        "The faith of the Yoruba, Edo and Fon, who honour Olodumare and the orisa, the divine powers whose shrines and festivals order the life of the towns.",
    "west_african_bori_pagan":
        "The Bori of the Hausa and the peoples of the central Sudan, the possession cult of the iskoki, the spirits that ride their devotees.",
    "ngaiism_pagan":
        "The faith of the Kikuyu, Maasai and the peoples of the Kenyan highlands, who pray to Ngai on the slopes of Kirinyaga, the mountain of brightness.",
    "mu":
        "The shamanic faith of Jeju and the Korean peninsula, in which the mudang, the shamans, honour the spirits of mountain, sea and ancestors through the gut.",
    "mazdakism":
        "The communal creed of Mazdak, who preached the sharing of goods and was put down by Khosrow; his followers still hide in the hills of Khuzestan.",
    "khurramism":
        "The Khurramites, the joyous, heirs of Mazdak and of Babak, a faith of the hill peoples of Azerbaijan, Gilan and Khorasan who rose against the caliphs.",
    "afridunism":
        "The folk religion of the Daylamites and the Caspian shore, which honours the hero Afridun and keeps the old Iranian customs of the forest and the hills.",
    "zun_pagan":
        "The sun faith of the Zun, the god-kings of Zabulistan and Sistan, whose temple at Zamindawar and whose idol drew pilgrims from all India.",
}

# the faiths that take a frame of their own on the icon strips after the base game's (the others keep
# the frame their template has)
ICON_ORDER = (
    "baltic_pagan",
    "finnish_pagan",
    "slavic_pagan",
    "bosnian_church",
    "magyar_pagan",
    "armenian_apostolic",
    "miaphysitism",
    "nestorian",
    "khurmazta",
    "shaiva_faith",
    "vaishnava_faith",
    "north_african_acham_pagan",
    "utaki",
    "kamuyism_pagan",
    "hantuism",
    "shangqing_faith",
    "zhengyi",
    "maitreya_faith",
    "manichaean_faith",
    "moism",
    "dab_qhuas",
    "haymanot",
    "waaqism_pagan",
    "kushitism_pagan",
    "kabarism",
    "siberian_pagan",
    "bon_faith",
    "kiratism",
    "bimoism",
    "satsana_phi",
    "jain_faith",
    "shakta_faith",
    "smartism",
    "sedism",
    "melieism",
    "rrmeaism",
    "bilikuism",
    "kaharingan",
    "tolotang",
    "aluk",
    "dayawism",
    "west_african_roog_pagan",
    "west_african_pagan",
    "akom_pagan",
    "west_african_bidu_pagan",
    "west_african_orisha_pagan",
    "west_african_bori_pagan",
    "ngaiism_pagan",
    "mu",
    "mazdakism",
    "khurramism",
    "afridunism",
    "zun_pagan",
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


def _code(line):
    return line.split("#", 1)[0]


def split_items(lines):
    """A block body -> [(name, kind, [raw lines])]; comments and blank lines ride with the item
    after them. kind: 'block' (name = { ... }), 'line' or 'tail'."""
    out, pend, depth, cur = [], [], 0, None
    for ln in lines:
        c = _code(ln)
        if depth == 0 and cur is None:
            m = re.match(r"^\s*([A-Za-z0-9_]+)\s*=\s*(\{?)", c)
            if m:
                depth = c.count("{") - c.count("}")
                cur = [m.group(1), "block" if m.group(2) else "line", pend + [ln]]
                pend = []
                if depth <= 0:
                    out.append(tuple(cur))
                    cur, depth = None, 0
                continue
            pend.append(ln)
            continue
        cur[2].append(ln)
        depth += c.count("{") - c.count("}")
        if depth <= 0:
            out.append(tuple(cur))
            cur, depth = None, 0
    if pend:
        out.append((None, "tail", pend))
    return out


def parse_groups(text):
    lines = text.split("\n")
    pre, groups, i = [], [], 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*\{", _code(lines[i]))
        if not m:
            pre.append(lines[i])
            i += 1
            continue
        depth, j, body = _code(lines[i]).count("{") - _code(lines[i]).count("}"), i + 1, []
        while depth > 0:
            depth += _code(lines[j]).count("{") - _code(lines[j]).count("}")
            body.append(lines[j])
            j += 1
        closing = body.pop()
        groups.append([m.group(1), lines[i], split_items(body), closing])
        i = j
    return pre, groups


NOT_RELIGIONS = ("flag_emblem_index_range", "religious_schools")


def block_range(text, key):
    return re.search(r"(?m)^\t%s = \{.*?^\t\}(?=\n)" % re.escape(key), text, re.S)


def _set_line(block, name, value):
    new, n = re.subn(r"(?m)^(\t\t%s\s*=\s*).*$" % re.escape(name), lambda x: x.group(1) + value, block, count=1)
    if not n:
        raise SystemExit(f"religions: block has no {name} line")
    return new


def rekey(block, template, faith, vanilla_keys, to_faith):
    """The template's block as the faith's: header and self references use the faith's key; a reference to
    another base-game religion becomes that religion's faith when the file has it, else is dropped."""
    block = re.sub(r"^\t%s = \{" % re.escape(template), "\t%s = {" % faith, block, count=1)
    head, rest = block.split("\n", 1)
    out = []
    for ln in rest.split("\n"):
        code, sep, comment = ln.partition("#")
        drop = False
        for k in vanilla_keys:
            pat = r"\b%s\b" % re.escape(k)
            if not re.search(pat, code):
                continue
            new = faith if k == template else to_faith.get(k)
            if new:
                code = re.sub(pat, new, code)
            elif re.fullmatch(r"\s*%s\s*" % re.escape(k), code) or re.search(r"=\s*%s\b" % re.escape(k), code):
                drop = True  # a bare list entry, or a command or condition on the religion
                break
            else:
                code = re.sub(r"\s*" + pat, "", code)
        if not drop:
            out.append(code + (sep + comment if sep else ""))
    return head + "\n" + "\n".join(out)


def used_faiths():
    import sqlite3

    con = sqlite3.connect(os.path.join(HERE, "tags.db"))
    used = set()
    for q in ("select religion from provinces", "select religion from tags"):
        for (r,) in con.execute(q):
            if r:
                used.add(r)
    con.close()
    return used


def vanilla_frames():
    """Frames of the religion strip in the base game (what ICON_ORDER continues)."""
    t = _read(os.path.join(VANILLA_INTERFACE, "countryview.gfx"))
    m = re.search(r'name = "GFX_icon_religion"[^{}]*?noOfFrames\s*=\s*(\d+)', t)
    return int(m.group(1))


def religion_text():
    import faiths

    used = sorted(used_faiths())
    missing = [f for f in used if f not in TEMPLATE]
    if missing:
        raise SystemExit(f"religions: no TEMPLATE for faith(s) {missing} (tools/religions.py)")
    pre, groups = parse_groups(_read(VANILLA))
    templates = {}
    vanilla_keys = []
    for _g, _h, items, _c in groups:
        for name, kind, lines in items:
            if kind == "block" and name not in NOT_RELIGIONS:
                templates[name] = "\n".join(lines)
                vanilla_keys.append(name)
    to_faith = {v: f for v, f in VANILLA_FAITH.items() if f in used}
    base = vanilla_frames()
    icon = {f: base + i for i, f in enumerate(ICON_ORDER, 1)}
    by_group = {}
    for f in used:
        info = faiths.ck3_faith(f)
        t = TEMPLATE[f]
        src = templates[t]
        # a template stands out from the blank lines before it
        src = src.lstrip("\n")
        if not src.startswith("\t"):
            src = "\t" + src.lstrip()
        for old, new in EDITS.get(f, ()):
            if old not in src:
                raise SystemExit(f"religions: edit for {f} does not apply: {old!r}")
            src = src.replace(old, new, 1)
        blk = rekey(src, t, f, vanilla_keys, to_faith)
        if info and info["color"]:
            blk = _set_line(blk, "color", "{ %d %d %d }" % info["color"])
        if f in icon:
            blk = _set_line(blk, "icon", str(icon[f]))
        g = faiths.expected_group(f)
        if g is None:
            raise SystemExit(f"religions: CK3 files {f} under no religion")
        by_group.setdefault(g, []).append(blk)
    out = list(pre)
    for name, head, items, closing in groups:
        out.append(head)
        for iname, kind, lines in items:
            if kind == "block" and iname not in NOT_RELIGIONS:
                continue
            if kind == "tail":
                continue
            out += lines
        for blk in by_group.pop(name, []):
            out += ["", blk]
        out += [closing, ""]
    if by_group:
        raise SystemExit(f"religions: faiths in unknown groups {sorted(by_group)}")
    import rites

    return rites.patch_text("\n".join(out).rstrip("\n") + "\n")


def religion_loc(text):
    import faiths

    lines = ["l_english:"]
    for f in sorted(used_faiths()):
        info = faiths.ck3_faith(f)
        if not info or not info["name"]:
            continue
        lines.append(f' {f}:0 "{info["name"]}"')
        lines.append(f' {f}_desc:0 "{DESC.get(f) or "The " + info["name"] + " faith."}"')
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
        if not os.environ.get("KAR_NO_ENSURE"):  # set while tags.db is being migrated
            write()


if __name__ == "__main__":
    check = "--check" in sys.argv
    stale = write(check)
    for p in stale:
        print(("stale: " if check else "wrote ") + os.path.relpath(p, MOD))
    sys.exit(1 if (check and stale) else 0)
