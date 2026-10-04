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


# tag -> (vanilla file, name, capital, primary culture, ruler block, extra)
# Culture ids are validated against common/cultures/00_cultures.txt: EU4 1.37
# has no "german" and no "italian" at all, so those would silently fall back.
# Lotharingia is Burgundian (it holds Burgundy, Provence, Savoy and the
# Lotharingian Low Countries); Italy is Lombard, as Louis II's kingdom was.
HEADER = {
    "LOT": (1878, "burgundian"),
    "GER": (1876,  "hessian"),
    "BAV": (65,   "bavarian"),
    "ITA": (4728, "lombard"),
    "SOR": (60,   "sorbian"),
}

# The five Carolingian kingdoms are peers at rank 2. Lusatia is a free
# minor principality, so it sits a step below them.
RANK = {"LOT": 2, "GER": 2, "BAV": 2, "ITA": 2, "SOR": 1}

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


def patch_vanilla(tag, capital=None, ruler=None, strip_elector=False):
    """Copy a vanilla history file, changing only a capital, the 1444 ruler and
    whether the country is an imperial elector.

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
        ruler = VANILLA_RULERS.get(spec.get("ruler"))
        was_elector = tag in IMPERIAL_ELECTORS
        open(os.path.join(OUT, f"{tag}.txt"), "w", encoding="utf-8",
             errors="surrogateescape").write(
            with_provenance(tag, ck3_sync(tag, patch_vanilla(
                tag, spec.get("capital"), ruler, was_elector))))
        what = []
        if spec.get("capital"):
            what.append(f"capital -> {spec['capital']}")
        if ruler:
            what.append(f"867 ruler {VANILLA_RULERS[spec['ruler']].split(chr(10))[3].split(chr(34))[1]}")
        if was_elector:
            what.append("electorate removed")
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
