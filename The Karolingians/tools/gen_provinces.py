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

AREA_OWNERS = {
    # Reconstructed as the settlement of c.867, after Lothair I had split his
    # own share in 855 (Lotharingia to Lothair II, Italy to Louis II) and after
    # the Treaty of Prum had handed Brittany to Charles the Bald in 865.
    # brittany_area is deliberately NOT listed: Brittany is left free. Its five
    # provinces (Armor, Finistere, Vannetais, Vendee, Rennes) are vanilla BRI
    # -owned and BRI-cored with no HRE flag and no cores anywhere else, so
    # simply not claiming the area hands Brittany back all of its cores intact.
    # CK3 treats it as its own kingdom in 867 (k_brittany :: ##d_brittany),
    # which is also how it plays here - an independent Breton tag with its own
    # 1444 ruler, rather than a West Frankish province.
    "FRA": {  # West Francia - Charles the Bald, King of the Franks
        # Septimania (Toulouse, Languedoc, Carcassonne) and Aquitaine. NOT
        # Provence/Dauphine, which were still Lotharingian, and NOT Brittany.
        "ile_de_france_area", "normandy_area", "loire_area",
        "orleans_area", "poitou_area", "guyenne_area", "languedoc_area",
        "massif_central_area", "pyrenees_area", "champagne_area", "picardy_area",
        # West Burgundy is West Frankish: everything west of the Saone. CK3
        # agrees on the one county it places - c_nevers under k_france ::
        # ##d_burgundy - and Charolais and Auxerrois have no CK3 867 entry at
        # all, so they follow their area west of the river. Dijon is NOT taken
        # by the area, because it sits east of the Saone with the rest of
        # bourgogne_area; it is taken as a per-province override below, where
        # CK3's c_dijon is the evidence.
        "west_burgundy_area",
        # Catalonia minus Tarragona. The Catalan counties were Frankish: they sit
        # inside the Spanish March and Belesarius - sent by Charles the Bald -
        # held Barcelona and Girona as marcher counts. catalonia_area is NOT
        # claimed as a whole because Tarragona (2988) stays with Aragon, so
        # these four are per-province overrides instead. Aragon keeps the rest
        # of its 867 holdings untouched.
        #   197 Roussillon (Rosello), 212 Girona, 213 Barcelona, 2987 Urgell
        # Flanders is West Frankish in CK3 867: k_france.txt :: ##d_flanders
        # holds c_brugge, c_yperen, c_ypres, c_guines, c_lille, c_boulogne and
        # barony CALAIS. It is one of Lothair II's two shortest frontiers and
        # never his - Louis the German held it as a buffer against the Franks.
        "flanders_area",
    },
    "LOT": {  # Lotharingia - Lothair II, middle kingdom, capital Aachen
        # Lotharingia proper (Low Countries, Moselle, Rhine) plus Upper
        # Burgundy and the Kingdom of Provence/Arles, all held until 875.
        "lower_rhineland_area", "lorraine_area", "alsace_area",
        "wallonia_area", "brabant_area", "north_brabant_area",
        "holland_area", "frisia_area", "bourgogne_area",
        "romandie_area", "savoy_dauphine_area",
    },
    "GER": {  # East Francia - Louis the German
        # Saxony, Thuringia, Hesse, the Rhineland, East Franconia and Alemannia
        # (Swabia + the Alemannic Swiss plateau), which Louis was seizing from
        # 857 onward and held outright by the 870s.
        "hesse_area", "upper_rhineland_area", "palatinate_area",
        "north_rhine_area", "westphalia_area", "north_westphalia_area",
        "weser_area", "lower_saxony_area", "braunschweig_area",
        "thuringia_area", "northern_saxony_area",
        "lower_swabia_area", "upper_swabia_area", "switzerland_area",
        # Transjurania is NOT taken East. CK3 lumps it into k_burgundy, but the
        # 867 start sits inside the Burgundian succession crisis: Rudolf II was
        # deposed by Charles the Bald and Louis the German, and the Treaty of
        # Meerssen (869) is still two years away. This mod leaves the 867
        # county-level reading alone instead: Bern, Fribourg, Valais and
        # Freiburg stay with romandie_area in Lotharingia, and Geneva goes
        # further still, to Italy, on its own override below. switzerland_area
        # (Zurich, Schwyz, St Gallen, Chur, Illanz) is here, which CK3 confirms
        # in ##d_currezia -> k_east_francia.
        "franconia_area", "upper_franconia_area",
    },
    "BAV": {  # Bavaria - Carloman, granted his own appanage in 855
        # Bavaria proper, the Nordgau/Regensburg, the Austrian march, Tyrol,
        # Carinthia and the Carantanian march. NOT Swabia or Franconia: those
        # were East Frankish. Bayreuth (Nordgau) is Bavarian but shares EU4's
        # upper_franconia_area with clearly East Franconian provinces.
        "upper_bavaria_area", "lower_bavaria_area",
        "east_bavaria_area", "tirol_area", "austria_proper_area",
        "inner_austria_area",
    },
    "ITA": {  # Kingdom of Italy - north only, Pavia
        "lombardy_area", "piedmont_area", "po_valley_area", "liguria_area",
        "venetia_area", "emilia_romagna_area", "tuscany_area",
        # Provence and the Istrian coast, both pulled off their previous
        # holders. provence_area was Lotharingian under Lothair II, but the
        # Kingdom of Italy under Louis II reached to the Mediterranean here,
        # and Provence is culturally and geographically Mediterranean. For
        # carinthia_area - EU4's Slovenian area, which actually contains
        # Carniola's Krain and Cilli rather than being Carinthia - Italy takes
        # Istria, Gorz and Trieste, the old Patriarchate of Aquileia coast, but
        # NOT Krain and Cilli, which stay Bavarian; see the overrides below.
        "provence_area", "carinthia_area",
    },
    "SOR": {  # Lusatia - a free Sorbian principality, not a Carolingian realm
        # Lusatia proper is the one part of the map with no 867 claimant in
        # this partition: the Sorbs were tributary to whoever held the
        # neighbouring marches and are given their own land here. CK3 has no
        # Sorbian kingdom at all, so this area is a mod decision rather than a
        # reading of k_*.txt - it takes the three vanilla-BOH provinces, which
        # are SOR-cored and already Sorbian in culture, off Bohemia.
        "lusatia_area",
        # South Saxony only - the area Wittenberg sits in. Northern Saxony
        # (Magdeburg, Anhalt, Goslar) and Lower Saxony (Hamburg, Luneburg,
        # Lauenburg, Celle) both stay East Frankish.
        "south_saxony_area",
    },
}

# Provinces carved back out of their area's tag, keyed province id -> tag.
# EU4 areas straddle 867 borders, so these are the provinces the area-level

PROVINCE_OWNERS = {
    # Venice keeps its own namesake province. It cores it in vanilla, so it
    # needs no new country file and survives as a maritime republic; the rest
    # of its 1444 holdings inside northern Italy - Treviso, Padova, Ravenna -
    # fold into the Kingdom of Italy. Its overseas provinces (Corfu, Athens,
    # Crete, Euboea, Durres, Kotor) lie outside all 57 areas, untouched.
    112: "VEN",
    # Geneva and Savoie go to Italy, breaking both of their areas out. Neither
    # is a Neustrian or Lotharingian province at all - CK3 files c_geneva and
    # c_savoie under k_burgundy :: ##d_savoie, the Alpine kingdom straddling
    # the Pennine and Graubunden passes - and the mod gives the Alpine west to
    # Italy, which by 867 already reaches the Ligurian and Provencal coast.
    # So Geneva leaves romandie_area (Bern, Fribourg and Wallis stay
    # Lotharingian) and Savoie leaves savoy_dauphine_area (Lyonnais, Dauphine
    # and Annecy stay Lotharingian). This supersedes the earlier Transjurania
    # reading, which sent Geneva East Francia at the Meerssen line.
    4720: "ITA",    # Geneva
    205: "ITA",     # Savoie
    # NOT moved, though CK3 disagrees: 1867 Freiburg is k_east_francia ::
    # ##d_alsace, so East Francian, while Bern/Fribourg/Wallis have no decisive
    # 867 precedent and stay with the area. Say the word and Freiburg goes
    # East Francia.
    # NOT overridden, deliberately: 203 Lyonnais and 204 Dauphine. An earlier
    # pass gave them to France because they are FRA-cored in vanilla, but CK3
    # puts c_lyon squarely in k_burgundy :: ##d_dauphine alongside c_vienne and
    # the rest of the Dauphine, so both belong to the Kingdom of Burgundy and
    # therefore to Lotharingia in this mod. They keep their vanilla FRA cores,
    # so France can still reconquer them. Within savoy_dauphine_area only
    # Savoie (205) leaves for Italy; Lyonnais, Dauphine and Annecy stay LOT.
    # lower_rhineland_area also holds Trier and Koblenz. The Moselle was East
    # Frankish under Louis the German, while Aachen (Lothair II's capital) and
    # Julich stayed Lotharingian - so the area is split rather than left whole.
    80: "GER",     # Trier
    1760: "GER",   # Koblenz
    # Koln and Berg are Lotharingian, not East Frankish. CK3 puts both
    # counties in k_lotharingia proper - c_cologne and c_berg sit alongside
    # c_aachen and c_julich in d_rhine, k_lotharingia - and the 867 partition
    # left the lower Rhine with Lothair II. Koln was also never Louis the
    # German's seat, so East Francia's capital moves to Frankfurt (1876).
    85: "LOT",     # Koln
    84: "LOT",     # Berg
    # Nice was a county of Provence until 1388. Now that provence_area is
    # Italian, Nice goes with it and its area, so the override is gone and it
    # lands in liguria_area with Genoa and Albenga.
    # Trent, on the other hand, is carved out of tirol_area and goes Italy:
    # the Bishopric of Trent was Italian-facing and linked to the Lombard
    # kingdom, while Tirol proper stays Bavarian.
    110: "ITA",     # Trent      (tirol_area; vanilla TNT)
    # Dijon (Dijonnais) goes to West Francia, breaking bourgogne_area open.
    # The Saone was the 867 line between West and Upper Burgundy, and the area
    # split follows it: Nevers, Charolais and Auxerrois west of the river are
    # already FRA via west_burgundy_area, while Franche-Comte and Salins east of
    # it stay Lotharingian. An earlier pass took that geography as final and left
    # Dijon with the rest of its area, which made it the single province where the
    # mod parted from CK3. It no longer does:
    #   k_france.txt :: ##d_burgundy holds c_dijon in 867, and its holder is
    #   Raoul (CK3 character 303420, dynasty 743, Robertine) - a West Frankish
    #   count under Charles the Bald, not a Lotharingian one.
    # Nothing else in bourgogne_area moves: only this one province changes hands.
    192: "FRA",     # Bourgogne (Dijon)  (bourgogne_area; vanilla BUR)
    # Vogtland goes to Lusatia with the Sorbian lands, carved out of
    # thuringia_area: Plauen and Zwickau were the two halves of the
    # Sudeten/Voigtland march that kept one foot in each sphere.
    2965: "SOR",   # Vogtland   (thuringia_area; vanilla THU)
    # Leipzig leaves Lusatia for East Francia. south_saxony_area is otherwise
    # Sorbian, and CK3 backs that: b_wittenberg, b_dresden, b_gorlitz,
    # b_bautzen, b_meissen, b_plauen and b_gera all sit under k_sorbia (the
    # kingdoms holding d_lausitz and d_meissen), which is the direct analogue of
    # Lusatia here. Leipzig is the exception - b_leipzig belongs to
    # c_mersenburg, which CK3 files under d_anhalt inside k_east_francia,
    # alongside Halle and Magdeburg. So the area splits: Merseburg's
    # hinterland is East Frankish, the Meissen/Lausitz block is Sorbian.
    62: "GER",     # Leipzig (Leipzig)  (south_saxony_area; vanilla THU)
    # Catalonia minus Tarragona, carved out of catalonia_area for West Francia.
    # Barcelona, Girona, Urgell and Roussillon (Rosello) were Frankish marcher
    # counties; Tarragona (2988) is left with Aragon. Claimed one by one
    # because only these four change hands - the area as a whole does not.
    197: "FRA",     # Roussillon (Rosello)  (catalonia_area; vanilla ARA)
    212: "FRA",     # Girona                 (catalonia_area; vanilla ARA)
    213: "FRA",     # Barcelona              (catalonia_area; vanilla ARA)
    2987: "FRA",    # Urgell                 (catalonia_area; vanilla ARA)
    # Vizcaya and Huesca (Osca) to Navarra. Biscay was a Basque county under
    # Navarre's sphere, and Huesca came with the Sobrarbe/Appalachian march that
    # straddled the Pyrenees. Both are carved out one at a time because neither
    # area changes hands as a whole - Navarra's own province (210) and Rioja
    # (2989) stay put, and Aragon keeps the rest of aragon_area. NAV is a
    # vanilla tag, so it needs no country file from this mod.
    209: "NAV",     # Vizcaya (Giscaya)   (basque_country; vanilla CAS)
    211: "NAV",     # Huesca  (Osca)      (aragon_area;     vanilla ARA)
    # silesia_area changes hands entirely but splits down the middle: the
    # Breslau/Liegnitz/Glogau west goes to Silesia, the Opole/Ratibor east to
    # Great Moravia. Note that file names and in-game names diverge here - the
    # player sees Wroclaw, Legnica and Glogow, and the game stores those as
    # "Breslau", "Liegnitz" and "Glogau".
    264: "SIL",     # Breslau (Wroclaw)    (silesia_area; vanilla OPL)
    4238: "SIL",    # Liegnitz (Legnica)   (silesia_area; vanilla GLG)
    2966: "SIL",    # Glogau   (Glogow)    (silesia_area; vanilla GLG)
    4723: "GMA",    # Opole                (silesia_area; vanilla OPL)
    263: "GMA",     # Ratibor  (Racibor)   (silesia_area; vanilla OPL)
    # Great Moravia takes the whole of moravia_area - Brno, Olomouc and
    # Ostrava - giving it a real Moravian heartland instead of existing only as
    # a formable nation. GMA is vanilla, so again no country file is needed.
    265: "GMA",     # Brno                 (moravia_area; vanilla BOH)
    4237: "GMA",    # Olomouc              (moravia_area; vanilla BOH)
    4726: "GMA",    # Ostrava              (moravia_area; vanilla BOH)
    # ...and the whole of slovakia_area, so Great Moravia starts as a real
    # landholder rather than a formable name. There is no nitra_area in EU4
    # 1.37 and no province called Nitra; slovakia_area is the region meant, and
    # it holds five: Hont, Zemplen, Spis, Pozsony and Trencin. Spis and Zemplen
    # are Ruthenian rather than Slovak, but they are the eastern half of the
    # same Slovak march lands, so they go over as a block.
    154: "GMA",     # Hont                 (slovakia_area; vanilla HUN)
    162: "GMA",     # Zemplen              (slovakia_area; vanilla HUN)
    1318: "GMA",    # Spis                 (slovakia_area; vanilla HUN)
    1772: "GMA",    # Pozsony              (slovakia_area; vanilla HUN)
    4236: "GMA",    # Trencin              (slovakia_area; vanilla HUN)
    # Bayreuth sat in the Nordgau around Regensburg, which was Bavarian. Its
    # area-mates (Bamberg, Nuremberg, Coburg) are East Franconian, hence the
    # split.
    4717: "BAV",   # Bayreuth
    # East Swabia is NOT one realm in 867. CK3 splits it, and so does this mod:
    #   k_east_francia.txt :: ##d_swabia   -> c_ulm, c_grunningen, c_wurttemberg,
    #                                          c_baden, c_zollern, c_hohenberg
    #   k_bavaria.txt      :: ##d_augsburg -> c_augsburg, c_kempten (barony
    #                                          Memmingen), c_ravensburg,
    #                                          c_burgau, c_alpsee
    # So the Augsburg group is Bavarian and stays GER only where CK3 says East
    # Francia. Upper Swabia therefore splits, and Bregenz (barony of
    # c_ravensburg, d_augsburg) is Bavarian too - it is already BAV via
    # tirol_area, which agrees with d_tyrol also sitting under k_bavaria.
    1868: "BAV",   # Augsburg   (CK3 c_augsburg  -> d_augsburg -> k_bavaria)
    68: "BAV",     # Memmingen  (CK3 barony Memmingen -> c_kempten -> d_augsburg)
    # --- West Francia / Lotharingia: the two directions CK3 corrects ---------
    # To Lotharingia, out of West Francia: the County of Verdun. CK3 files
    #   187 Barrois (Bar)   c_bar   -> d_bar
    #   4766 Verdun          c_verdun -> d_bar
    # under k_france, but that is an anachronism: in 867 Bar and Verdun were
    # Lotharingian, held by Lothair I and then Lothair II, and only became
    # securely West Frankish after Lothair II's death in 869. So lorraine_area
    # goes whole to LOT, joining Metz and Lothringen (c_metz / c_nancy under
    # d_upper_lorraine, k_lotharingia). The Ardennes follow suit: EU4's only
    # land province there is 94 Luxemburg, in wallonia_area, and CK3 places
    # c_luxembourg under d_luxembourg in k_lotharingia - so it is already LOT.
    # West Burgundy (Nevers, Charolais, Auxerrois) goes the other way to France
    # while the rest of bourgogne_area - Dijon, Franche-Comte, Salins, all east
    # of the Saone - stays Lotharingian; see west_burgundy_area above.
    # To Lotharingia, out of France - the "vice versa" half:
    #   1743 Cambray  c_cambray -> d_brabant -> k_lotharingia
    # CK3 puts Cambrai in d_brabant with Hainaut and Antwerpen, so it is
    # Lothair II's even though it sits inside the Picardy area next to France.
    1743: "LOT",    # Cambray
    # --- Central Italy: Lazio and Umbria, plus Ancona and Urbino -------------
    # In 867 there is no Papal State to speak of, so the Patrimony goes to the
    # Lombard Kingdom of Italy under Louis II rather than sitting with the
    # Pope. Urbino was part of that Patrimony long before the deluge of
    # Montefeltro donations that made it a papal fief, so it goes over too.
    # Rome and the Abruzzi are carved back out below and stay as they are.
    2976: "ITA",    # Umbria     (lazio_area; vanilla PGA)
    4731: "ITA",    # Spoleto    (lazio_area; vanilla PAP)
    4732: "ITA",    # Terracina  (lazio_area; vanilla PAP)
    119: "ITA",     # Ancona     (central_italy_area; vanilla PAP)
    2977: "ITA",    # Urbino    (central_italy_area; vanilla URB)
    # Corsica still rode with the Lombard duchy of Tuscany in 867, a century
    # before Pisa and Genoa started wrangling over it, so it follows Italy
    # rather than staying with Genoa (1247 Corsica, vanilla GEN).
    1247: "ITA",    # Corsica    (corsica_sardinia_area; vanilla GEN)
    # carinthia_area is EU4's Slovenian area, not Carinthia: it holds Carniola
    # proper (Krain, Cilli) plus the Aquileian coast (Istria, Gorz, Trieste).
    # The area goes to Italy, but Carniola is carved back out and stays
    # Bavarian, since the Heptarchy was Frankish and Lotharingian, never
    # Italian, in 867.
    129: "BAV",    # Krain      (carinthia_area; vanilla HAB)
    4751: "BAV",    # Cilli      (carinthia_area; vanilla CLI)
# Deliberately NOT taken: 118 Roma (the Patrimony itself, left papal),
    # 120 Abbruzzi (vanilla NAP - Abruzzo is not papal and stays with Naples,
    # so this keeps the earlier "southern Italy untouched" rule intact).
    # 2977 Urbino WAS taken, to Italy - see the central Italy block above.
    # Bregenz (4710) and Bayreuth (4717) were re-checked against CK3 and
    # already sit correctly:
    #   4710 Bregenz  barony BREGENZ   -> c_ravensburg -> d_augsburg -> k_bavaria
    #   4717 Bayreuth barony BAYREUTH  -> c_parsberg   -> d_nordgau  -> k_bavaria
    # Savoie (205) and Geneva (4720) read the same way in CK3, but both are
    # overridden to Italy rather than folded into Lotharingia:
    #   205 Savoie    c_savoie, barony Annecy/Aosta -> d_savoie -> k_burgundy
    #   4720 Geneva   barony GENEVE     -> d_savoie -> k_burgundy
    # CK3 files West Burgundy (d_provence, d_savoie, d_dauphine, d_upper_burgundy,
    # d_transjurania) under k_burgundy, which this mod folds into Lotharingia.
    # Donauworth (4711), St Gallen (1870) and Illanz (4722) have no CK3 867
    # entry at all, so they stay with their area.
}

CAPITAL = {"FRA": 183, "LOT": 1878, "GER": 1876, "BAV": 65, "ITA": 4728, "SOR": 60}
NAME = {"FRA": "West Francia", "LOT": "Lotharingia", "GER": "East Francia",
        "BAV": "Bavaria", "ITA": "Italy", "SOR": "Lusatia"}


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
# why Albania sits after Anatolia and why BYZ_GREECE is last of all).
TRANSFERS = (
    ("BYZ", BYZ_ALL),
    ("BUL", BUL_ALL),
    ("CRT", CRETE),
    ("HUN", MOGYERS_LEVIDIA),
    ("CRI", CRI_AZOV),
    ("MON", MON_ADRIATIC),
    ("DAL", DAL_CORE),
    ("ARB", ARABIA_ALL),
    ("EGY", EGY_ALL),
    ("ADU", ADU_ALL),
    ("ASU", ASU_ALL),
)

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
