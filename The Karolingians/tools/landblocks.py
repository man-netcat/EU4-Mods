#!/usr/bin/env python3
"""The Karolingians - the named land blocks.

A land block is a group of provinces named for the thing it IS rather than for
the tag that ends up holding it: ARABIA_MAMLUK is the Mamluks' land outside
Egypt, BYZ_GREECE is every greek-culture province in the game. The allocation in
gen_provinces.py never spells a bare province list twice - it hands a tag a
block by name.

These blocks used to sit interleaved with two province-FILE text transforms
inside gen_provinces.py, so a tag's land lived in the same file as the code that
writes the map. They are separated here verbatim and unmodified: every value is
computed from the same provdata cache by the same _owned() and _area() helpers as
before, which is checked by comparing every block against the pre-split module.

Writing a new block
-------------------
Use _owned() to take a vanilla tag's holdings resolved AT THE START DATE, and
_area() to take whole areas, so the block says what was asked for instead of
hiding behind bare numbers. Then give it to a tag with Tag(...).grants. Never
hardcode a province id that a vanilla owner or an area already names.

If a block genuinely has to be a one-off list, say why in a comment at the list.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

_PROVDATA = json.load(open(str(CACHE / "provdata.json")))
provs = _PROVDATA["provs"]
AREAS = _PROVDATA["areas"]

# The eastern half of the partition, decided by hand rather than computed,
# because it is a political transfer rather than a share of Carolingian land.
# Order matters: later lists win any overlap with earlier ones, which is why
# Albania sits after Anatolia and why BYZ_GREECE is last of all.
#
# BYZ_CORES    - every province carrying a Byzantium core at 1444.11.11 that
#                Byzantium does not already own.
# BYZ_ANATOLIA - the Ottoman provinces inside vanilla's anatolia_region
#                (map/region.txt -> areas -> map/area.txt). The Ottoman Empire's
#                tag is TUR, not OTT - OTT is Ottawa, and getting that wrong
#                hands Canada to Byzantium.
# BYZ_ALBANIA  - albania_area: Vlore, Lezhe x2, Kruje. Vlore (143) was assigned
#                to Bulgaria in the first pass and is overridden here.
# BYZ_CRIMEA   - Kaffa and Mantrega. Both are Genoese at 1444 (GEN), and the
#                city of Kaffa exists twice: 285 (Genoese) and 2757 (the vanilla
#                KAF tag). "Mantrega" is province 2447, spelled Mantrega in
#                vanilla - it is NOT the MAT tag, which is Matlatzinca in Mexico.
# BYZ_CANDAR   - CND: Kastamonu and Sinop.
# BYZ_TREBIZOND- TRE: Trebizond.
# BYZ_GREECE   - every greek-culture province at 1444.11.11 except Crete, taken
#                from the province files' own `culture` key rather than a region,
#                because vanilla has no greece_region and greek culture is what
#                actually covers the mainland, the Aegean and the Ionian islands.
#                Cyprus (321) is greek-culture and is included on that basis.
#
# CRETE goes to CRT, which already exists in vanilla as "Crete", so releasing it
# needs a province override and nothing else.
BYZ_CORES = [144, 146, 147, 148, 149, 1853, 4699, 4702, 4705, 4779]
BYZ_ANATOLIA = [316, 317, 318, 319, 322, 326, 329, 1846, 1848, 2296, 2297,
                2298, 2299, 2300, 2304, 4308, 4309, 4311, 4312, 4313, 4314,
                4315]
BYZ_ALBANIA = [143, 4174, 4175, 4750]
BYZ_CRIMEA = [285, 2447, 2757]
BYZ_CANDAR = [325, 328]
BYZ_TREBIZOND = [330]
# BYZ_THEODORO - FEO "Theodoro" is an empty vanilla tag in 1444; its only province,
#                2410 Theodoro (Feodosia), is held by TRE and folds in with it.
BYZ_THEODORO = [2410]
# BYZ_SOUTH_ITALY - Apulia (122) and Syracuse (2982), vanilla NAP and SIC. Both
#                  are unclaimed by the partition, so neither conflicts with a
#                  Carolingian realm, and both are defensible Byzantine lands on
#                  an 867 start: Apulia stayed Byzantine into the 9th century and
#                  Bari until c. 840, and Syracuse did not fall to the Arabs
#                  until 878.
BYZ_SOUTH_ITALY = [122, 2982]
# BYZ_KARAMAN    - every province KAR owns at 1444, derived from the owner tag
#                 rather than hand-listed. Hand-listing is what went wrong the
#                 first time: karaman_area holds only 4 of KAR's 7 provinces, the
#                 other three sitting in cukurova_area and germiyan_area, so
#                 "all of Karaman" silently lost Icel (2302). Karaman is KAR,
#                 not KRM - KRM is Crimea.
BYZ_KARAMAN = sorted(int(pid) for pid, pr in _PROVDATA["provs"].items()
                     if pr.get("owner") == "KAR")
BYZ_GREECE = [142, 144, 145, 146, 147, 148, 149, 151, 164, 1773, 1853, 2348,
              3003, 320, 321, 4698, 4699, 4700, 4701, 4702, 4705, 4779]
BYZ_ALL = (BYZ_CORES + BYZ_ANATOLIA + BYZ_ALBANIA + BYZ_CRIMEA + BYZ_CANDAR
           + BYZ_TREBIZOND + BYZ_THEODORO + BYZ_SOUTH_ITALY
           + BYZ_KARAMAN + BYZ_GREECE)
CRETE = [163]
# --- Arabia ----------------------------------------------------------------
# Derived from the 1444 owner data, not hand-listed. "All Mamluk provinces
# outside egypt_region" is a rule about a set, and writing it out by hand is
# exactly how Karaman lost Icel earlier.
#
# ARB is Arabia. It is NOT ARL, which is Ardabil - an easy trap in this family
# of three-letter tags, and one that would have handed the Holy Land to a
# Persian village.
#   ARABIA_MAMLUK  - vanilla MAM outside egypt_region: the Palestine, Transjordan
#                     and Hejaz holdings. The 26 egypt_region Mamluk provinces are
#                     Egypt proper and go to EGY instead - see EGY_ALL below.
#   ARABIA_SYRIA   - all seven SYR provinces, Damascus (the capital) included.
#   ARABIA_RAMAZAN - RAM, i.e. Ramazanoğlu, which is just Adana.
#   ARABIA_DULKADIR- all four DUL provinces.
# Erzincan needs no entry of its own: it is Aq Qoyunlu at 1444, so
# ARABIA_AQ_QOYUNLU covers it. It only looks Timurid if you read the top
# level of the province file and ignore the 1402 block.
#   ARABIA_MEDINA    - MDA, which is a tag and not a province. It owns Medina,
#                     Yanbu and Ma'din Sulaym; hardcoding 384 and calling it "the
#                     Medina tag" left Yanbu and Ma'din Sulaym behind, so it is
#                     derived from the owner like everything else.
#   ARABIA_HOLY_CITIES - MDA's three provinces plus Mecca (385). ARB is a formable
#                     nation that owns nothing and declares `capital = 385`, so
#                     Mecca is required or the start-date check fails.
_AREA_OF = _PROVDATA["area_of"]
_REGION_OF_AREA = _PROVDATA["region_of_area"]


def _owned(tag, region=None, exclude_regions=()):
    """Province ids owned by `tag` at the 1444.11.11 start, filtered by region.

    owner_1444, not the top-level `owner`. The top level of a vanilla province
    file is the state before any dated block fires, and 158 provinces have an
    owner or core change dated inside (867, 1444]. Erzincan is the case in point:
    top level says TIM with add_core = TIM, but a 1402.1.1 block gives it to the
    Aq Qoyunlu and removes the Timurid core. This mod ships no defines.lua, so it
    runs on vanilla's 1444.11.11 start and the resolved value is the true one.
    """
    if isinstance(exclude_regions, str):
        exclude_regions = (exclude_regions,)
    out = []
    for pid, pr in _PROVDATA["provs"].items():
        if pr.get("owner_1444", pr.get("owner")) != tag:
            continue
        reg = _REGION_OF_AREA.get(_AREA_OF.get(pid))
        if region is not None and reg != region:
            continue
        if reg in exclude_regions:
            continue
        out.append(int(pid))
    return sorted(out)


def _region(pid):
    """Region of a province id, via its area. None if the area is unknown."""
    return _REGION_OF_AREA.get(_AREA_OF.get(str(pid)))


def _area(*areas):
    """Province ids belonging to any of the named areas, sorted and de-duped.

    Used where a transfer was specified as "these areas" rather than as a list
    of province ids, so the code says what was asked for instead of hiding it
    behind 17 bare numbers. Province membership comes from provdata's `areas`
    index, which is the same source _owned() reads owners from, so an area and
    the provinces in it can never disagree.
    """
    out = set()
    for area in areas:
        out |= {int(pid) for pid in _PROVDATA["areas"].get(area, ())}
    return sorted(out)


# ARABIA_MAMLUK is the Mamluks' land OUTSIDE Egypt, and it is the only part of
# vanilla MAM that the Abbasids take: Palestine, Transjordan and the Hejaz coast.
# horn_of_africa_region is excluded because Suakin (1232) and Halaib (2324) are
# Red Sea / Beja land which the Mamluks ruled as Sudan, and Egypt kept those two
# when the Mamluks were folded into the EGY tag (see EGY_ALL).
ARABIA_MAMLUK = _owned("MAM", exclude_regions=("egypt_region",
                                              "horn_of_africa_region"))
ARABIA_SYRIA = _owned("SYR")
ARABIA_RAMAZAN = _owned("RAM")
ARABIA_DULKADIR = _owned("DUL")
ARABIA_MEDINA = _owned("MDA")
ARABIA_HOLY_CITIES = ARABIA_MEDINA + [385]
# The short tags do not survive into the game, so these are looked up by their
# real ones: Qara Qoyunlu is QAR (not QQ), Aq Qoyunlu is AKK (not AQ - AQK exists
# as a tag but owns nothing), and Mushasha is MSY (not MSH).
# Haasa is ALH, NOT HAU. HAU is Hausa, which is a West African polity and a
# formable nation owning nothing at 1444. ALH is al-Hasa, the Persian Gulf
# emirate: El Catif, Qatar, Bahrain, Grane and Hofuf.
ARABIA_QARA_QOYUNLU = _owned("QAR")
ARABIA_AQ_QOYUNLU = _owned("AKK")
ARABIA_MUSHASHA = _owned("MSY")
ARABIA_AL_HAASA = _owned("ALH")
# Two Bedouin tags that bridge the two ends of the realm: Fadl holds the Syrian
# Desert (Tadmor/Palmyra, Azraq, Suwaida), which links the Syrian core to Arabia,
# and Anizah holds Al Ula and Jawf, which link the Hejaz to the Syrian Desert.
ARABIA_FADL = _owned("FAD")
ARABIA_ANIZAH = _owned("ANZ")
ARABIA_ALL = (ARABIA_MAMLUK + ARABIA_SYRIA + ARABIA_RAMAZAN + ARABIA_DULKADIR
              + ARABIA_QARA_QOYUNLU + ARABIA_AQ_QOYUNLU + ARABIA_MUSHASHA
              + ARABIA_AL_HAASA + ARABIA_FADL + ARABIA_ANIZAH
              + ARABIA_HOLY_CITIES)

# EGY_ALL - Egypt. For this scenario the Mamluks ARE Egypt, so every province
# vanilla MAM still holds at 1444.11.11 is handed to EGY and the Mamluks tag ends
# up with no land at all. It is derived as "everything vanilla MAM owns that the
# Abbasids are not already taking" on purpose: that keeps EGY_ALL and
# ARABIA_MAMLUK exactly complementary, so the two can never double-book a
# province or drop one if MAM's 1444 holdings are ever re-resolved. Do not
# hardcode 361 Cairo here. EGY is a vanilla formable nation that owns nothing and
# declares `capital = 361`, so Cairo arrives with the rest of Egypt and the
# start-date check still passes.
EGY_ALL = [p for p in _owned("MAM") if p not in ARABIA_MAMLUK]

# ADU_ALL - Andalusia, built from areas rather than a flat province list so the
# intent stays readable and matches how the transfer was specified.
#
# Three sources, all of them vanilla start-date holdings, none of them invented:
#
#   1. Portugal, in full: _owned("POR") -> 13 provinces. This deliberately
#      includes Ceuta 1751 and the Atlantic islands Azores 367 / Madeira 368,
#      because "all of Portugal" means the whole tag, and 367/368 are core-less
#      ocean islands that belong to whoever holds Portugal.
#   2. Granada, in full: _owned("GRA") -> 4 provinces, which is exactly
#      upper_andalucia_area (Almeria, Granada, Gibraltar, Malaga).
#   3. Aragon's *Iberian* provinces only: the 16 of its 25 that sit in
#      iberia_region, dropping Sicily, Malta and Sardinia, which Aragon keeps.
#      This is _owned("ARA") filtered by region, because "Iberian Aragon" is a
#      description of which land is meant, not of the tag's total holdings.
#      Aragon survives as a purely Italian realm.
#   4. Four more areas off Castile, named directly: extremadura_area,
#      toledo_area, lower_andalucia_area and castille_area (South Castile).
#      17 Castilian provinces, cored CAS in every case, and disjoint from the
#      three tags above, so this block adds rather than overlaps.
#
# Together that is 50 provinces: 13 + 4 + 16 + 17, minus six that belong to
# other tags, which leaves Andalusia 45. Note that this drags in
# Cordoba 225, which is
# ADU's vanilla declared capital, so unlike EGY (which needed no capital change
# because Cairo 361 was already inside EGY_ALL) Andalusia keeps vanilla's
# `capital = 225` and it is now genuinely owned. Cordoba staying in Andalusian
# hands is also the whole point of the area list: leaving it to Castile would
# split the Andalusian heartland in half along the Guadalquivir.
#
# Castile keeps the other 16 Iberian provinces (Galicia, Asturias, Leon,
# Biscay, Old Castile, Salamanca, Burgos, Rioja, Palencia, Zamora, Lugo, Vigo,
# Orense) plus the Canaries, so it remains a real kingdom rather than being
# wiped off the map.
#
# ASU_ALL - Asturias. The three areas of the Asturian north-west: Galicia,
# Asturias and Leon, 12 provinces, all of them Castilian at 1444.11.11.
#
# AST IS NOT ASTURIAS. AST is Astrakhan, a Russian steppe horde with its own
# horde government and a 1459 accession block; Asturias is ASU, which is the tag
# already cored on these provinces (206/207/1745/209 carry ASU alongside CAS,
# and the Leon-area ones carry LON). Typing AST here would hand the Asturian
# north to a Kalmyk horde on the lower Volga.
#
# Vanilla ASU is a 6-line formable-style tag with no dated history, no ruler and
# `capital = 207` Asturias, which is inside the transfer, so its declared capital
# arrives with it and no capital override is needed. ASU is not a mod realm and
# gets no country file from the generator: it is listed in ALL_TAGS so
# patch() grants it owner/controller/core at the start date, and a hand-written
# history/countries/ASU.txt supplies the 867 court.
#
# Castile is left with Vizcaya 209 and the Canaries (366, 4565). Rioja 2989 goes
# to ADU via ADU_ALL, Segovia 4789 goes to ASU, and Vizcaya stays Castilian
# because Navarra only takes it in a 1516.1.23 block - at this start date it is
# still a Castilian province.
ASU_ALL = _area("galicia_area", "asturias_area", "leon_area") + [4789]

# Segovia 4789 is added on top of the three areas, and removed from ADU_ALL above.
# It arrives here from outside those areas: 4789 sits in castille_area, so the
# area lists alone would give it to Andalusia. Asking for it by id is the only
# way to say "this one province of an Andalusian area is Asturian".
#
# The province is a genuine exclave. Burgos 1746, the nearest province of
# Asturias's own land, is between Segovia and everything ASU holds, and Burgos
# is itself Andalusian (it comes in via asturias_area). So ASU ends up with 13
# provinces, 12 of them one connected block and Segovia hanging off the south.
# That is the requested map, recorded here so it is not mistaken for a bug.

# ADU is a vanilla formable nation with zero cores anywhere in the map, so the
# transfer has to add an ADU core to all 60. That is what patch() does for
# every hand-written list.
#
# Rioja 2989 is added separately and by id rather than through basque_country.
# It is the one province of the Basque area that is neither Basque land to keep
# nor Asturian, and it is asked for by name. basque_country is deliberately not
# used: it would drag in Vizcaya 209 and Navarra 210, and Navarra is the NAV
# realm this mod gifts separately (see ALL_TAGS), so the two lists would
# fight over one province.
ADU_ALL = sorted(
    set(_owned("POR")
        + _owned("GRA")
        + [p for p in _owned("ARA") if _region(p) == "iberia_region"]
        + _area("extremadura_area", "toledo_area", "lower_andalucia_area",
                "castille_area")
        + [2989]
        # Five provinces are subtracted because they belong to somebody else, and
        # one because of Segovia:
        #
        #   197 Roussillon, 212 Girona, 213 Barcelona, 2987 Urgell -> FRA
        #   211 Huesca (Pirineo)                                  -> NAV
        #
        # All five are Catalan or Aragonese, so the area shorthands above sweep
        # them into Andalusia, but PROVINCE_OWNERS gives them to West Francia and
        # Navarre instead. They are subtracted here rather than left to the
        # transfer's "never take land another tag already holds" rule, because that
        # rule made the outcome depend on statement order: ADU_ALL read as 50
        # while the mod has always given Andalusia 45, and nothing recorded that.
        # Naming them makes ADU_ALL itself 45.
        #
        #   4789 Segovia -> ASU. One of the four provinces of castille_area, so the
        # area shorthand puts it in Andalusia, but Asturias asks for it - see
        # ASU_ALL. Written as an explicit subtraction rather than by trimming the
        # area list, because "castille_area minus Segovia" is the actual rule, and
        # hiding the exception inside the area name would make the next reader
        # believe the whole area is Andalusian. sorted(set(...)) because set
        # arithmetic needs a set, not a list.
        ) - {197, 211, 212, 213, 2987, 4789})

# The Mamluks ARE Egypt here, so every surviving reference to the MAM tag in a
# copied province file becomes a reference to EGY. This has to rewrite the copied
# vanilla history, not just the start-date block we append, or the Mamluks come
# back from the dead: vanilla's 1770.1.1 block hands Yanbu, Medina, Mecca, Tabuk,
# Ma'din Sulaym and Al Wajh to MAM, which would resurrect a separate Mamluks
# country in 1770 and take the Hejaz straight back off the Abbasids. The
# 1510.1.1 and 1517.1.1 blocks that strip the Mamluk core turn into Egyptian core
# changes instead, which is what actually happened to Egypt in 1517.
#
# A blanket word-boundary substitution is safe here, and was checked before being
# used: all 28 Egyptian provinces already carry an EGY core from vanilla, so no
# province ends up with a duplicated one; no dated block both adds and removes a
# MAM core, which is the case that would turn into the nonsense "add_core = EGY
# remove_core = EGY"; no block already carries both cores; and MAM appears in
# these files nowhere except as one of the six tag keys add_core, remove_core,
# owner, controller, discovered_by and add_claim. Comments spell the dynasty out
# as "Mamluks" and are deliberately left alone.
#
# Note that _owned("MAM") above is NOT one of these references and must stay MAM:
# it reads the vanilla owner to find out which provinces the Mamluks held, and
# vanilla EGY owns nothing at all, so _owned("EGY") would return an empty list.
TAG_RENAMES = {"MAM": "EGY"}



BUL_REST = [150, 159, 1765, 2746, 2750, 3001, 4703, 4704, 4706, 4780]
# BUL_CORES - provinces vanilla already cores to BUL, which BUL_REST deliberately
#             excludes (that list is the *uncored* Ottoman remainder). Burgas is
#             one of them and would otherwise have stayed Ottoman.
BUL_CORES = [1764]
# BUL_BUDJAK   - Budjak (1756), vanilla MOL. Taken because an 867 Bulgaria holds
#                the Danube steppe after the Bulgar conquest of Moldavia, and
#                because vanilla already treats the province as Danubian.
BUL_BUDJAK = [1756]
# BUL_WALLACHIA - all five WAL provinces at 1444: Oltenia, Tirgoviste, Buzau,
#                 Giurgiu, Severin.
BUL_WALLACHIA = [160, 161, 2998, 4531, 4532]
# BUL_SERBIA - Serbia proper, i.e. all seven vanilla SER provinces, plus Syrmia,
#              the one Hungarian province of serbian culture and so the only
#              "Serbian Hungarian" land in the 1444 data (slavonia_area).
#              Nis (3000) already sits in BUL_REST; the union makes that harmless.
BUL_SERBIA = [141, 1766, 1827, 3000, 4173, 4176, 4239, 4757]
# The rest of the Hungarian Basin to Bulgaria - everything HUN held in 1444
# except the three below and the five slovakia_area provinces that Great Moravia
# keeps. Pest, Bekes, Temes, Bihar, Maros, Hunyad, Maramaros, Szabolcs, Torontal,
# Szolnok, Bacs, Turda, Kiralyfold.
BUL_HUNGARY_BASIN = [153, 155, 156, 157, 158, 1951, 1952, 1953, 1954, 4125, 4126,
                     4127, 4128]
# Sopron, Fejer and Somogy are parked unowned until the Balaton tag is built.
BALATON_RESERVED = [135, 1864, 4240]
# HUN is renamed "Mogyers" (localisation/replace/countries_l_english.yml) and
# given the pre-migration Magyar homeland of the Levedia tradition: the Podolia /
# Dnieper LEEDIA land and the Crimean-steppe Kuban area. It does NOT get the
# Carpathian Basin, because this mod's premise is a Carolingian 867 - before the
# Magyar migration - so the Basin is still theirs to lose, and its 1444 holdings
# are redistributed on CK3 evidence instead (see the next comment).
#   4540 Winnica, 1944 Cherkasy, 1943 Bratslav - ruthenian, vanilla LIT
#   282 Yedisan, 2406 Ingil, 283 Zaporozhia    - crimean,  vanilla CRI
# Hungary's old 1444 provinces are deliberately NOT taken here. They are
# redistributed instead: the Basin to Bulgaria (BUL_HUNGARY_BASIN), the five
# slovakia_area ones to Great Moravia (PROVINCE_OWNERS, 154/162/1318/1772/4236),
# and Sopron/Somogy/Fejer parked unowned for Balaton (BALATON_RESERVED).
MOGYERS_LEVIDIA = [282, 283, 2406, 1943, 1944, 4540]
# Capital of the Magyar homeland tag is 283 Zaporozhia, on CK3's evidence rather
# than taste: CK3 names its Pontic Steppe title cn_etelkoz in Hungarian - Etel/Edil
# being the confederation the Levedia tradition derives the Magyars from - and
# cn_zaporizhia in Russian, for the same title
# (common/landed_titles/00_landed_titles.txt, capital c_odessa). CK3's own
# k_magyar capital is c_visegrad/Pest, but that is the settled Carpathian kingdom
# this mod hands to Balaton, not the homeland.
# CRI_AZOV - 286 Azow, the last Genoese province in the Azov basin, handed to
#            Crimea now that its two Black Sea Genoese ports are Byzantine.
CRI_AZOV = [286]
# MON_ADRIATIC - Zeta (138) and Kotor (4754). Zeta is already vanilla MON and is
#               MON's capital (Zabljak), so it only needs restating here for
#               check_start to assert it; Kotor is Venetian at 1444 and is the
#               actual transfer, giving Montenegro the Bay of Kotor.
MON_ADRIATIC = [138, 4754]
# DAL_CORE     - Dalmatia (136, its capital at Split) and Zadar (4753). Both are
#               already vanilla DAL, so this restates them purely so check_start
#               asserts the capital; nothing actually changes hands.
DAL_CORE = [136, 4753]
BUL_ALL = (BUL_REST + BUL_CORES + BUL_BUDJAK + BUL_WALLACHIA
           + BUL_SERBIA + BUL_HUNGARY_BASIN)
