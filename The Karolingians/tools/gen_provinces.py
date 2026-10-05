#!/usr/bin/env python3
"""The Karolingians - province pipeline. Areas, tags and single provinces in;
history/provinces out.

This is the one script that decides who owns what, and the one that writes the
province files. It used to be three: partition.py computed the Carolingian
partition and dumped cache/alloc.json, gen_provinces.py read that back and
layered the eastern transfers on top, and check_start.py/validate.py read the
result. Three places could disagree and did - Lusatia was still a sixth
partition kingdom here while the mod's own localisation had always described a
FIVE kingdom empire with Lusatia outside it - and the JSON between them was a
fourth copy that nothing checked against the code that produced it.

The specification
-----------------
Three kinds of statement, and nothing else. Every tag in this mod is assigned
land the same way; there are no special cases and no tiers.

    AREA_OWNERS     {tag: [area, ...]}       "the area of x is the tag of y"
    PROVINCE_OWNERS {province id: tag}       "loose province p is the tag of y"
    TRANSFERS       ((tag, [province ...]))  "hand this block to this tag"

Areas are the backbone because they are what the base game itself groups
provinces by, and "these areas plus these loose provinces" is how the map was
actually reasoned about. Loose provinces are not an escape hatch: EU4 areas
straddle 867 borders, so most of the judgement lives there, and every entry
carries the CK3 or historical evidence it rests on.

How the three combine
---------------------
Areas first, then loose provinces, then transfers - in that order, and only in
that direction. A loose province always beats its area. A transfer only takes
land that nobody has claimed yet, so it can never move a province some earlier
statement already gave away. That one rule is why the layers compose without a
precedence table, and why adding a transfer can never silently undo the
partition.

Writing the files
-----------------
Every mod province file REPLACES the vanilla file, so each one is a copy of
the vanilla file with only the start-state keys patched:
  owner / controller  -> the tag that takes the province
  add_core            -> appended; vanilla cores are KEPT so that every
                         absorbed tag (Habsburg, Milan, Savoy, Burgundy,
                         Switzerland ...) survives as a releasable
  hre                 -> forced to "no", which dissolves the HRE
Dated blocks (fort upgrades, religion changes, the 1806 hre = no events)
are preserved verbatim, then a final block dated at the start date re-asserts
owner/controller/core/hre so pre-1444 vanilla events cannot undo the partition.

Usage
-----
    python3 tools/gen_provinces.py           # write the province files
    python3 tools/gen_provinces.py --report  # balance report, writes nothing
    python3 tools/gen_provinces.py --alloc   # dump the allocation as JSON
"""
import json, os, re, shutil, sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
SRC = os.path.join(GAME, "history", "provinces")
MOD = str(HERE.parent)
OUT = os.path.join(MOD, "history", "provinces")
_PROVDATA = json.load(open(str(CACHE / "provdata.json")))
# Vanilla province/area lookups the specification is resolved against.
provs = _PROVDATA["provs"]
AREAS = _PROVDATA["areas"]
VANILLA_PDIR = SRC
VANILLA_CDIR = os.path.join(GAME, "history", "countries")

# Tag lists live in modtags.py, which every other tool imports too. They used to
# be copied into four scripts and the copies drifted - gen_countries.py still
# treated Lusatia as a partition kingdom while the mod's own localisation had
# always described a five-kingdom empire with Lusatia outside it.
#
# The aliases below are kept because half the file refers to them by these names.
from modtags import ALL_TAGS  # noqa: F401

# Layers 1 and 2 of the allocation now live on the Tag for each realm, because
# the reasoning is per-realm: "Trieste is Italy's but Krain is Bavaria's" is not
# a statement about a province, it is a statement about Italy and about Bavaria.
# tagdb.py holds the areas a realm takes whole and the individual provinces it
# carves back out of them; this file walks them.
#
# One province is deliberately still declared here. Venice is not a Tag - the mod
# maintains no realm for it and takes no land away from it beyond leaving it be -
# so its namesake province is the one land-holder this mod tracks without owning.
UNTRACKED_OWNERS = {
    112: "VEN",
}

from tagdb import AREA_OWNERS, PROVINCE_OWNERS  # noqa: E402

#: Layer 2 in the order the allocator reads it: the untracked holder first, then
#: everything the database declares. Every province appears exactly once, so this
#: ordering carries no meaning - the allocator deliberately makes one province's
#: claim beat its area's regardless of where it sits in the dict.
PROVINCE_OWNERS = {**UNTRACKED_OWNERS, **PROVINCE_OWNERS}

#: Capitals and names for the realms whose country file this generator writes.
#: Both are Tag fields; this is the projection this script reads.
from tagdb import BY_TAG  # noqa: E402

#: The realms whose province files carry an explicit capital, keyed as before.
#: That set is exactly the realms taking whole areas in layer 1 - the partition
#: proper. The single-province carve-outs (Silesia, Great Moravia, Navarra) are
#: tagged with a capital too, but they hold a province or two rather than a
#: region, and no capital is declared on their behalf.
CAPITAL = {tag: BY_TAG[tag].capital for tag in AREA_OWNERS}
NAME = {tag: BY_TAG[tag].name for tag in AREA_OWNERS}


# The named land blocks - BYZ_ALL, ARABIA_ALL, BUL_ALL, MOGYERS_LEVIDIA and the
# rest - live in landblocks.py, so a tag's land is not defined in two files at
# once. They are computed from the same provdata cache, by the same _owned() and
# _area() helpers, as they were when they sat below in this file.
from landblocks import (  # noqa: F401
    _AREA_OF, _REGION_OF_AREA, _owned, _area, _region,
    BYZ_CORES, BYZ_ANATOLIA, BYZ_ALBANIA, BYZ_CRIMEA, BYZ_CANDAR,
    BYZ_TREBIZOND, BYZ_THEODORO, BYZ_SOUTH_ITALY, BYZ_KARAMAN, BYZ_GREECE,
    BYZ_ALL, CRETE,
    ARABIA_MAMLUK, ARABIA_SYRIA, ARABIA_RAMAZAN, ARABIA_DULKADIR, ARABIA_MEDINA,
    ARABIA_HOLY_CITIES, ARABIA_QARA_QOYUNLU, ARABIA_AQ_QOYUNLU, ARABIA_MUSHASHA,
    ARABIA_AL_HAASA, ARABIA_FADL, ARABIA_ANIZAH, ARABIA_ALL,
    EGY_ALL, ASU_ALL, ADU_ALL, TAG_RENAMES,
    BUL_REST, BUL_CORES, BUL_BUDJAK, BUL_WALLACHIA, BUL_SERBIA,
    BUL_HUNGARY_BASIN, BALATON_RESERVED, BUL_ALL,
    MOGYERS_LEVIDIA, CRI_AZOV, MON_ADRIATIC, DAL_CORE,
)

# The two province-FILE text transforms, and the constants only they use. These
# rewrite a file's text rather than naming land, so they stay here with the
# writer that calls them.

def apply_renames(text):
    for old, new in TAG_RENAMES.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text


# CULTURE_GONE_867 - vanilla cultures that do not exist yet at this start date,
# mapped to what the province should be instead. Applied to every province the mod
# writes, keyed on the vanilla culture rather than on a hardcoded province list, so
# a province added to the map later cannot be left behind holding a culture that
# postdates the scenario.
#
# turkish -> greek, 32 provinces. The Anatolian beyliks - Karaman, Germiyan,
# Aydin, Dulkadir, Ramadan and the rest - are a late-13th-century idiom. In 867
# this land is Byzantine and Greek-speaking, and the Oghuz Turks have not crossed
# into Anatolia at all. Vanilla hands it to a beylik because vanilla starts in
# 1444, where they are correct.
#
# pontic_greek -> greek, 4 provinces: Kaffa, Trebizond, Canik, Mantrega. This is
# not a near miss. The culture is named for the Empire of Trebizond, founded in
# 1204 by Alexios III and David Komnenos and destroyed by Mehmed II in 1461 - 337
# years after this scenario. The Greek population of the Pontic coast was real in
# 867, since Sinope, Trapezus and Kerasous were Milesian colonies, but a
# Trapezuntine in 867 was simply a Byzantine Greek. So greek is right and "Pontic
# Greek" is not, rather than the two being neighbours.
#
# There is no `pontic` culture in this game at all. The Pontic *steppe* is a
# separate and larger question and is deliberately not touched here: its cultures
# are crimean, astrakhani and mishary, none of them Turkish, and the power there in
# 867 was the Khazar Khaganate. That is its own piece of work.

CULTURE_GONE_867 = {"turkish": "greek", "pontic_greek": "greek"}

# CONQUERED_BY_THE_ARABS - the five of those 32 that the Abbasids hold, and which
# therefore keep Muslim religion. Adana 327, Marash 332, Malatya 2303, Ayntab 4298
# and Divrigi 4310. Ayntab and Divrigi really had fallen to the Arabs by 867
# (851 and 855); the other three were still Byzantine and fall in 895-979, so they
# are this mod's deliberate early conquest rather than a 867 record. Named
# explicitly so the rule reads as "Byzantine land, minus what the Arabs took"
# instead of "whatever tag happens to be holding it today".
CONQUERED_BY_THE_ARABS = {327, 332, 2303, 4298, 4310}


# Two Muslim denominations turn up among the 33 Turkish-culture provinces, not
# one: 26 are sunni, and Malatya 2303, Sivas 329 and Divrigi 4310 are shiite. A
# rewrite that only matched `sunni` left Sivas as greek + shiite on Byzantine land,
# so both are matched here. Malatya and Divrigi are Arab-held and so keep theirs
# either way; Sivas is the one that silently went wrong.
MUSLIM_RELIGIONS_867 = ("sunni", "shiite")

# CULTURE_COMMENT_NOTES - provinces where vanilla's own trailing comment on the
# culture line contradicts the culture this mod assigns, so the comment is
# qualified instead of left to read as an error. Only one province needs it.
#
# 318 Sugla, i.e. Smyrna: vanilla says "Should not be Greek or Orthodox in 1444.
# Its status as a majority Greek city dates to at least after the 17th Century".
# That is correct for 1444 - the Aydinids took Smyrna around 1330 and made it
# Turkish and Muslim - and irrelevant here. This scenario is 867, when Smyrna was
# Byzantine and Greek. The Saracen fleet that raided it did so in 869, two years
# after the start date, so even that is not yet true at 1444.11.11.
CULTURE_COMMENT_NOTES = {
    318: "# The \"not Greek\" warning below is a 1444 note, not an 867 one. Vanilla\n"
         "# is right about its own date: the Aydinids took Smyrna c. 1330. This\n"
         "# scenario is 867, when it was Byzantine Greek - the Saracen raid on the\n"
         "# city is 869, two years after the start date.",
}


def apply_867_culture(text, pid):
    """Rewrite culture (and religion) for provinces whose vanilla culture is later
    than 867. Culture is rewritten once, at the top-level province block; religion
    is rewritten everywhere it appears, because a dated block that re-sets
    religion would otherwise leave the province Muslim after 1444."""
    m = re.search(r"^(\s*)culture\s*=\s*(\w+)", text, re.M)
    if not m:
        return text
    culture = CULTURE_GONE_867.get(m.group(2))
    if not culture:
        return text
    text = (text[:m.start()]
            + f"{m.group(1)}culture = {culture}"
            + text[m.end():])
    if pid not in CONQUERED_BY_THE_ARABS:
        text = re.sub(rf"^(\s*religion\s*=\s*)({'|'.join(MUSLIM_RELIGIONS_867)})\b",
                      r"\1orthodox", text, flags=re.M)
    note = CULTURE_COMMENT_NOTES.get(pid)
    if note:
        text = text.replace(f"culture = {culture}",
                            f"{note}\n{m.group(1)}culture = {culture}", 1)
    return text

# The rest of the Ottomans, i.e. neither cored nor Anatolian. Ten, all Balkan:
# Tarnovo, Silistria, Nis, Vidin, Plovdiv, Skopje, Kostendil, Tirnovo, Tolcu,
# Ohrid. Vlore used to be here and moved to Byzantium with the rest of Albania.




# vanilla EGY owns nothing at all, so _owned("EGY") would return an empty list.
# The rest of the Ottomans, i.e. neither cored nor Anatolian. Ten, all Balkan:
# Tarnovo, Silistria, Nis, Vidin, Plovdiv, Skopje, Kostendil, Tirnovo, Tolcu,

# ------------------------------------------------------------------ combine --

# Layer 3, in order. A later entry wins any overlap with an earlier one (which is
# why Albania sits after Anatolia and why BYZ_GREECE is last of all). The order
# and the province lists both come from the database now - see Tag.grants and
# Tag.grant_order in tagdb.py, which is where a realm declares what blocks it
# takes and in what precedence.
from tagdb import TRANSFERS  # noqa: E402,F401

LAYER2_MOVES: list = []


def build(verbose=False):
    """{tag: [province ids]} - the whole allocation. The one answer.

    Areas, then loose provinces, then transfers, in that order and only in that
    direction. Filtered to the tags the mod actually hands provinces to, so a tag
    that only appears in a comment or an area list cannot leak into the result.
    """
    LAYER2_MOVES.clear()
    alloc: dict = {}
    owner_of: dict = {}
    overlaps = []

    # Layer 1: areas.
    for tag, areas in AREA_OWNERS.items():
        ids = []
        for area in areas:
            for pid in AREAS.get(area, ()):
                pr = provs.get(str(pid))
                if not (pr and pr.get("owner")):
                    continue
                ids.append(pid)
                if pid in owner_of:
                    overlaps.append((pid, owner_of[pid], tag))
                else:
                    owner_of[pid] = tag
        alloc[tag] = sorted(set(ids))
    if overlaps:
        raise SystemExit(
            "gen_provinces: provinces claimed by two areas, fix AREA_OWNERS: "
            + ", ".join(f"{p} ({a} and {b})" for p, a, b in overlaps))

    # Layer 2: loose provinces, applied after every area so one always beats its
    # area regardless of the order the dict is written in.
    for pid, tag in PROVINCE_OWNERS.items():
        prev = owner_of.get(pid)
        owner_of[pid] = tag
        if prev in alloc:
            alloc[prev] = [p for p in alloc[prev] if p != pid]
        alloc.setdefault(tag, [])
        if pid not in alloc[tag]:
            alloc[tag] = sorted(alloc[tag] + [pid])
        LAYER2_MOVES.append((pid, provs[str(pid)]["name"], prev, tag))

    # Layer 3: transfers. `claimed` deliberately includes the tag's own
    # provinces: the point is to add unclaimed land, never to move land a tag
    # already holds, which is what lets the layers compose with no precedence
    # table.
    for tag, extra in TRANSFERS:
        claimed = set(alloc.get(tag, ()))
        for other in alloc:
            if other != tag:
                claimed |= set(alloc[other])
        alloc[tag] = sorted(set(alloc.get(tag, [])) |
                            {p for p in extra if p not in claimed})

    if verbose:
        for pid, name, prev, tag in LAYER2_MOVES:
            print(f"  override: province {pid} {name} {prev} -> {tag}")
    return {t: sorted(alloc[t]) for t in ALL_TAGS if t in alloc and alloc[t]}


def owner_map(alloc=None):
    """{province id: tag}, for callers asking about one province at a time."""
    alloc = build() if alloc is None else alloc
    return {p: t for t, ps in alloc.items() for p in ps}


# EMPIRE_CORE_AREAS - the land of the 867 Carolingian Empire, defined as geography
# rather than as "whatever five tags happen to hold".
#
# It used to be EMPIRE_KINGDOMS, a list of five tags, which made the empire's extent a
# function of the allocation: move a province between realms and the empire silently
# changed shape. Worse, it made five tags privileged over the other fifteen, and
# Lusatia privileged-in-reverse as the one realm defined by what it was not. This mod
# treats every tag on the same terms, so the empire is described by where it was
# instead of by who holds it.
#
# These 60 areas are the whole Frankish heartland - the 843 Verdun partition and
# everything under it. They contain 237 provinces, of which 11 were never imperial and
# are excluded by name below, leaving the same 226 the tag list used to produce. The
# areas are the unit because a whole area is usually wholly imperial, and the
# exceptions are the interesting part, which is why they are listed rather than
# absorbed.
EMPIRE_CORE_AREAS = (
    "alsace_area", "austria_proper_area", "bourgogne_area", "brabant_area",
    "braunschweig_area", "carinthia_area", "catalonia_area", "central_italy_area",
    "champagne_area", "corsica_sardinia_area", "east_bavaria_area",
    "emilia_romagna_area", "flanders_area", "franconia_area", "frisia_area",
    "guyenne_area", "hesse_area", "holland_area", "ile_de_france_area",
    "inner_austria_area", "languedoc_area", "lazio_area", "liguria_area",
    "loire_area", "lombardy_area", "lorraine_area", "lower_bavaria_area",
    "lower_rhineland_area", "lower_saxony_area", "lower_swabia_area",
    "massif_central_area", "normandy_area", "north_brabant_area",
    "north_rhine_area", "north_westphalia_area", "northern_saxony_area",
    "orleans_area", "palatinate_area", "picardy_area", "piedmont_area",
    "po_valley_area", "poitou_area", "provence_area", "pyrenees_area",
    "romandie_area", "savoy_dauphine_area", "south_saxony_area",
    "switzerland_area", "thuringia_area", "tirol_area", "tuscany_area",
    "upper_bavaria_area", "upper_franconia_area", "upper_rhineland_area",
    "upper_swabia_area", "venetia_area", "wallonia_area", "weser_area",
    "west_burgundy_area", "westphalia_area",
)

# NOT_IMPERIAL_867 - the 11 provinces inside those areas that the 867 empire did not
# hold. Every one is excluded on its own 867 history, never because of who holds it
# now, which is the test that keeps this list from quietly re-encoding the tag
# privileges it replaced. None of them is excluded for being Lusatian, Breton, Venetian
# or anything else; if a province is listed here it is because it was not imperial.
#
#   59 Wittenberg, 61 Dresden, 4744 Zwickau - Saxon and Meissen land, east of the
#       imperial frontier. Thuringia just west of them (Erfurt, Weimar) is inside the
#       empire, so the line runs through the area rather than around it.
#   112 Venezia      - an independent maritime republic by 867, never imperial.
#   118 Roma         - the papal states. The papacy sits outside the empire's own
#   120 Abbruzzi        succession and holds no imperial land.
#   127 Sassari, 2986 Cagliari, 4735 Arborea - Sardinia, independent. Corsica, in the
#       same area, was imperial, which is why 1247 is absent from this list.
#   2965 Vogtland    - Sorbian-held hinterland of Thuringia, not imperial territory.
#       This is a judgement about Vogtland in 867, not about Lusatia: Lusatia holds
#       seven provinces and not one of them is excluded here for that reason.
#   2988 Tarragona   - Catalonia. The empire held it 801-859 and lost it again before
#       this date, so 867 has it outside the empire.
NOT_IMPERIAL_867 = {
    59, 61, 112, 118, 120, 127, 2965, 2986, 2988, 4735, 4744,
}


def empire_core():
    """The provinces the 867 empire held, from EMPIRE_CORE_AREAS minus
    NOT_IMPERIAL_867. Sorted, and the same 226 the old five-tag list produced."""
    core = set()
    for area in EMPIRE_CORE_AREAS:
        for pid in AREAS.get(area, ()):
            if pid not in NOT_IMPERIAL_867 and provs.get(str(pid), {}).get("owner"):
                core.add(pid)
    return sorted(core)


def dev(pid):
    """base_tax + base_production, for the report's balance column."""
    for fn in os.listdir(VANILLA_PDIR):
        if re.match(rf"^{pid}\s*-", fn):
            txt = open(os.path.join(VANILLA_PDIR, fn), encoding="utf-8",
                       errors="replace").read()
            ta = re.search(r"base_tax\s*=\s*([\d.]+)", txt)
            pr = re.search(r"base_production\s*=\s*([\d.]+)", txt)
            return ((float(ta.group(1)) if ta else 0.0)
                    + (float(pr.group(1)) if pr else 0.0))
    return 0.0


START = "1444.11.11"  # the mod's start date


def force_block(new_owner):
    """Dated block that re-asserts our ownership at the start date.

    EU4 fires every dated history entry up to and including the start date,
    in file order, AFTER the undated baseline. Vanilla therefore overrides
    the undated owner/controller for any province it hands over before
    1444.11.11 - Verona to Venice in 1405, Aquitaine to England in 1306,
    Avignon to the Pope in 1274, East Frisia to EFR, and so on. Patching only
    the undated header is not enough, so the province gets a final dated block
    that wins. Appending it last also means we override vanilla, not the
    other way round, and add_core/hre are re-stated because the same pre-1444
    events can drop a core or re-enable the empire flag.
    """
    return (
        f"\n{START} = {{\towner = {new_owner}\n"
        f"\tcontroller = {new_owner}\n"
        f"\tadd_core = {new_owner}\n"
        f"\thre = no\n"
        f"}} # The Karolingians: hold the 867 partition at the 1444 start\n"
    )


def unown(text):
    """Strip owner and controller so the province starts unowned.

    An unowned province is a normal EU4 state, not a trick: 1472 vanilla
    provinces have no owner at all, land included (Grain Coast, Kumasi,
    Pensacola), and their files simply carry no `owner` key. A mod province
    file replaces the vanilla one for that id, so deleting the key is enough.

    Cores are deliberately kept. These three are Hungarian land being parked
    for the Balaton tag, and leaving them HUN-cored means Balaton can inherit
    them without anyone having to remember which provinces they were.
    """
    lines = text.splitlines()
    dated_start = len(lines)
    for idx, ln in enumerate(lines):
        if re.match(r"^\d+\.\d+\.\d+\s*=", ln.strip()):
            dated_start = idx
            break
    out = [ln for idx, ln in enumerate(lines)
           if idx >= dated_start or not re.match(r"^(owner|controller)\s*=", ln.strip())]
    return "\n".join(out) + (
        f"\n# The Karolingians: unowned, held for the Balaton tag\n")


def patch(text, new_owner):
    """Rewrite the start-state (undated) portion of a province file."""
    out, i, n = [], 0, len(text.splitlines())
    lines = text.splitlines()
    # locate end of the undated header: first dated block
    dated_start = len(lines)
    for idx, ln in enumerate(lines):
        s = ln.strip()
        if re.match(r"^\d+\.\d+\.\d+\s*=", s):
            dated_start = idx
            break

    for idx, ln in enumerate(lines):
        if idx >= dated_start:
            out.append(ln)
            continue
        s = ln.strip()
        # --- hre flag -------------------------------------------------
        if re.match(r"^hre\s*=", s):
            out.append(re.sub(r"hre\s*=\s*\w+", "hre = no", ln))
            continue
        # --- owner / controller --------------------------------------
        m = re.match(r"^(owner|controller)\s*=\s*", s)
        if m:
            indent = ln[:len(ln) - len(ln.lstrip())]
            out.append(f"{indent}{m.group(1)} = {new_owner}")
            continue
        # --- add_core: remember existing, append ours at end of header --
        out.append(ln)

    # inject our core just before the first dated block (end of header).
    # Skip it when the vanilla file already grants this core - Morea and
    # Constantinople ship `add_core = BYZ` and are now in the allocation, so
    # without this they would end up with the line twice.
    have_core = any(re.match(rf"^\s*add_core\s*=\s*{re.escape(new_owner)}\s*$", lines[idx])
                    for idx in range(dated_start))
    core_line = f"add_core = {new_owner}"
    if have_core:
        return "\n".join(out) + "\n" + force_block(new_owner)
    # find insertion point: after the last add_core in header, else at end
    ins = dated_start
    last_core = None
    for idx in range(dated_start):
        if re.match(r"^\s*add_core\s*=", lines[idx]):
            last_core = idx
    if last_core is not None:
        ins = last_core + 1
        out.insert(ins, core_line)
    else:
        out.insert(dated_start, core_line)

    return "\n".join(out) + "\n" + force_block(new_owner)


def main(argv):
    alloc = build(verbose="--report" in argv)
    # every allocated province, gifts included - note Venezia is NOT in here:
    # it is deliberately left vanilla so the base game creates it.
    owner_of = {p: t for t, ps in alloc.items() for p in ps}

    # every province that must be written: the partition + every hre=yes
    provs = _PROVDATA["provs"]
    hre_yes = {int(p) for p, pr in provs.items() if pr["hre"]}
    todo = sorted(set(owner_of) | hre_yes | set(BALATON_RESERVED))

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT, exist_ok=True)

    written = 0
    for pid in todo:
        src = None
        for fn in os.listdir(SRC):
            if re.match(rf"^{pid}\s*-.*\.txt$", fn):
                src = os.path.join(SRC, fn)
                break
        if not src:
            print(f"!! no vanilla file for province {pid}")
            continue
        text = apply_867_culture(
            apply_renames(open(src, encoding="utf-8",
                                errors="surrogateescape").read()), pid)
        tag = owner_of.get(pid)
        if pid in BALATON_RESERVED:
            new = unown(text)
        else:
            new = patch(text, tag) if tag else text
        # Global HRE strip at ANY depth: catches the initial flag plus later
        # dated events such as 1464.1.1 East Frisia / 1548.6.26 Flanders that
        # would otherwise re-join the empire long after 1444.
        new = re.sub(r"(\bhre\s*=\s*)yes\b", r"\1no", new)
        open(os.path.join(OUT, os.path.basename(src)), "w",
             encoding="utf-8", errors="surrogateescape").write(new)
        written += 1

    print(f"wrote {written} province files")
    for tag, ps in sorted(alloc.items(), key=lambda kv: -len(kv[1])):
        print(f"  {tag:4} {len(ps):3}")
    print(f"  hre=yes stripped : {len(hre_yes)}")
    print(f"  total            : {len(todo)}")


def report(alloc):
    """Balance report. Writes nothing - the diagnostic half of the pipeline."""
    owner_of = owner_map(alloc)
    caps = {}
    for fn in os.listdir(VANILLA_CDIR):
        if not fn.endswith(".txt"):
            continue
        tag = fn.split(" ")[0].split("-")[0].strip()
        m = re.search(r"^\s*capital\s*=\s*(\d+)", open(
            os.path.join(VANILLA_CDIR, fn), encoding="utf-8",
            errors="replace").read(), re.M)
        if m:
            caps[tag] = int(m.group(1))
    total = 0
    for tag in sorted(alloc, key=lambda t: -len(alloc[t])):
        ids = alloc[tag]
        cap = CAPITAL.get(tag)
        if cap is not None:
            assert cap in ids, f"{tag} capital {cap} not in its own area set!"
        olds = defaultdict(int)
        for pid in ids:
            olds[provs[str(pid)]["owner"]] += 1
        hre = sum(1 for pid in ids if provs[str(pid)]["hre"])
        print(f"{tag} {NAME.get(tag, tag):13} n={len(ids):3} dev={sum(dev(p) for p in ids):6.0f}"
              + (f" cap={cap}({provs[str(cap)]['name']})" if cap else "")
              + f" hre={hre}")
        print("     from: " + " ".join(f"{k}:{v}" for k, v in
                                       sorted(olds.items(), key=lambda x: -x[1])))
        total += len(ids)
    print("=" * 78)
    print(f"{len(owner_of)} provinces reassigned")


if __name__ == "__main__":
    import sys as _sys
    _argv = _sys.argv[1:]
    _alloc = build(verbose="--report" in _argv)
    if "--alloc" in _argv:
        print(json.dumps(_alloc, indent=1, sort_keys=True))
    elif "--report" in _argv:
        report(_alloc)
    else:
        main(_argv)
