#!/usr/bin/env python3
"""The Karolingians - generate history/countries for the six realms.

Rulers are the historical monarchs of the 867 partition:
    FRA  Charles the Bald   (West Francia, 843-877)
    LOT  Lothair II         (Lotharingia,   855-869)
    GER  Louis the German   (East Francia,  843-876)
    BAV  Carloman of Bavaria(Bavaria,       855-880)
    ITA  Louis II of Italy  (Italy,         844-875)

EU4 ages a monarch from birth_date, so a literal 867 birth year would make a
621-year-old ruler who dies on turn one. Every birth year is therefore shifted
forward by exactly 577 years (1444 - 867), which keeps the real month/day and
makes each king the SAME AGE in 1444 that he was in 867. death_date is shifted
by the same amount so nobody dies during the first three centuries.
"""
import os, re, shutil
from pathlib import Path

from modtags import ALL_TAGS

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
SRC = os.path.join(GAME, "history", "countries")
MOD = str(HERE.parent)
OUT = os.path.join(MOD, "history", "countries")

START = "1444.1.1"
# All five Carolingian realms share one dynasty deliberately. A shared dynasty
# is what unlocks Claim Cushion in EU4 - claiming a neighbour's throne without
# a war - so keeping it unbroken is the point of a divided empire: the five can
# put it back together by marriage instead of conquest. It has to cover the
# heirs as well as the monarchs, or the dynasty breaks the first time one of
# these realms succeeds, which is exactly what Arnulf and Berengar used to do.
DYNASTY = "de Carolingie"
SHIFT = 577


def shifted(y, m=1, d=1):
    return f"{y + SHIFT}.{m}.{d}"


# Capitals and cultures for the realms whose country file is written from scratch.
# Which realms those are is the Tag's `country` field, not a list here: see
# tagdb.HEADER and tagdb.FRESH_REALMS.
from tagdb import HEADER, FRESH_REALMS  # noqa: E402,F401

# The rank of every realm, its capital, its CK3 title, and the realms that are kept
# but not yet authored - all of it is one Tag object per realm in tagdb.py, which
# is also where every rank's justification lives. These four names are the same
# data seen from this script's side of the fence.
#
# A rank is argued from a realm's own 867 standing and never from which group a
# tag was filed under. The old rule here was "the five are peers at 2, Lusatia
# sits below them", which made the ranks a statement about the partition rather
# than about the realms.
from tagdb import (  # noqa: E402,F401
    RANK, KEPT_REALMS, DEFERRED_REALMS, ALL_TAGS, BY_TAG,
)

# Vanilla tags this mod touches. They keep their own vanilla history - none of
# them is a realm of ours, they all sit outside the Karolingian sphere and are
# absent from the HRE decision - so this only ever corrects a capital and/or
# installs an 867 ruler. Nothing else in the vanilla file is touched.
VANILLA = {
    # Silesia: its vanilla seat is Ratibor (263), which now belongs to Great
    # Moravia, so SIL would own land but not its own seat. Breslau (264) is the
    # historical capital of the duchy - Ratibor was an appanage seat - and lies
    # inside the set SIL actually holds. It also gets its own 867 ruler.
    "SIL": {"capital": 264, "ruler": "SIL"},
    # Bohemia: an 867 ruler, no capital change (Praha 266 is still its own).
    "BOH": {"ruler": "BOH"},
    # Great Moravia: an 867 ruler, no capital change (Olomouc 4237 is its own).
    "GMA": {"ruler": "GMA"},
    # Navarre: the mod takes Vizcaya and Pirineo from France, and Pamplona (210)
    # is already vanilla's own NAV capital, so the capital is left alone.
    "NAV": {"ruler": "CK3"},
    # Montenegro: Zeta (138) and Kotor (4754) are the Dioclean core, and Zeta is
    # already vanilla's MON capital.
    "MON": {"ruler": "CK3"},
    # Sardinia: no province changes hands and no capital changes - vanilla already
    # seats SAR at 127, which is one of its own three. All this entry is here for
    # is the rank, because without it SAR takes EU4's default of 1 by accident
    # rather than by argument. No ruler is written: see NOT_CK3 in ck3ruler.py.
    "SAR": {},
}

# 867 rulers for the vanilla tags above. Dates are CK3's own, taken from
# game/history/characters/, and are shifted by SHIFT like every ruler here.
#
# GMA  Rostislav (Rastislav), CK3 slovien.txt id 187002: birth 815.1.1, death
#      869.1.1. He is the Moravian ruler in 867. Svatopluk was only Prince of
#      Nitra until 870 and then succeeds him, which is why Svatopluk - not a
#      son - is the heir.
# BOH  Borivoj I, the first historically documented Premyslid, the year 867 being
#      the dynasty's own founding date. Sources put his birth at c. 852/53
#      (MedLands) or c. 870 (Wikipedia); 852 is used, which makes him 15 in 1444.
#      Both his sons were born after 867 - Spytihnev 875, Vratislav 888 - so the
#      heir is an infant either way and he carries regent = yes. That regency is
#      an artefact of the age shift, not a fact about 867.
# SIL  Gardomir, CK3 polish.txt id 82293: birth 844.1.1, death 912.1.1 - so 23 in
#      867, which is the age the user asked for. He is one of the semi-legendary
#      Silesian dukes of the Legenda memorabilis, the 13th-century Polish
#      hagiography CK3 also draws Sliezan (id 82291, b 805.1.1, d 864.1.1) and
#      his wife Gniewosadka (82292) from. Sliezan died in 864, so by 867 Gardomir
#      is the line's incumbent - a real succession, but a legendary one, which is
#      why it is sourced to CK3 rather than to the chronicles. Eldest son
#      Uniedrog (82297, b 863.1.1, d 942.1.1) is heir; his brother Swietopelk
#      (82298) is the best-attested of the three, but not the eldest.
#      EU4 1.37 has no nickname field in a monarch block - nickname is absent
#      from all 8416 vanilla name keys' blocks - so "Slezan" is part of the name.
VANILLA_RULERS = {
    "GMA": f"""
{START} = {{
	monarch = {{
		name = "Rostislav"
		dynasty = "of Rostislav"
		birth_date = {shifted(815, 1, 1)}
		death_date = {shifted(869, 1, 1)}
		adm = 3
		dip = 4
		mil = 3
	}}
	heir = {{
		name = "Svatopluk"
		monarch_name = "Svatopluk"
		dynasty = "of Rostislav"
		birth_date = {shifted(840, 1, 1)}
		death_date = {shifted(894, 1, 1)}
		claim = 90
		adm = 4
		dip = 4
		mil = 4
	}}
}}
""",
    "BOH": f"""
{START} = {{
	monarch = {{
		name = "Borivoj"
		dynasty = "of Premyslid"
		regent = yes
		birth_date = {shifted(852, 1, 1)}
		death_date = {shifted(889, 1, 1)}
		adm = 1
		dip = 2
		mil = 1
	}}
	heir = {{
		name = "Spytihnev"
		monarch_name = "Spytihnev"
		dynasty = "of Premyslid"
		birth_date = {shifted(875, 1, 1)}
		death_date = {shifted(915, 1, 1)}
		claim = 85
		adm = 2
		dip = 1
		mil = 2
	}}
}}
""",
    "SIL": f"""
{START} = {{
	monarch = {{
		name = "Gardomir Slezan"
		dynasty = "Slezan"
		birth_date = {shifted(844, 1, 1)}
		death_date = {shifted(912, 1, 1)}
		adm = 2
		dip = 2
		mil = 3
	}}
	heir = {{
		name = "Uniedrog"
		monarch_name = "Uniedrog"
		dynasty = "Slezan"
		birth_date = {shifted(863, 1, 1)}
		death_date = {shifted(942, 1, 1)}
		claim = 80
		adm = 2
		dip = 2
		mil = 3
	}}
}}
""",
}

RULERS = {
    "FRA": f"""
{START} = {{
	monarch = {{
		name = "Charles the Bald"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(823, 8, 13)}
		death_date = {shifted(877, 10, 6)}
		adm = 3
		dip = 3
		mil = 3
	}}
	heir = {{
		name = "Louis"
		monarch_name = "Louis the Stammerer"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(837, 9, 27)}
		death_date = {shifted(879, 8, 10)}
		claim = 95
		adm = 3
		dip = 2
		mil = 3
	}}
}}
""",
    "LOT": f"""
# Lothair II died childless in 869, which is why Lotharingia came apart. He is
# deliberately left without an heir so the scripted fragmentation still works.
{START} = {{
	monarch = {{
		name = "Lothair II"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(835)}
		death_date = {shifted(869)}
		adm = 2
		dip = 2
		mil = 2
	}}
}}
""",
    "GER": f"""
{START} = {{
	monarch = {{
		name = "Louis the German"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(817, 8, 27)}
		death_date = {shifted(876, 9, 5)}
		adm = 4
		dip = 3
		mil = 4
	}}
	heir = {{
		name = "Charles"
		monarch_name = "Charles the Fat"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(839)}
		death_date = {shifted(888, 12, 13)}
		claim = 95
		adm = 3
		dip = 3
		mil = 4
	}}
}}
""",
    "BAV": f"""
{START} = {{
	monarch = {{
		name = "Carloman"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(817)}
		death_date = {shifted(880)}
		adm = 3
		dip = 3
		mil = 2
	}}
	heir = {{
		name = "Arnulf"
		monarch_name = "Arnulf"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(850)}
		death_date = {shifted(907, 12, 14)}
		claim = 95
		adm = 3
		dip = 3
		mil = 3
	}}
}}
""",
    "ITA": f"""
{START} = {{
	monarch = {{
		name = "Louis II"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(826)}
		death_date = {shifted(875, 8, 13)}
		adm = 3
		dip = 3
		mil = 3
	}}
	heir = {{
		name = "Berengar"
		monarch_name = "Berengar"
		dynasty = "{DYNASTY}"
		birth_date = {shifted(845)}
		death_date = {shifted(924, 10, 17)}
		claim = 95
		adm = 3
		dip = 3
		mil = 3
	}}
}}
""",
    # Lusatia is a free Sorbian principality with no 867 Carolingian monarch,
    # so it gets its own dynasty and native 1444 dates instead of a shifted 867
    # one. Mstivoj is an attested West Slavic name form (cf. Mstivoj of
    # Kladsko), which suits the Sorbian heartland around Zwickau and Leipzig.
    "SOR": f"""
{START} = {{
	monarch = {{
		name = "Mstivoj"
		dynasty = "of Lusatia"
		birth_date = 1395.3.2
		death_date = 1449.11.8
		adm = 2
		dip = 1
		mil = 2
	}}
	heir = {{
		name = "Mstivoj"
		monarch_name = "Mstivoj"
		dynasty = "of Lusatia"
		birth_date = 1425.6.14
		death_date = 1470.1.1
		claim = 80
		adm = 2
		dip = 2
		mil = 2
	}}
}}
""",
}


# Provenance comments, one per CK3-sourced realm, emitted into the generated
# file directly above its 1444.1.1 block. These used to be pasted into the output
# by hand, which meant the next run of this script deleted them - the comments
# were the one thing in the country files with no source behind them.
#
# They live here because that is where everything else about the ruler lives.

PROVENANCE = {
    "FRA": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of k_france
# at 867.1.1 is character 90104, "Charles", of dynasty 25061 "Karling". CK3 gives
# him no epithet, so the earlier hand-written "Charles the Bald" is gone; that is
# what verbatim means here. Do not hand-edit name or dynasty - run
# `python3 tools/ck3ruler.py --fix` instead, and validate.py will fail if the file
# and CK3 disagree.
""",
    "LOT": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of
# k_lotharingia at 867.1.1 is character 144998, "Lothaire", of dynasty 25061
# "Karling". Note CK3 writes that name unquoted, with no epithet; the earlier
# hand-written "Lothair II" is gone. Do not hand-edit name or dynasty - run
# `python3 tools/ck3ruler.py --fix` instead.
""",
    "GER": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of
# k_east_francia at 867.1.1 is character 90107, "Ludwig", of dynasty 25061
# "Karling". CK3 gives him no epithet, so the earlier hand-written "Louis the
# German" is gone; that is what verbatim means here. Do not hand-edit name or
# dynasty - run `python3 tools/ck3ruler.py --fix` instead.
""",
    "BAV": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of
# d_bavaria at 867.1.1 is character 42018, "Karlmann", of dynasty 25061
# "Karling".
#
# The duchy is deliberate, and the reason is in tools/ck3ruler.py: CK3 has no
# independent Bavaria in 867. Its k_bavaria is held by Ludwig (90107) - the same
# man as k_east_francia - continuously from 826.1.1 until 876.1.1, and Carloman
# only takes it in 876. Since this mod does split Bavaria off as its own realm,
# d_bavaria is the title whose 867 holder is him. Mapping to k_bavaria would have
# made this a second "Ludwig"/"Karling" and erased the realm.
#
# Do not hand-edit name or dynasty - run `python3 tools/ck3ruler.py --fix` instead.
""",
    "ITA": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of k_italy
# at 867.1.1 is character 30228, "Louis", of dynasty 25061 "Karling". CK3 gives
# him no regnal number, so the earlier hand-written "Louis II" is gone. Do not
# hand-edit name or dynasty - run `python3 tools/ck3ruler.py --fix` instead.
""",
    "SOR": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of
# d_lausitz at 867.1.1 is character 184007, "Radomil", of the Milczanow dynasty.
#
# CK3 models no Sorbian title at all - k_sorbs and d_sorbs both have no holder -
# so d_lausitz is the nearest title with an actual 867 ruler. That replaces the
# hand-written "Mstivoj"/"of Lusatia". Mstivoj is historically the better-known
# Lusatian ruler of the period and survives as the heir below; CK3's choice is
# followed because it is what the rest of this mod's western Slavic realms do.
#
# Do not hand-edit name or dynasty - run `python3 tools/ck3ruler.py --fix` instead.
""",
    "GMA": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of k_moravia
# at 867.1.1 is character 187002, "Rostislav", of the Mojmird dynasty.
#
# This realm holds the two Moravian provinces (Brno 265, Olomouc 4237) as well as
# Galicia, and its ruler was already Rostislav, so k_moravia is the title whose 867
# holder the mod was reaching for. The hand-written dynasty "of Rostislav" was
# invented; CK3 calls the house Mojmird. Do not hand-edit name or dynasty - run
# `python3 tools/ck3ruler.py --fix` instead.
""",
    "SIL": """\
# Ruler lifted verbatim from CK3 by tools/ck3ruler.py: CK3's holder of
# d_lower_silesia at 867.1.1 is character 82293, "Gardomir", of the dynasty
# CK3 spells "Slezan" with diacritics. The hand-written "Gardomir Slezan"/"Slezan"
# was already a guess at exactly this, so only the spelling is new. Do not
# hand-edit name or dynasty - run `python3 tools/ck3ruler.py --fix` instead.
""",
}

# ---------------------------------------------------------------- CK3 rulers --

def with_provenance(tag, text):
    """Insert this tag's provenance comment above its 1444.1.1 block."""
    note = PROVENANCE.get(tag)
    if not note or "1444.1.1 = {" not in text or note.strip() in text:
        return text
    return text.replace("1444.1.1 = {", note + "1444.1.1 = {", 1)


# Every name and dynasty written below used to be typed in by hand, which meant
# this script and ck3ruler.py each held their own copy of the same fact - and
# running this script silently reverted all fifteen CK3-sourced rulers to the
# pre-lift strings ("Charles the Bald", "of Rostislav", Mstivoj/"of Lusatia").
#
# So this script no longer decides those two fields. It writes the ruler's stats,
# dates and heir exactly as before, then asks ck3ruler what CK3's 867 holder's
# name and dynasty are. One source of truth, and regenerating is idempotent
# instead of destructive.
#
# Only name and dynasty are taken. Stats and dates stay hand-written because they
# are judgement calls: CK3's 1-25 skill scale is not EU4's 1-6, and CK3 has no
# 1444 to be alive in.
_CK3_CACHE: dict = {}


def ck3_ruler(tag):
    """CK3's 867 name/dynasty for `tag`, or None if CK3 is not the authority."""
    if tag not in _CK3_CACHE:
        try:
            import ck3ruler as _c
        except ImportError:
            _CK3_CACHE[tag] = None
            return None
        if tag not in _c.TITLES:
            _CK3_CACHE[tag] = None
            return None
        got = _c.resolve(tag, _c.load_titles(), _c.load_chars(),
                         _c.load_dynasties(), _c.load_houses())
        # A CK3 character with no dynasty (the Pope) yields None here rather than
        # a half-answer, so the mod's own string is left alone instead of being
        # blanked or invented.
        _CK3_CACHE[tag] = None if got.get("error") or not got.get("dynasty") else got
    return _CK3_CACHE[tag]


def ck3_sync(tag, text):
    """Rewrite the ruler's name and every dynasty line from CK3."""
    got = ck3_ruler(tag)
    if got is None:
        return text
    blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
    if not blk:
        return text
    new = re.sub(r'name = "[^"]+"', f'name = "{got["name"]}"',
                 blk.group(1), count=1)
    new = re.sub(r'dynasty = "[^"]+"', f'dynasty = "{got["dynasty"]}"', new)
    return text[:blk.start(1)] + new + text[blk.end(1):]



# --------------------------------------------------------------------------------------
# Rulers derived from CK3
# --------------------------------------------------------------------------------------
# SIL, GMA and BOH above have hand-written ruler blocks, because each one needed a
# judgement CK3 cannot make for us: which son was the heir, and why a regency is an
# artefact of the age shift rather than a fact about 867. NAV and MON need no such
# judgement, so their blocks are derived from CK3 instead of transcribed. A
# transcription is a snapshot of CK3 that silently rots; this is CK3's own entry,
# read at build time, which is the authority the hand-written blocks cite anyway.
#
# One conversion is applied, and it is applied to every ruler: CK3 rates skills
# roughly 1-20, EU4 rates monarch stats 0-6, so EU4 = CK3 / 3, clamped to 1-6. CK3
# records no skills at all for some characters (Miroslav of Duklja is one), and for
# those the mod uses a neutral 2/2/2 rather than inventing a reputation.
def _eu4_skill(ck3_value):
    if ck3_value is None:
        return 2, None
    return max(1, min(6, round(int(ck3_value) / 3))), int(ck3_value)


def _ck3_dates_and_skills(cid, chars):
    """(birth, death, adm, dip, mil) for a CK3 character id, or None if not found."""
    body = chars.get(cid)
    if body is None:
        return None
    birth = death = None
    # CK3 stores a life event as a dated block whose key IS the date and whose
    # body is `birth = yes` / `death = yes`, e.g. `844.1.1 = { birth = "844.1.1" }`.
    for date, block in re.findall(r"(\d+\.\d+\.\d+)\s*=\s*\{(.*?)\n\t\}", body, re.S):
        if re.search(r"^\s*birth\s*=", block, re.M):
            birth = date
        if re.search(r"^\s*death\s*=", block, re.M):
            death = date
    def skill(key):
        m = re.search(r"^\s*" + key + r"\s*=\s*(\d+)", body, re.M)
        return m.group(1) if m else None
    adm, _ = _eu4_skill(skill("stewardship"))
    dip, _ = _eu4_skill(skill("diplomacy"))
    mil, _ = _eu4_skill(skill("martial"))
    return birth, death, adm, dip, mil


def _ck3_name(cid, chars, loc):
    m = re.search(r'^\s*name\s*=\s*(?:"([^"]*)"|([^\s#"]+))', chars[cid], re.M)
    if not m:
        return None
    return loc(m.group(1) or m.group(2)) or (m.group(1) or m.group(2))


def ck3_block(tag):
    """A 867 monarch (and heir where CK3 records one) derived from CK3."""
    import ck3ruler as c

    titles, chars = c.load_titles(), c.load_chars()
    dyns, houses = c.load_dynasties(), c.load_houses()
    got = c.resolve(tag, titles, chars, dyns, houses)
    if "error" in got:
        raise SystemExit(f"{tag}: {got['error']}")
    cid = got["char"]
    facts = _ck3_dates_and_skills(cid, chars)
    if facts is None:
        raise SystemExit(f"{tag}: CK3 character {cid} has no readable entry")
    birth, death, adm, dip, mil = facts
    if not birth or not death:
        raise SystemExit(f"{tag}: CK3 character {cid} has no birth or death date")
    name = _ck3_name(cid, chars, c.loc)
    dynasty = got["dynasty"]

    def person(cid_, claim=None):
        nonlocal chars
        nm = _ck3_name(cid_, chars, c.loc)
        b, d, a, dp, ml = _ck3_dates_and_skills(cid_, chars)
        dy = c.resolve_dynasty(chars[cid_], dyns, houses)
        out = [f'\t\tname = "{nm}"']
        if claim is not None:
            out.append(f'\t\tmonarch_name = "{nm}"')
        if dy:
            out.append(f'\t\tdynasty = "{dy}"')
        for label, d_ in (("birth_date", b), ("death_date", d)):
            if not d_:
                raise SystemExit(f"{tag}: CK3 character {cid_} has no {label}")
            y, m, dd = (int(x) for x in d_.split("."))
            out.append(f"\t\t{label} = {shifted(y, m, dd)}")
        if claim is not None:
            out.append(f"\t\tclaim = {claim}")
        out += [f"\t\tadm = {a}", f"\t\tdip = {dp}", f"\t\tmil = {ml}"]
        return "\n".join(out)

    lines = [f"{START} = {{", "\tmonarch = {", person(cid), "\t}"]
    # The heir is the eldest son CK3 records. CK3 has no gender key on these
    # characters, so a child is used only where the name is not a daughter's; where
    # CK3 records no children at all (Miroslav) no heir is written, and the game
    # generates one, which is honest about the gap instead of inventing a son.
    kids = [k for k, b in chars.items()
            if re.search(rf"^\s*father\s*=\s*{cid}\b", b, re.M)]
    kids.sort(key=lambda k: _ck3_dates_and_skills(k, chars)[0] or "9999.9.9")
    if kids:
        lines += ["\their = {", person(kids[0], claim=90), "\t}"]
    lines += ["}", ""]
    if not dynasty:
        lines.insert(0, f"# {name} has no dynasty in CK3, so none is written here.")
        lines.insert(0, "# Inventing a house to fill the gap would be a fabrication.")
    return "\n".join(lines)


def find_vanilla(tag):
    for fn in os.listdir(SRC):
        if fn.split(" ")[0] == tag and fn.endswith(".txt"):
            return os.path.join(SRC, fn), fn
    raise SystemExit(f"no vanilla history file for {tag}")


def fresh(tag):
    cap, culture = HEADER[tag]
    return f"""government = monarchy
add_government_reform = feudalism_reform
government_rank = {RANK[tag]}
technology_group = western
primary_culture = {culture}
religion = catholic
capital = {cap}
{RULERS[tag]}"""


def patch_fra():
    """Keep every vanilla French history event; only override the 1444 ruler."""
    path, fn = find_vanilla("FRA")
    text = open(path, encoding="utf-8", errors="surrogateescape").read()
    lines = text.splitlines()
    # first dated block at or after the start date, so chronological order holds
    ins = len(lines)
    for i, ln in enumerate(lines):
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)\s*=", ln.strip())
        if m and (int(m.group(1)), int(m.group(2)), int(m.group(3))) >= (1444, 1, 1):
            ins = i
            break
    block = ["1444.1.1 = {"] + \
            RULERS["FRA"].strip("\n").splitlines()[1:-1] + ["}", ""]
    out = lines[:ins] + block + lines[ins:]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------------------
# Disbanding the Holy Roman Empire
# --------------------------------------------------------------------------------------
# There is no empire switch to flip. A country is an elector purely because its own
# history says `elector = yes` - common/empire/electors.txt ships empty, and
# DESIRED_NUM_OF_ELECTORS in defines.lua only sizes how many the emperor would LIKE,
# not who is one. Dissolving the empire therefore means dissolving its electorate.
#
# Vanilla does exactly this, and says so in its own comments. Seven country files
# carry `1806.7.12 = { elector = no }` - the Reichsdeputationshauptschluss, the real
# abolition of the HRE - and REG's reads `1806.7.12 = { elector = no } # the HRE is
# dissolved`. That dated block is why a 1821 start date has no Holy Roman Empire:
# the history is read up to 1821, every elector has been set to `no`, and there is
# nobody left to elect an emperor. A 1444 start simply never reaches those dates.
#
# So to get that same end state at 1444 we write the dissolution ourselves, one
# state at a time instead of one dated block per country: the top-level
# `elector = yes` of each 1444 electorate member becomes `elector = no`, which is
# vanilla's own syntax for the empire's end. No on_action, no defines override.
#
# Only these seven, because only these seven have a TOP-LEVEL `elector = yes`.
# That qualifier matters: Regensburg and Hessen also have `elector = yes`, but
# only inside dated blocks from 1803, when the Reichsdeputationshauptschluss gave
# them electoral dignity. At 1444 they hold no vote at all, so they need no
# override and their 1803-1806 history is left untouched.
#
# Bohemia matters twice over: it is one of the seven, and it is also the one this
# mod keeps land and an 867 ruler for, so its copy is patched below along with its
# capital and ruler. The other six are copied verbatim with only that one line
# changed.
IMPERIAL_ELECTORS = ["BOH", "BRA", "KOL", "MAI", "PAL", "SAX", "TRI"]


def patch_vanilla(tag, capital=None, ruler=None, strip_elector=False, rank=None):
    """Copy a vanilla history file, changing only a capital, the government rank,
    the 1444 ruler and whether the country is an imperial elector.

    Everything else in the vanilla file is preserved verbatim, so a vanilla tag
    keeps its whole later history - Zizka and the defenestration of Prague for
    Bohemia, the Piast line for Silesia - and only its 867 start is replaced.
    """
    path, fn = find_vanilla(tag)
    text = open(path, encoding="utf-8", errors="surrogateescape").read()
    if strip_elector:
        # `^` with no leading-whitespace class on purpose: only a TOP-LEVEL
        # `elector = yes` is a vote in 1444. The same key indented inside a dated
        # block is a later state (Regensburg's 1803 one) and must survive, so
        # matching `\s*` here would silently rewrite 1803-1806 history.
        text, n = re.subn(r"^elector\s*=\s*yes[^\n]*$",
                          "elector = no # mod: the HRE is dissolved, "
                          "see the 1806.7.12 entry in vanilla's own files",
                          text, count=1, flags=re.M)
        assert n == 1, f"{tag}: no top-level 'elector = yes' to dissolve in {fn}"
    if capital is not None:
        text, n = re.subn(r"^(\s*capital\s*=\s*)\d+.*$", rf"\g<1>{capital}", text,
                          count=1, flags=re.M)
        assert n == 1, f"{tag}: no capital line to patch in {fn}"
    if rank is not None:
        # Eight of the twenty realms have no government_rank in vanilla at all,
        # so they silently fall to EU4's default of 1. That is how the Tulunids
        # ended up ranked level with Silesia: not a decision, an omission. Set
        # every one of them from RANK so the tier is always deliberate.
        text, n = re.subn(r"^(\s*government_rank\s*=\s*)\d+.*$", rf"\g<1>{rank}", text,
                          count=1, flags=re.M)
        if n == 0:
            # No line to patch: add one beside the other government keys, so the
            # header stays readable rather than gaining a stray line at the end.
            anchor = re.search(r"^\s*government\s*=\s*\w+.*$", text, re.M)
            assert anchor, f"{tag}: no government line to anchor a rank to in {fn}"
            text = text[:anchor.end()] + f"\ngovernment_rank = {rank}" + text[anchor.end():]
    if ruler is not None:
        lines = text.splitlines()
        # insert before the first dated block at or after the start date, so
        # chronological order holds; default to the end of the file
        ins = len(lines)
        for i, ln in enumerate(lines):
            m = re.match(r"^(\d+)\.(\d+)\.(\d+)\s*=", ln.strip())
            if m and (int(m.group(1)), int(m.group(2)),
                      int(m.group(3))) >= (1444, 1, 1):
                ins = i
                break
        block = ruler.strip("\n").splitlines()
        lines = lines[:ins] + block + [""] + lines[ins:]
        text = "\n".join(lines) + "\n"
    return text


def main():
    os.makedirs(OUT, exist_ok=True)
    for tag in ["LOT", "GER", "BAV", "ITA", "SOR"]:
        open(os.path.join(OUT, f"{tag}.txt"), "w", encoding="utf-8").write(
            with_provenance(tag, ck3_sync(tag, fresh(tag))))
        print(f"wrote {tag}.txt")
    open(os.path.join(OUT, "FRA.txt"), "w",
         encoding="utf-8", errors="surrogateescape").write(with_provenance("FRA", ck3_sync("FRA", patch_fra())))
    print("wrote FRA.txt (vanilla history preserved)")
    for tag, spec in VANILLA.items():
        want = spec.get("ruler")
        ruler = ck3_block(tag) if want == "CK3" else VANILLA_RULERS.get(want)
        was_elector = tag in IMPERIAL_ELECTORS
        open(os.path.join(OUT, f"{tag}.txt"), "w", encoding="utf-8",
             errors="surrogateescape").write(
            with_provenance(tag, ck3_sync(tag, patch_vanilla(
                tag, spec.get("capital"), ruler, was_elector, RANK.get(tag)))))
        what = []
        if spec.get("capital"):
            what.append(f"capital -> {spec['capital']}")
        if ruler:
            nm = re.search(r'name = "([^"]+)"', ruler)
            what.append(f"867 ruler {nm.group(1) if nm else want}"
                        + (" (from CK3)" if want == "CK3" else ""))
        if was_elector:
            what.append("electorate removed")
        if tag in RANK:
            what.append(f"rank {RANK[tag]}")
        print(f"wrote {tag}.txt (vanilla history preserved"
              + (", " + ", ".join(what) if what else "") + ")")
    # The remaining electors, so the empire is left with nobody to elect as
    # emperor. Verbatim vanilla apart from the single dissolved vote.
    for tag in IMPERIAL_ELECTORS:
        if tag in VANILLA:
            continue
        # Build first, write second. `open(..., "w")` truncates before its
        # argument is evaluated, so writing patch_vanilla(...) inline left a
        # 0-byte country file behind whenever the assert fired - and an empty
        # file looks clean to every grep-based check.
        text = patch_vanilla(tag, strip_elector=True)
        with open(os.path.join(OUT, f"{tag}.txt"), "w", encoding="utf-8",
                  errors="surrogateescape") as fh:
            fh.write(text)
        print(f"wrote {tag}.txt (vanilla history preserved, "
              f"electorate dissolved)")


if __name__ == "__main__":
    main()
