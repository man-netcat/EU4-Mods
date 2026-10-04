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
# Together that is 50 provinces: 13 + 4 + 16 + 17. Note that this drags in
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
        # Segovia 4789 is subtracted from ADU. It is one of the four provinces
        # of castille_area, so the area shorthand puts it in Andalusia, but it is
        # asked for by Asturias instead - see ASU_ALL. Written as an explicit
        # subtraction rather than by trimming the area list, because
        # "castille_area minus Segovia" is the actual rule, and hiding the
        # exception inside the area name would make the next reader believe the
        # whole area is Andalusian. sorted(set(...)) because set arithmetic needs
        # a set, not a list.
        ) - {4789})

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


def apply_renames(text):
    for old, new in TAG_RENAMES.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return text
# The rest of the Ottomans, i.e. neither cored nor Anatolian. Ten, all Balkan:
# Tarnovo, Silistria, Nis, Vidin, Plovdiv, Skopje, Kostendil, Tirnovo, Tolcu,
# Ohrid. Vlore used to be here and moved to Byzantium with the rest of Albania.
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
# Dnieper LeEDIA land and the Crimean-steppe Kuban area. See the notes in
# partition.py for why those six and not the Carpathian Basin.
#   4540 Winnica, 1944 Cherkasy, 1943 Bratslav - ruthenian, vanilla LIT
#   282 Yedisan, 2406 Ingil, 283 Zaporozhia    - crimean,  vanilla CRI
# Hungary's old 1444 provinces are deliberately NOT taken here. They are
# redistributed instead: the Basin to Bulgaria (BUL_HUNGARY_BASIN), the five
# slovakia_area ones to Great Moravia (partition.py), and Sopron/Somogy/Fejer
# parked unowned for Balaton (BALATON_RESERVED).
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
        text = apply_renames(open(src, encoding="utf-8",
                                  errors="surrogateescape").read())
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
