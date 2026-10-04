#!/usr/bin/env python3
"""Resolve CK3's 867 bookmark and copy ruler name + dynasty into EU4 country files.

Why this exists
---------------
The mod's 867-flavoured realms each name their ruler after a CK3 character who
holds the matching CK3 title at 867.1.1. Those two fields - the ruler's name and
his dynasty - were being transcribed by hand, which is exactly the kind of thing
that silently rots: a dynasty string ends up invented ("Asturleonese" was his
CK3 *culture*, not his dynasty) and nothing catches it.

This module does the lookup properly and checks the country files against it.
It deliberately does NOT touch stats or birth/death dates:

  * adm/dip/mil are read off CK3 skills/traits and then deliberately re-scaled,
    because CK3's 1-25 scale is not EU4's 1-6. Those are judgement calls and are
    commented per-ruler in the country files.
  * birth_date/death_date are translated so the ruler is alive and adult at the
    mod's 1444.11.11 start, since CK3 has no 1444. Also a judgement call.

So the contract is narrow on purpose: name and dynasty are copied, stats and
dates are left alone.

CK3 name spellings are preserved rather than anglicised - Basileios not Basil,
Alfonsu not Alfonso - because that is the point of drawing from CK3.

Usage
-----
    python3 tools/ck3ruler.py            # report drift for every mapped tag
    python3 tools/ck3ruler.py --fix      # rewrite the name/dynasty lines
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parent
CDIR = MOD / "history" / "countries"
GAME_CK3 = "/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game"

# CK3's only bookmark, and the date this mod's flavour is taken from. Kept as a
# string because it is also spliced into regexes when scanning dated blocks.
DATE = "867.1.1"
START = (1444, 11, 11)

# Mod tag -> CK3 character id. This is the only thing that has to be written by
# hand; name and dynasty are both derived from the character.
#
# A character id is used rather than a title lookup because it is exact: titles
# get reassigned, split and vacated between bookmarks, and d_granada in
# particular has NO holder at all on 867.1.1 (only Umar ibn Hafsun from 880), so
# a title-keyed registry silently resolves to nothing. Character ids are stable
# file facts.
#
# Where a tag has a matching CK3 title, TITLES below cross-checks that the
# character really is the 867 holder of it. That check is advisory, not
# authoritative: ADU is intentionally mapped to a character rather than to
# d_granada, because CK3 models Granada in 867 as a county c_granada under
# k_andalusia with no duchy at all.
#
# CRT is absent on purpose. CK3 models no Crete whatsoever: no k_crete, d_crete
# or c_candia exists. Abu Hafs Umar is a historical invention documented in
# CRT.txt, so there is nothing to verify it against and listing it would produce
# a false "no such character" failure.
#
# The tags below are the only ones actually derived from CK3. That is a deliberate
# subset by design, not an oversight: NOT_CK3 further down carries a written reason for
# every other land-holding tag, and `land_holders()` enforces that the two lists
# together account for all of them. BOH, GMA and SIL are absent because they are
# not CK3-sourced at all - local Slavic rulers with dynasty strings invented for
# the mod.
# THE MAP: EU4 tag -> CK3 title. This is the only registry in the file; the CK3
# character is not stored, because it is not independent data - it is simply
# whoever holds this title on CK3's 867.1.1, read at run time. Keeping the two
# apart was a bug waiting to happen: a tag could name one character and be
# cross-checked against the holder of a different title, and nothing would notice.
#
# So adding a realm is one line here. Nothing else needs to change.
TITLES = {
    # -- the mod's own Carolingian partition ----------------------------------
    # CK3 has no realm-by-realm match for this partition, so these are the closest
    # title each EU4 realm corresponds to, and the strings are lifted verbatim from
    # CK3's own 867 state.
    #
    # All five are dynasty 25061 "Karling", so the mod's shared "de Carolingie"
    # becomes CK3's spelling. Names lose their epithets, because CK3 has none: it
    # calls him "Charles", not "Charles the Bald", and "Ludwig", not "Louis the
    # German". That is the point of lifting verbatim.
    "FRA": "k_france",         # Charles,   Karling
    "LOT": "k_lotharingia",    # Lothaire,  Karling
    "GER": "k_east_francia",   # Ludwig,    Karling
    "ITA": "k_italy",          # Louis,     Karling
    # Bavaria maps to the DUCHY, not the kingdom, and that is deliberate. CK3 has
    # no independent Bavaria in 867: k_bavaria is held by Ludwig - the same man as
    # k_east_francia - continuously from 826.1.1 until 876.1.1, and Carloman only
    # takes it in 876. Since the mod does split Bavaria off under Carloman in 867,
    # d_bavaria is the title whose 867 holder is him. k_bavaria would make this a
    # second "Ludwig"/"Karling" and erase the realm.
    "BAV": "d_bavaria",        # Karlmann,  Karling
    # -- the mod's western Slavic realms --------------------------------------
    # CK3 models no Sorbian title: k_sorbs and d_sorbs both have no holder.
    # d_lausitz is the nearest title with an actual 867 ruler, so the mod's
    # Mstivoj/"of Lusatia" becomes CK3's Radomil/Milczanow.
    "SOR": "d_lausitz",        # Radomil,   Milczanow
    # CK3's d_lower_silesia holder is Gardomir, and the mod's Silesia already
    # called its ruler Gardomir Slezan; "Slezan" was a guess at CK3's dynn_Slezan,
    # which is spelled with diacritics.
    "SIL": "d_lower_silesia",  # Gardomir,  Slezan
    # GMA holds the two Moravian provinces (Brno 265, Olomouc 4237) as well as
    # Galicia, and its ruler was already Rostislav, so k_moravia is the title whose
    # 867 holder the mod was reaching for.
    "GMA": "k_moravia",        # Rostislav, Mojmird
    # -- the mod's other CK3-sourced realms ----------------------------------
    "ARB": "e_arabia",         # al-Mu'tazz, Abbasid
    "BYZ": "e_byzantium",      # Basileios,  dynasty 644
    "BUL": "k_bulgaria",       # Boris,     Balgarsko
    "DAL": "d_dalmatia",       # Amphilochios, Radenos
    "EGY": "k_egypt",          # Ahmad,     Tulunid
    # ADU is a county, because that is all CK3 has: in 867 there is no d_granada,
    # and Granada is c_granada under k_andalusia.
    "ADU": "c_granada",        # Nayih,     Nayihid
    "ASU": "k_asturias",       # Alfonsu,   House of Cantabria
    "NAV": "k_navarra",        # Gartzia,   Iniga
    # The Papal State keeps Rome: 118 Roma is deliberately not taken (see
    # PROVINCE_OWNERS in gen_provinces.py), so PAP still holds one province at
    # the start date on the mod's own account. Its 867 holder is Pope Nicholas I
    # - CK3 character 7853, "Niccolo", localisation Niccolò.
    #
    # He is the one mapped character with NO dynasty and no dynasty_house at all,
    # which is historically ordinary: the papacy is not a hereditary house in
    # CK3's model. So the name lifts and the dynasty does not exist to lift.
    # Nothing is invented to cover the gap - until this mod writes its own PAP.txt
    # there is nothing to sync, and this resolves to a NOTE like NAV does.
    "PAP": "k_papal_state",    # Niccolo,   (no dynasty in CK3)
}

# Every other tag that owns land at the mod's start date, with the reason it is
# not taken from CK3. This exists so the audit has no blind spot: `land_holders()`
# derives the real set from the generated province files, and any land-holder that
# appears in neither TITLES nor here is reported as unclassified and fails.
# Without it, adding a realm to the mod silently escapes the check.
#
# Two kinds of entry, deliberately kept apart:
#
#   * "vanilla" - the mod never writes a ruler for it; it keeps vanilla's own
#     history file and vanilla's 1444 ruler. There is nothing to derive.
#   * "mod-invented" - the mod authors the ruler and CK3 has no counterpart, so
#     copying a name would overwrite deliberate design with a lookup artefact.
NOT_CK3 = {
    # Bohemia: CK3 has no k_bohemia holder at 867 to check against - not an
    # unheld title, simply no recorded holder - so the mod's own Borivoj stands.
    "BOH": "mod-invented: Borivoj is the mod's own Bohemian ruler; CK3 records no "
           "867 holder for k_bohemia to verify against",
    # CK3 has no Crete at all: no k_crete, d_crete or c_candia exists, so there is
    # no character to compare a name or dynasty against. Abu Hafs Umar is a
    # historical invention documented in CRT.txt.
    "CRT": "no CK3 model: CK3 has no Crete, so there is no character to compare",
    # -- vanilla tags the mod gives land to but never writes a ruler for -------
    # These keep vanilla's own country file and vanilla's 1444 ruler, so the mod
    # has nothing to derive. Listed so the audit is exhaustive, not because any
    # of them is being checked.
    "BRA": "vanilla: keeps vanilla's Brandenburg file and 1440 Hohenzollern ruler",
    "CRI": "vanilla: keeps vanilla's Azov ruler",
    "DTT": "vanilla: keeps vanilla's Leitha ruler",
    "HSA": "vanilla: keeps vanilla's ruler",
    "HUN": "vanilla: keeps vanilla's 1444.11.10 Hunyadi block",
    "MKL": "vanilla: keeps vanilla's Montferrat ruler",
    "MON": "vanilla: keeps vanilla's Adriatic ruler",
    "SHL": "vanilla: keeps vanilla's Schauenburg ruler",
    "STE": "vanilla: keeps vanilla's Stettin ruler",
    "TEU": "vanilla: keeps vanilla's Teutonic ruler",
    "WOL": "vanilla: keeps vanilla's Wolgast ruler",
}


# An heir belongs to the ruler's dynasty unless a succession deliberately changed
# it. Listing a tag here opts its heir out of the sync in main(); there are no
# such cases at the moment, but a realm whose heir starts a new house should say
# so here rather than have --fix quietly overwrite it.
HEIR_DYNASTY_OVERRIDE = {}


# CK3 bug to work around, not a mod choice.
#
# common/dynasty_houses/00_dynasty_houses.txt declares
#     house_abbasid = { name = dynn_Abbasid  dynasty = 7296 }
# but 7296 is declared in common/dynasties as dynn_Hashimid. So the Abbasid
# house points at the Hashimid dynasty, and copying the nested dynasty would give
# al-Mu'tazz - an Abbasid caliph in CK3's own history - a Hashimid dynasty name.
# The house's own name key is correct and is what the mod uses, so a house is
# preferred over the dynasty it nests, and this entry records why.
#
# Note the house declares `name = dynn_Abbasid` WITHOUT quotes, unlike every
# other house in the file. That is why the house parser accepts both quoted and
# bare name values.
HOUSE_NAME_OVERRIDE = {
    "house_abbasid": "dynn_Abbasid",
}


def _date_key(s: str) -> tuple:
    p = [int(x) for x in s.split(".")]
    return tuple(p + [0] * (3 - len(p)))


def _norm(text: str) -> str:
    """Normalise line endings.

    CK3 ships some files with CRLF and some with LF, and the character files are
    mixed. The brace-walking below matches `key = {` at the start of a line, so a
    stray \\r does not break the block boundaries it relies on.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _blocks(text: str):
    """Yield (head, body) for every top-level `key = { ... }` in a Paradox file."""
    for m in re.finditer(r"^([a-zA-Z_0-9]+)\s*=\s*\{", text, re.M):
        i = m.end() - 1
        d = 0
        while i < len(text):
            if text[i] == "{":
                d += 1
            elif text[i] == "}":
                d -= 1
                if d == 0:
                    break
            i += 1
        yield m.group(1), text[m.end():i]


def _inner_blocks(body: str):
    """Yield (key, body) for nested blocks.

    Key charset includes `.` because these are dated history blocks ("867.1.1")
    as well as named ones ("holder"), and the dated ones are the whole point of
    walking history/titles. The leading [ \t]* is load-bearing: every nested block
    inside a title is indented with a tab, so anchoring at "^" with no indent
    allowance matches nothing at all and silently yields zero blocks.
    """
    for m in re.finditer(r"^[ \t]*([a-zA-Z_0-9.]+)\s*=\s*\{", body, re.M):
        i = m.end() - 1
        d = 0
        while i < len(body):
            if body[i] == "{":
                d += 1
            elif body[i] == "}":
                d -= 1
                if d == 0:
                    break
            i += 1
        yield m.group(1), body[m.end():i]


# ---------------------------------------------------------------- CK3 data ---

def load_titles():
    """title id -> list of (date, body) for its dated history blocks."""
    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "titles").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for tid, body in _blocks(text):
            out.setdefault(tid, []).extend(_inner_blocks(body))
    return out


def holder_at(title, titles):
    """Character id holding `title` on DATE, or None."""
    return holder_at_exact(title, titles)[0]


def holder_at_exact(title, titles):
    """(holder, carried_block_date_or_None) for `title` on DATE.

    CK3 does not write a holder into every title's DATE block. k_egypt's holder
    is set at 866.1.1; k_france, k_italy, k_lotharingia and k_east_francia carry
    their holders forward from 840/843/855/866 with nothing dated 867 at all. That
    is normal - the state is real, it is simply recorded by continuity - so the
    holder is still returned. But the caller is told which block it came from,
    because a naive "last block wins" cannot tell continuity apart from a title
    that simply stopped being updated, and mistaking one for the other would
    report a confident wrong name.
    """
    blocks = titles.get(title)
    if not blocks:
        return None, None
    best = None
    at_date = None
    for head, body in blocks:
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", head)
        if not m:
            continue
        d = f"{m[1]}.{m[2]}.{m[3]}"
        if _date_key(d) > _date_key(DATE):
            continue
        h = re.search(r"holder\s*=\s*(\d+)", body)
        if not h:
            continue
        if _date_key(d) == _date_key(DATE):
            at_date = h.group(1)
        best = (h.group(1), d)
    if at_date is not None:
        return at_date, None
    return best if best else (None, None)


def load_chars():
    """character id -> body text."""
    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "characters").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for cid, body in _blocks(text):
            out.setdefault(cid, body)
    return out


def load_dynasties():
    """dynasty key (e.g. dynn_Tulunid) -> name key (dynn_Tulunid)."""
    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasties").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"(dynn_\w+)"', body)
            if n:
                out[key] = n.group(1)
    return out


def load_houses():
    """house key -> (house name key, nested dynasty key or None).

    The name pattern deliberately accepts an unquoted value: house_abbasid is the
    one house in CK3's file that writes `name = dynn_Abbasid` with no quotes, and
    a quoted-only pattern would read that house as having no name at all.
    """
    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasty_houses").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"?\s*(dynn_\w+)\s*"?', body)
            d = re.search(r"^\s*dynasty\s*=\s*(\w+)", body, re.M)
            name_key = n.group(1) if n else None
            out[key] = (HOUSE_NAME_OVERRIDE.get(key, name_key),
                        d.group(1) if d else None)
    return out


_LOC_FILES = None
# The key charset includes `-` and `.` as well as word characters. CK3 mixes key
# styles freely inside one file: names/character_names_l_english.yml has entries
# like ` Al-Mu_tazz:1 "al-Mu'tazz"` alongside plain `Abbasid:0 "Abbasid"`, and a
# `\\w`-only key class silently drops every hyphenated key. That is not cosmetic:
# it is why al-Mu'tazz's name came out as the raw untranslated key "Al-Mu_tazz".
_LOC_RE = re.compile(r'^[ \t]*([\w.\-]+)\s*:\d*\s*"(.*?)"[ \t\r\n]*$', re.M)


def loc(key):
    """English text of a localisation key, searching every English file.

    The whole English tree is scanned once and indexed by key, rather than
    re-walking ~1250 files on every call. The earlier per-key version looked
    correct but was subtly broken: it cached every match it saw while scanning
    for one key, so the first lookup populated the cache with a single entry and
    every later lookup short-circuited on "cache is non-empty" and returned None
    for perfectly valid keys. Indexing the whole tree once cannot have that
    failure mode.

    CRLF is tolerated explicitly. CK3's yml files carry \\r\\n and these lines are
    at end-of-file positions, where a strict $ anchor after the closing quote
    silently fails to match.
    """
    global _LOC_FILES
    if _LOC_FILES is None:
        _LOC_FILES = {}
        for pat in ("localization/english", "localisation/english"):
            root = Path(GAME_CK3) / pat
            if not root.is_dir():
                continue
            for f in sorted(root.rglob("*.yml")):
                try:
                    t = _norm(f.read_text(errors="replace"))
                except OSError:
                    continue
                for k, v in _LOC_RE.findall(t):
                    # First definition wins, so a later file cannot shadow an
                    # earlier one for a key that is genuinely defined twice.
                    _LOC_FILES.setdefault(k, v)
    return _LOC_FILES.get(key)


def resolve_dynasty(body, dyns, houses):
    """Dynasty string for a CK3 character body.

    A character usually names a `dynasty = <id>`. Some name only a
    `dynasty_house = <house>`, and then the house is the authority.

    For the house case the house's OWN name key wins, not the dynasty the house
    nests. house_cantabria declares `dynasty = erwigiana`, but its own name key
    is dynn_Cantabria, and "Cantabria" is what identifies the house the
    character actually sits in. The nested dynasty is only a fallback for a house
    that declares no name at all.

    This distinction is the whole reason ASU is "Cantabria" and not "Erwigiana",
    so it is spelled out here rather than left to a reader to infer.
    """
    m = re.search(r"^\s*dynasty\s*=\s*(\w+)", body, re.M)
    if m:
        return loc(dyns.get(m.group(1), "")) or m.group(1)
    h = re.search(r"^\s*dynasty_house\s*=\s*(\w+)", body, re.M)
    if h:
        house = h.group(1)
        name_key, nested = houses.get(house, (None, None))
        name_key = HOUSE_NAME_OVERRIDE.get(house, name_key)
        if name_key:
            return loc(name_key) or name_key
        if nested:
            return loc(dyns.get(nested, "")) or nested
    return None


def resolve(tag, titles, chars, dyns, houses):
    """{tag: {char, name, dynasty, title, carried}} or {tag: {error: ...}}.

    The character is looked up as the 867 holder of TITLES[tag] rather than stored,
    so the map holds one fact per realm - which title it corresponds to - and
    cannot come to disagree with itself.
    """
    title = TITLES[tag]
    cid, carried = holder_at_exact(title, titles)
    if cid is None:
        return {"error": f"CK3 has no 867 holder for {tag}'s title {title}"}
    body = chars.get(cid)
    if body is None:
        return {"error": f"CK3 has no character {cid} for {tag}"}
    # CK3 writes a character's name three ways, and all three occur in the files
    # this mod reads, so all three have to parse:
    #     name = "Nayih"     quoted
    #     name = Lothaire    bare, unquoted - 698 such lines in CK3's characters,
    #                        including Lothair II, who holds k_lotharingia
    #     name = "Nayih" # Nayih ibn Suleyman, Sheik of Granada (848-880)
    #                        quoted with a trailing comment, which is the most
    #                        common form of all
    # Anchoring to end-of-line would drop the commented form, which is why this
    # matches the value and stops at the comment instead.
    nm = re.search(r'^\s*name\s*=\s*(?:"([^"]*)"|([^\s#"]+))', body, re.M)
    if not nm:
        return {"error": f"character {cid} has no name line"}
    raw = nm.group(1) or nm.group(2)
    # CK3 character names are localisation keys when they need one, e.g.
    # "Al-Mu_tazz" is defined as "al-Mu'tazz". Prefer the localisation so the
    # apostrophe comes out right.
    name = loc(raw) or raw
    dy = resolve_dynasty(body, dyns, houses)
    return {"char": cid, "name": name, "dynasty": dy, "title": title,
            "carried": carried, "no_dynasty": not dy}


# -------------------------------------------------------------- country files -

def land_holders():
    """{tag: n_provinces} for every tag owning land at the mod's start date.

    Read back out of the generated province files rather than from a hand-kept
    list, so the audit follows the mod instead of an intention: if a realm gains
    or loses land, this set changes with it. check_start.effective is the same
    dated-history replay check_start.py uses, so this agrees with it by
    construction - including for provinces whose only owner is set in a dated
    block (Azores and Madeira) or which vanilla leaves unowned.
    """
    from check_start import effective
    out = {}
    for f in sorted((MOD / "history" / "provinces").glob("*.txt")):
        pid = int(f.name.split("-")[0].strip())
        text = f.read_text(encoding="utf-8", errors="surrogateescape")
        owner, _ctrl, _core, _hre = effective(text)
        if owner:
            out[owner] = out.get(owner, 0) + 1
    return out


def monarch_block(path):
    """(full_text, monarch_body) for the 1444.1.1 monarch block."""
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    m = re.search(r"^1444\.1\.1 = \{\s*\n\tmonarch = \{(.*?)^\t\}", text,
                  re.M | re.S)
    return text, (m.group(1) if m else None)


def current(body):
    """(name, dynasty) as currently written in a monarch body."""
    if body is None:
        return (None, None)
    n = re.search(r'name = "([^"]+)"', body)
    d = re.search(r'dynasty = "([^"]+)"', body)
    return (n.group(1) if n else None, d.group(1) if d else None)


def heir_dynasty(text):
    """Dynasty string on the 1444.1.1 heir, or None if there is no heir.

    Reads the whole 1444.1.1 block rather than the monarch sub-block, because the
    heir sits beside the monarch, not inside it.
    """
    blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
    if not blk:
        return None
    heir = re.search(r'heir = \{(.*?)\n\t\}', blk.group(1), re.S)
    if not heir:
        return None
    d = re.search(r'dynasty = "([^"]+)"', heir.group(1))
    return d.group(1) if d else None


def main(argv):
    fix = "--fix" in argv
    titles, chars = load_titles(), load_chars()
    dyns, houses = load_dynasties(), load_houses()

    bad = []
    unwritten = []

    # Coverage first, so an unclassified realm is reported even if every mapped
    # tag happens to agree. Deriving the set from the province files is what makes
    # this a real gate: a tag added to the mod later shows up here unclassified.
    holders = land_holders()
    unclassified = sorted(t for t in holders
                          if t not in TITLES and t not in NOT_CK3)
    print(f"== {len(holders)} tags own land at the mod start date ==")
    print(f"   CK3-derived (name/dynasty checked): {len(TITLES)}")
    print(f"   classified as not CK3-derived      : {len(NOT_CK3)}")
    for t in unclassified:
        bad.append(f"{t} owns {holders[t]} provinces at the start date but is in "
                   f"neither TITLES nor NOT_CK3; add it to one of them with a "
                   f"reason so it is accounted for")
    if unclassified:
        print(f"   UNCLASSIFIED: {', '.join(unclassified)}")
    stale = [t for t in NOT_CK3 if t not in holders]
    if stale:
        # Not a failure: NOT_CK3 may legitimately carry a tag that no longer owns
        # land. Worth printing, because it usually means an allocation moved.
        print(f"   note: NOT_CK3 lists tags with no land now: {', '.join(sorted(stale))}")

    for tag in sorted(TITLES):
        got = resolve(tag, titles, chars, dyns, houses)
        path = CDIR / f"{tag}.txt"
        if "error" in got:
            bad.append(f"{tag}: {got['error']}")
            continue
        if not path.exists():
            # Mapped but unwritten. The mod can legitimately keep a vanilla
            # history file for a realm it only touches on the map - NAV and PAP
            # are the current examples - and then there is no name/dynasty of ours
            # to check, only a title worth reporting. The coverage gate below still
            # fails if a land-holder is in neither registry, so this cannot become
            # a way to skip a realm silently.
            print(f"  NOTE {tag} {got['title']} / char {got['char']}")
            print(f"        no {path.name}: keeps the vanilla file, nothing to sync")
            if got.get("no_dynasty"):
                print(f"        CK3 867: name={got['name']!r} and NO dynasty - "
                      f"CK3 records neither dynasty nor dynasty_house for this "
                      f"character. Nothing is invented for it: if this tag ever "
                      f"gets a country file, map it to a title whose 867 holder "
                      f"has a dynasty.")
            else:
                print(f"        CK3 867: name={got['name']!r} "
                      f"dynasty={got['dynasty']!r}")
            unwritten.append(tag)
            continue
        text, body = monarch_block(path)
        cn, cd = current(body)
        if got.get("no_dynasty"):
            bad.append(f"{tag}: CK3 character {got['char']} ({got['name']}) has "
                       f"neither dynasty nor dynasty_house, so the dynasty in "
                       f"{path.name} has nothing to be checked against. Map the "
                       f"tag to a CK3 title whose 867 holder has a dynasty "
                       f"rather than inventing one here.")
            print(f"  FAIL {tag} {got['title']} / char {got['char']}")
            print(f"        file: name={cn!r} dynasty={cd!r}")
            print(f"        CK3 : name={got['name']!r} and NO dynasty")
            continue
        hd = heir_dynasty(text)
        heir_bad = (hd is not None and hd != got["dynasty"]
                    and tag not in HEIR_DYNASTY_OVERRIDE)
        ok = (cn == got["name"] and cd == got["dynasty"] and not heir_bad)
        mark = "OK " if ok else "DRIFT"
        src = (f"<- {got['title']}"
               + (f" (holder carried from {got['carried']})"
                  if got.get("carried") else ""))
        print(f"  {mark} {tag} {src} / char {got['char']}")
        print(f"        file: name={cn!r} dynasty={cd!r}")
        print(f"        CK3 : name={got['name']!r} dynasty={got['dynasty']!r}")
        if hd is not None:
            print(f"        heir dynasty={hd!r}"
                  + ("  <- should match the ruler's" if heir_bad else ""))
        if not ok:
            if fix:
                # Rewritten inside the whole 1444.1.1 block rather than the monarch
                # sub-block, so the heir's dynasty can be brought along with the
                # ruler's. Only the ruler's NAME is taken from CK3: the heir is a
                # different man whom CK3 does not model here, so his name, stats and
                # dates are left exactly as the mod wrote them.
                blk = re.search(r"^1444\.1\.1 = \{\n(.*?)^\}", text, re.M | re.S)
                new = blk.group(1)
                if cn is not None:
                    new = re.sub(r'name = "[^"]+"', f'name = "{got["name"]}"',
                                 new, count=1)
                if cd is not None:
                    new = re.sub(r'dynasty = "[^"]+"',
                                 f'dynasty = "{got["dynasty"]}"', new, count=1)
                if heir_bad:
                    heir = re.search(r'heir = \{.*?\n\t\}', new, re.S)
                    nb = re.sub(r'dynasty = "[^"]+"',
                                f'dynasty = "{got["dynasty"]}"',
                                heir.group(0), count=1)
                    new = new[:heir.start()] + nb + new[heir.end():]
                text = text[:blk.start(1)] + new + text[blk.end(1):]
                path.write_text(text, encoding="utf-8",
                                errors="surrogateescape")
                print(f"        fixed -> {got['name']} / {got['dynasty']}")
            else:
                if cn != got["name"] or cd != got["dynasty"]:
                    bad.append(f"{tag}: file has {cn!r}/{cd!r}, CK3 has "
                               f"{got['name']!r}/{got['dynasty']!r}")
                if heir_bad:
                    bad.append(f"{tag}: heir dynasty is {hd!r} but the ruler's is "
                               f"{got['dynasty']!r}")

    if bad:
        print("\nFAIL:")
        for b in bad:
            print("  " + b)
        return 1
    checked = len(TITLES) - len(unwritten)
    print(f"\nOK: all {len(holders)} start-date land-holders are accounted for; "
          f"{checked} of {len(TITLES)} CK3-mapped rulers match CK3's 867 bookmark"
          + (f", {len(unwritten)} unwritten ({', '.join(sorted(unwritten))}) "
             f"keep vanilla's file" if unwritten else "")
          + (" (rewritten)" if fix else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))