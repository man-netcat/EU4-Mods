#!/usr/bin/env python3
"""Ruler-culture pipeline: every tag takes its 867 holder's CK3 culture.

Maps the holder culture to our EU4 key (CK3_TO_EU4) and lifts the culture
(entry + CK3 names + loc + DB row, Pictish precedent) when we don't have
the key yet (tools/cultures.py writes the cultures file from the base game and
CK3; a new key needs a LIFTS entry there); anything else resolves to None and the caller
falls back to the vanilla province culture.
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ck3  # noqa: E402
import db  # noqa: E402
from models import Culture as CultureRow  # noqa: E402

CULT_FILE = os.path.join(HERE, "..", "common", "cultures", "00_cultures.txt")

CK3_TO_EU4 = {
    # CK3 867 county/holder culture -> our EU4 key. Every value must exist
    # in common/cultures/00_cultures.txt (--selftest enforces this).
    # 867-fallbacks for cultures with no EU4 key are documented inline.
    "frankish": "frankish", "occitan": "occitain", "catalan": "catalan",
    "aragonese": "aragonese", "castilian": "castillian", "leonese": "leonese",
    "galician": "galician", "portuguese": "castillian",
    "andalusian": "andalusian", "levantine": "levantine",
    "egyptian": "al_misr_arabic",
    "basque": "basque", "breton": "breton", "welsh": "welsh",
    "cornish": "cornish", "irish": "irish", "gaelic": "irish",
    "pictish": "pictish", "cumbrian": "cumbrian", "scottish": "scottish",
    "anglo_saxon": "anglosaxon", "saxon": "saxon", "dutch": "dutch",
    "frisian": "dutch", "bavarian": "bavarian", "swabian": "swabian",
    "franconian": "franconian", "french": "frankish",
    "lombard": "lombard", "italian": "italian", "cisalpine": "cisalpine",
    "roman": "roman",
    "venetian": "venetian", "sardinian": "sardinian",
    "sicilian": "sicilian", "umbrian": "umbrian", "neapolitan": "neapolitan",
    "greek": "greek", "armenian": "armenian", "georgian": "georgian",
    "alan": "circassian", "gothic": "goths",
    "swedish": "swedish", "norwegian": "norwegian", "danish": "danish",
    "norse": "norse", "icelandic": "norse",
    "finnish": "finnish", "karelian": "karelian", "estonian": "estonian",
    "livonian": "livonian", "latgallian": "latvian", "latvian": "latvian",
    "lithuanian": "lithuanian", "samogitian": "lithuanian",
    "prussian": "prussian", "pommeranian": "pommeranian",
    "sami": "sapmi", "samoyed": "samoyed",
    "polish": "polish", "polabian": "polabian", "czech": "czech",
    "slovak": "slovak", "slovien": "slovien", "carantanian": "carantanian",
    "croatian": "croatian", "serbian": "serbian", "bulgarian": "bulgarian",
    "bolghar": "bulgarian", "bosnian": "bosnian", "dalmatian": "dalmatian",
    "romanian": "romanian", "vlach": "romanian",
    "rus": "russian", "russian": "russian", "novgorodian": "novgorodian",
    "ryazanian": "ryazanian", "severian": "ryazanian",
    "magyar": "magyar", "hungarian": "magyar", "avar": "avar",
    "khazar": "bulgarian", "pecheneg": "pecheneg", "cuman": "khazak",
    "kipchak": "khazak", "kimek": "khazak", "oghuz": "turkmeni",
    "karluk": "uzbehk", "sogdian": "uzbehk", "tocharian": "uyghur",
    "saka": "uyghur", "khwarezmian": "khwarezmian", "tajik": "persian",
    "tibetan": "tibetan", "bodpa": "tibetan", "tsangpa": "tibetan",
    "sumpa": "tibetan", "laktan": "tibetan", "zhangzhung": "tibetan",
    "tuyuhun": "tibetan",
    "turkish": "turkmeni", "turkmeni": "turkmeni",
    "azeri": "azerbaijani", "kurdish": "kurdish",
    "persian": "persian", "baloch": "baluchi", "daylamite": "mazandarani",
    "bedouin": "bedouin_arabic",
    "syrian": "levantine",
    "maghrebi": "maghrebi", "berber": "berber", "baranis": "baranis", "butr": "butr",
    "guanches": "guanche", "tuareg": "tuareg",
    "coptic": "al_misr_arabic", "nubian": "nubian", "beja": "beja",
    "somali": "somali", "afar": "afar", "oromo": "oromo",
    "gala": "oromo", "ethiopian": "amhara",
    "swahili": "swahili", "east_bantu": "swahili", "bantu": "swahili",
    "malagasy": "madagascan",
    "manden": "mali", "malinke": "mali", "mel": "mali", "bambara": "bambara",
    "marka": "bambara", "bozo": "bambara", "bobo": "bambara",
    "songhai": "songhai", "sorko": "songhai", "sao": "kanuri",
    "mossi": "mossi", "gur": "mossi", "daju": "tunjur", "zaghawa": "tunjur",
    "hausa": "hausa", "kanuri": "kanuri", "fulani": "fulani",
    "pulaar": "fulani", "wolof": "fulani", "dyola": "fulani",
    "guan": "fon", "fon": "fon", "ewe": "fon", "akan": "fon", "kru": "fon",
    "yoruba": "yorumba", "nupe": "yorumba", "edo": "yorumba",
    "igbo": "yorumba", "jukun": "jukun",
    "chinese": "wu", "min": "hakka", "wu": "wu", "yue": "cantonese",
    "gan": "gan", "xiang": "xiang", "jin": "jin",
    "korean": "korean", "balhae": "korean", "silla": "korean",
    "khitan": "khitan", "jurchen": "manchu", "mongol": "mongol",
    "buryat": "buryat", "oirat": "oirats", "naiman": "naiman",
    "kerait": "kerait", "kirghiz": "kirgiz", "khalkha": "mongol",
    "uriankhai": "mongol", "tatar": "siberian",
    "uyghur": "uyghur", "tangut": "tibetan",
    "tibetan_group": "tibetan",
    "viet": "vietnamese", "vietnamese": "vietnamese", "khmer": "khmer", "lao": "lao",
    "thai": "central_thai", "burmese": "burmese", "mon": "mon",
    "shan": "shan", "kachin": "kachin", "chin": "chin", "karen": "karen",
    "arakanese": "arakanese", "pyu": "burmese",
    "malay": "malayan", "senoi": "malayan", "nakkavaram": "malayan",
    "javanese": "javanese", "sundanese": "sundanese",
    "tagalog": "filipino", "cham": "cham",
    "papuan": "papuan", "melanesian": "melanesian",
    "polynesian": "polynesian", "aboriginal": "aboriginal",
    "hebrew": "hebrew", "radhanite": "hebrew", "aramaic": "aramaic",
    "assyrian": "aramaic", "syriac": "aramaic",
    "coptic_egyptian": "al_misr_arabic",
    "armenian_chalcedonian": "armenian",
    "samaritan": "hebrew", "jewish": "hebrew",
    "sindhi": "sindhi", "panjabi": "panjabi", "punjabi": "panjabi",
    "gujarati": "gujarati", "marathi": "marathi", "kannada": "kannada",
    "telegu": "telegu", "telugu": "telegu", "malayalam": "malayalam",
    "oriya": "oriya", "sinhala": "sinhala", "tamil": "tamil",
    "rajput": "rajput", "malvi": "malvi", "gondi": "gondi", "gond": "gondi",
    "kashmiri": "kashmiri", "nepali": "nepali", "kirati": "nepali",
    "assamese": "assamese", "bihari": "bihari", "avadhi": "avadhi",
    "kanauji": "kanauji", "hindustani": "kanauji",
    "bhil": "gondi", "korku": "gondi", "kharia": "gondi",
    "santal": "gondi", "munda": "gondi",
    "nuristani": "khorasani", "kati": "khorasani", "kamkata": "khorasani",
    "dardic": "kashmiri", "shina": "kashmiri", "kohistani": "kashmiri",
    "balti": "tibetan", "burusho": "tibetan",
    "nuristani_kati": "khorasani",
    "wakhi": "khorasani", "shughni": "khorasani", "yazghulami": "khorasani",
    "ishkashimi": "khorasani", "yidgha": "khorasani", "munji": "khorasani",
    "parachi": "khorasani", "ormuri": "khorasani",
    "sanglechi": "khorasani",
    "brahui": "baluchi", "makrani": "baluchi",
    "han": "zhongyuan",
    "sistani": "persian", "fars": "persian", "kermani": "persian",
    "yazdi": "persian", "larestani": "persian", "bandari": "persian",
    "khuzestani": "luri", "lori": "luri", "bakhtiari": "luri",
    "gilaki": "mazandarani", "talysh": "mazandarani",
    "tati": "mazandarani", "semnani": "mazandarani",
    "sorkhei": "mazandarani",
    "hazara": "khorasani", "aimaq": "khorasani", "firozkohi": "khorasani",
    "jamshidi": "khorasani", "taimuri": "khorasani", "timuri": "khorasani",
    "nuristani_ashkun": "khorasani", "prasuni": "khorasani",
    "waigali": "khorasani", "katarkala": "khorasani",
    "pashayi": "khorasani", "laghmani": "khorasani",
    "tregami": "khorasani", "savi": "khorasani",
    "gawar": "khorasani", "nishei": "khorasani",
    "shumashti": "khorasani", "grangali": "khorasani",
    # second-wave fills (encountered at county level)
    "acehnese": "acehnese", "afghan": "khorasani", "ainu": "ainu",
    "asturleonese": "castillian", "bashkir": "bashkir", "bengali": "bengali",
    "chuvash": "bulgarian", "emishi": "togoku", "japanese": "japanese", "ryukyuan": "ryukyuan", "amis": "amis",
    "khanty": "ostyaki", "komi": "komi", "latgalian": "latvian",
    "mari": "mari", "merya": "merya", "meshchera": "meshchera",
    "mogyer": "magyar", "mohe": "tungus", "mordvin": "mordvin",
    "muroma": "bulgarian", "nivkh": "nivkh", "shiwei": "mongol",
    "soninke": "soninke", "vepsian": "karelian", "welayta": "oromo",
    "yemeni": "yemeni_culture",
    # Maritime South-East Asia, the Tai and Hmong-Mien peoples, the Onggud: the base game's
    # nearest culture (EU4 has one culture for the Dayaks, one for the Moluccans, ...)
    "dayak": "bornean", "bugis": "sulawesi", "toraja": "sulawesi", "maluku": "moluccan",
    "bisayan": "filipino", "iloko": "filipino", "tai": "northern_thai", "khmu": "lao",
    "bouxcuengh": "zhuang", "hmong": "miao", "yi": "yi", "lhomon": "tibetan",
    "yughur": "uyghur", "ongud": "mongol",
}

_WALK_KEYS = ("father", "real_father", "mother")
_WALK_DEPTH = 3


def _body_value(body, key):
    """Value of a dated-aware character field as of 867.1.1: the latest
    dated change at or before 867.1.1 wins (Boris's birth Tengri vs his
    864 Greek-rite baptism); the undated head value is only the
    start-state fallback."""
    undated, best, depth, cur = None, None, 0, ""
    for ln in body.splitlines():
        s = ln.strip()
        if re.match(r"^\d+\.\d+\.\d+\s*=", s) and depth == 0:
            cur = s.split("=")[0].strip()
        code = ln.split("#", 1)[0]
        opens = code.count("{")
        m = re.match(r'^%s\s*=\s*"?([a-z_0-9]+)"?\s*$' % key, code.strip())
        if m:
            if depth == 0 and undated is None:
                undated = m.group(1)
            elif cur and cur <= "867.1.1":
                best = m.group(1)
        depth += opens - code.count("}")
        if depth <= 0:
            depth, cur = 0, ""
    return best if best is not None else undated


def _holder_with(title, key):
    """(holder id, value at 867) for a title's character field, walking
    up to three generations when the holder's own is unscripted."""
    titles = ck3.load_titles()
    chars = ck3.load_chars()
    holder = ck3.holder_at(title, titles)
    if not holder:
        return None, None
    seen = set()

    def walk(cid, d):
        if not cid or cid in seen or d > _WALK_DEPTH:
            return None
        seen.add(cid)
        body = chars.get(cid)
        if not body:
            return None
        got = _body_value(body, key)
        if got:
            return got
        for key_ in _WALK_KEYS:
            m = re.search(r"(?m)^\s*%s\s*=\s*([A-Za-z0-9_]+)" % key_, body)
            if m:
                got = walk(m.group(1), d + 1)
                if got:
                    return got
        return None

    return holder, walk(holder, 0)


def holder_culture(title):
    """(holder id, CK3 culture at 867) for a title's holder."""
    return _holder_with(title, "culture")


def holder_faith(title):
    """(holder id, CK3 faith at 867) - the character's `rite` entry."""
    return _holder_with(title, "rite")



def file_has(eu4key):
    import cultures
    cultures.ensure()
    try:
        text = open(CULT_FILE, encoding="cp1252", errors="replace").read()
    except FileNotFoundError:
        return False
    return bool(re.search(r"(?m)^[ \t]*%s = \{" % re.escape(eu4key), text))


def have_culture(eu4key):
    if eu4key is None or not file_has(eu4key):
        return False
    s = db.session()
    found = s.get(CultureRow, eu4key) is not None
    s.close()
    return found


def ensure_culture(ck3cult, session=None):
    """EU4 key for a CK3 culture: repair the DB row when the key exists,
    lift the whole culture when it doesn't (needs a tools/cultures.py LIFTS entry),
    else None so the caller falls back to the land culture. Pass the
    caller's session when one already holds the database: a second
    connection deadlocks against an uncommitted write (the addtag
    --take-then-lift crash)."""
    eu4key = CK3_TO_EU4.get(ck3cult) if ck3cult else None
    if eu4key is None:
        return None
    if not file_has(eu4key):
        print(f"  {ck3cult} -> {eu4key}: not in tools/cultures.py LIFTS, keeping land culture")
        return None
    s = session or db.session()
    s.merge(CultureRow(name=eu4key))
    if session is None:
        s.commit()
        s.close()
    return eu4key


def selftest():
    """Every mapped value must exist in our cultures file (direct check:
    substring key lists lie, e.g. catalan contains alan)."""
    text = open(CULT_FILE, encoding="cp1252", errors="replace").read()
    bad = sorted(
        {v for v in CK3_TO_EU4.values() if not re.search(r"(?m)^[ \t]*%s = \{" % v, text)}
    )
    if bad:
        print("UNDEFINED EU4 KEYS:", bad)
        return 1
    print(f"map OK ({len(set(CK3_TO_EU4.values()))} keys defined)")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())


# CK3 rite at 867 -> our EU4 religion key: through the CK3 faith the rite
# belongs to (rite_types), lifted by exactly one EU4 religion (see
# faiths.FAITH_RELIGION). No approximations: a tag never gets a religion that
# is a different CK3 faith than its ruler's.
from faiths import rite_religion_map  # noqa: E402

FAITH_TO_RELIGION = rite_religion_map()


def ruler_default(title, session=None):
    """EU4 culture for a new tag from its title's 867 holder (None to
    fall back to the vanilla province culture)."""
    holder, cc = holder_culture(title)
    if not cc:
        print(f"  no holder culture for {title}, keeping land culture")
        return None
    eu4key = ensure_culture(cc, session)
    if eu4key:
        print(f"  {title}: holder {holder} is {cc} -> {eu4key}")
    return eu4key


def ruler_religion(title):
    """EU4 religion for a new tag from its title's 867 holder's faith
    (None to fall back to the vanilla province religion)."""
    _holder, faith = holder_faith(title)
    if not faith:
        return None
    return FAITH_TO_RELIGION.get(faith)
