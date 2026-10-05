#!/usr/bin/env python3
"""The Karolingians - the tag database.

One Tag object per realm this mod maintains. Everything the generators need to
know about a realm is an attribute of that realm: what it is called, how big it
is, where its land is, which CK3 title its ruler comes from, and why. Adding a
realm means adding one object to TAGS, not editing six tables in four scripts.

Why this exists
---------------
The same fact used to be spelled out separately in modtags.py, gen_provinces.py,
gen_countries.py, ck3ruler.py and validate.py. Five copies is four ways to be
wrong, and the copies had already drifted - gen_countries.py still treated
Lusatia as a partition kingdom while the mod's own localisation had always
described a five-kingdom empire with Lusatia outside it, and a realm that
appeared in the allocation but not in ck3ruler's TITLES or NOT_CK3 was
unclassifiable without anyone noticing.

What a Tag is NOT
-----------------
A Tag is a realm this mod is RESPONSIBLE FOR: one it keeps a country file, a
rank and a court for. That is not the same as a tag that appears in the
allocation. Vanilla leftovers this mod deliberately does not touch - Brittany,
Venice, the other electors - are not Tags and are not tracked here. They hold
land and that is fine; the mod has no opinion about them.

The two axes that are easy to confuse
--------------------------------------
    managed   this mod keeps a realm for it: country file, rank, court, audit
    in_alloc  the allocation may hand it a province

VEN is in_alloc but not managed - it keeps its namesake province and survives as
a maritime republic with vanilla's ruler. BOH is managed but not in_alloc - the
mod never reassigns its land, it just maintains a court for it. Both are
ordinary, and conflating them is how Lusatia ended up defined by what it was
not.

Field notes
-----------
    rank      EU4 government_rank: 1 duchy/principality, 2 kingdom, 3 empire.
              Every rank is argued from the realm's own 867 standing, never from
              which group a tag was filed under.
    capital   Province id, or None to keep vanilla's own seat.
    culture   Primary culture for a from-scratch country file.
    ck3_title The CK3 title whose 867 holder supplies the ruler's name and
              dynasty. None means CK3 is not the authority - see no_ck3.
    grants    Named land blocks from landblocks.py that this tag takes.
    deferred  Why no country file is written yet, or None.

What is not here yet
--------------------
The per-province overrides and the area lists still live in gen_provinces.py,
where their justifications are written province by province. They move onto
Tag.overrides and Tag.areas in the next pass, and gen_provinces will derive both
tables from this file once they do. Until then gen_provinces remains
authoritative for land, and AREA_OWNERS/PROVINCE_OWNERS below are mirrors rather
than the source - do not edit either side alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------------------
# Realm size, argued per realm
# --------------------------------------------------------------------------------------
# Four realms are genuinely contested and are flagged in their own note rather than
# quietly decided. The old rule here was "the five are peers at 2, Lusatia sits below
# them", which made the ranks a statement about the partition rather than about the
# realms: it would have kept five tags at 2 and demoted a sixth even if Lusatia were
# the largest realm on the map.

@dataclass(frozen=True)
class Tag:
    """One realm this mod is responsible for."""

    tag: str
    #: Display name the mod uses for this realm, where it differs from vanilla's.
    name: Optional[str] = None
    #: 1 duchy, 2 kingdom, 3 empire. None only for a deferred realm.
    rank: Optional[int] = None
    #: The argument for that rank. Never left empty: an unargued tier is how the
    #: Tulunids ended up ranked level with Silesia.
    rank_note: str = ""
    #: Province id for the seat, or None to keep vanilla's.
    capital: Optional[int] = None
    #: Primary culture, for a country file written from scratch.
    culture: Optional[str] = None
    #: CK3 title supplying the 867 ruler's name and dynasty.
    ck3_title: Optional[str] = None
    #: Why CK3 is not the authority, when ck3_title is None. Required if ck3_title
    #: is None and the realm is not deferred - an unexplained gap is a silent one.
    no_ck3: Optional[str] = None
    #: Named land blocks this tag takes, from landblocks.py.
    grants: tuple = ()
    #: Position of this tag's grant in layer 3. Load-bearing, not cosmetic: the
    #: allocation lets a later transfer win an overlap, so reordering these
    #: silently moves provinces. None means the tag takes no block.
    grant_order: Optional[int] = None
    #: EU4 areas this tag claims. Migrated from gen_provinces in the next pass.
    areas: tuple = ()
    #: Provinces taken against their area. Migrated from gen_provinces next pass.
    overrides: tuple = ()
    #: Why no country file is written yet. A deferral, not an exemption.
    deferred: Optional[str] = None
    #: True for realms the mod gives land to (the allocation's tag list).
    in_alloc: bool = False

    #: Areas this realm takes whole, by EU4 area name. Layer 1 of the allocation.
    areas: tuple = ()

    #: Individual provinces this realm takes, applied after every area claim and
    #: before the transfers. Layer 2. Most realms need a handful because EU4 areas
    #: straddle 867 borders: an area is a modern administrative unit, not a
    #: Carolingian one, so the province inside it that belongs elsewhere has to be
    #: pulled back out by hand. Each entry below carries the evidence.
    provinces: tuple = ()
    #: What gen_countries.py does with this realm's country file:
    #:   "fresh"   - written from scratch (capital, culture, rank, own ruler)
    #:   "vanilla" - vanilla's file copied, patching capital/rank/ruler as asked
    #:   "elector" - vanilla's file copied with only its 867 vote dissolved
    #:   "none"    - no file; the realm is deferred or deliberately untouched
    country: str = "vanilla"

    # -- the axes a reader is most likely to get wrong --------------------------
    @property
    def managed(self) -> bool:
        """True if this mod keeps a realm for it: a rank and a court.

        PAP is deferred but not managed - it keeps vanilla's Rome and vanilla's
        ruler, so the mod has no realm there, only a title to audit against.
        """
        return self.rank is not None

    @property
    def writes_country_file(self) -> bool:
        """True if gen_countries.py emits a file for this realm.

        False for a deferred realm, and false for a realm the mod only strips an
        electorate from - those keep vanilla's file untouched.
        """
        return self.deferred is None and self.rank is not None

    def __post_init__(self):
        # A realm with no CK3 title must say why, or the audit cannot tell "we
        # looked and there is nothing there" from "nobody has looked".
        if self.ck3_title is None and self.no_ck3 is None and self.deferred is None:
            raise ValueError(
                f"{self.tag}: ck3_title is None but neither no_ck3 nor deferred "
                f"explains it - give one or the other, so the gap is deliberate")
        if self.rank is None and not self.deferred and self.country != "none":
            raise ValueError(
                f"{self.tag}: a Tag must have a rank, be deferred, or declare "
                f'country="none" - otherwise it is a realm of unclear status')


TAGS: list[Tag] = [

    # -- the 867 Carolingian partition ------------------------------------------
    Tag(tag="FRA", name="West Francia", rank=2, capital=183, culture="frankish",
        ck3_title="k_france", in_alloc=True,
        rank_note="West Francia: the largest of the partitions, and a kingdom. "
                  "Charles the Bald was King of the Franks from 843 and held "
                  "nothing higher in 867 - the imperial crown came in February "
                  "875, when Pope John VIII crowned him in Rome, eight years "
                  "after this start date. Ranking him 3 here would assert a "
                  "title he did not hold yet, which is the same anachronism that "
                  "made Bavaria a duchy rather than the kingdom Carloman was "
                  "crowned in 876. His successor Arnulf is crowned in 887 and is "
                  "still an anachronism for a 867 file, so rank 3 stays out.",
        areas=(
            # West Francia - Charles the Bald, King of the Franks
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
        ),
        provinces=(
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
            192,   # Bourgogne (Dijon)  (bourgogne_area; vanilla BUR)
            # Catalonia minus Tarragona, carved out of catalonia_area for West Francia.
            # Barcelona, Girona, Urgell and Roussillon (Rosello) were Frankish marcher
            # counties; Tarragona (2988) is left with Aragon. Claimed one by one
            # because only these four change hands - the area as a whole does not.
            197,   # Roussillon (Rosello)  (catalonia_area; vanilla ARA)
            212,   # Girona                 (catalonia_area; vanilla ARA)
            213,   # Barcelona              (catalonia_area; vanilla ARA)
            2987,   # Urgell                 (catalonia_area; vanilla ARA)
        )),

    Tag(tag="LOT", country="fresh", name="Lotharingia", rank=2, capital=1878, culture="burgundian",
        ck3_title="k_lotharingia", in_alloc=True,
        rank_note="Lotharingia: a kingdom, though a hollow and contested one.",
        areas=(
            # Lotharingia - Lothair II, middle kingdom, capital Aachen
            # Lotharingia proper (Low Countries, Moselle, Rhine) plus Upper
            # Burgundy and the Kingdom of Provence/Arles, all held until 875.
            "lower_rhineland_area", "lorraine_area", "alsace_area",
            "wallonia_area", "brabant_area", "north_brabant_area",
            "holland_area", "frisia_area", "bourgogne_area",
            "romandie_area", "savoy_dauphine_area",
        ),
        provinces=(
            # Koln and Berg are Lotharingian, not East Frankish. CK3 puts both
            # counties in k_lotharingia proper - c_cologne and c_berg sit alongside
            # c_aachen and c_julich in d_rhine, k_lotharingia - and the 867 partition
            # left the lower Rhine with Lothair II. Koln was also never Louis the
            # German's seat, so East Francia's capital moves to Frankfurt (1876).
            85,   # Koln
            84,   # Berg
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
            1743,   # Cambray
        )),

    Tag(tag="GER", country="fresh", name="East Francia", rank=2, capital=1876, culture="hessian",
        ck3_title="k_east_francia", in_alloc=True,
        rank_note="East Francia: a kingdom ruled in its own right.",
        areas=(
            # East Francia - Louis the German
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
        ),
        provinces=(
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
            80,   # Trier
            1760,   # Koblenz
            # Leipzig leaves Lusatia for East Francia. south_saxony_area is otherwise
            # Sorbian, and CK3 backs that: b_wittenberg, b_dresden, b_gorlitz,
            # b_bautzen, b_meissen, b_plauen and b_gera all sit under k_sorbia (the
            # kingdoms holding d_lausitz and d_meissen), which is the direct analogue of
            # Lusatia here. Leipzig is the exception - b_leipzig belongs to
            # c_mersenburg, which CK3 files under d_anhalt inside k_east_francia,
            # alongside Halle and Magdeburg. So the area splits: Merseburg's
            # hinterland is East Frankish, the Meissen/Lausitz block is Sorbian.
            62,   # Leipzig (Leipzig)  (south_saxony_area; vanilla THU)
        )),

    Tag(tag="ITA", country="fresh", name="Italy", rank=2, capital=4728, culture="lombard",
        ck3_title="k_italy", in_alloc=True,
        rank_note="Italy: Louis II was king of Italy as well as emperor, so Italy "
                  "is a kingdom held under an imperial claim, not the empire "
                  "itself.",
        areas=(
            # Kingdom of Italy - north only, Pavia
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
        ),
        provinces=(
            # Geneva and Savoie go to Italy, breaking both of their areas out. Neither
            # is a Neustrian or Lotharingian province at all - CK3 files c_geneva and
            # c_savoie under k_burgundy :: ##d_savoie, the Alpine kingdom straddling
            # the Pennine and Graubunden passes - and the mod gives the Alpine west to
            # Italy, which by 867 already reaches the Ligurian and Provencal coast.
            # So Geneva leaves romandie_area (Bern, Fribourg and Wallis stay
            # Lotharingian) and Savoie leaves savoy_dauphine_area (Lyonnais, Dauphine
            # and Annecy stay Lotharingian). This supersedes the earlier Transjurania
            # reading, which sent Geneva East Francia at the Meerssen line.
            4720,   # Geneva
            205,   # Savoie
            # Nice was a county of Provence until 1388. Now that provence_area is
            # Italian, Nice goes with it and its area, so the override is gone and it
            # lands in liguria_area with Genoa and Albenga.
            # Trent, on the other hand, is carved out of tirol_area and goes Italy:
            # the Bishopric of Trent was Italian-facing and linked to the Lombard
            # kingdom, while Tirol proper stays Bavarian.
            110,   # Trent      (tirol_area; vanilla TNT)
            # --- Central Italy: Lazio and Umbria, plus Ancona and Urbino -------------
            # In 867 there is no Papal State to speak of, so the Patrimony goes to the
            # Lombard Kingdom of Italy under Louis II rather than sitting with the
            # Pope. Urbino was part of that Patrimony long before the deluge of
            # Montefeltro donations that made it a papal fief, so it goes over too.
            # Rome and the Abruzzi are carved back out below and stay as they are.
            2976,   # Umbria     (lazio_area; vanilla PGA)
            4731,   # Spoleto    (lazio_area; vanilla PAP)
            4732,   # Terracina  (lazio_area; vanilla PAP)
            119,   # Ancona     (central_italy_area; vanilla PAP)
            2977,   # Urbino    (central_italy_area; vanilla URB)
            # Corsica still rode with the Lombard duchy of Tuscany in 867, a century
            # before Pisa and Genoa started wrangling over it, so it follows Italy
            # rather than staying with Genoa (1247 Corsica, vanilla GEN).
            1247,   # Corsica    (corsica_sardinia_area; vanilla GEN)
        )),

    Tag(tag="BAV", country="fresh", name="Bavaria", rank=1, capital=65, culture="bavarian",
        ck3_title="d_bavaria", in_alloc=True,
        rank_note="Bavaria is a DUCHY in 867, not a kingdom, and that is true "
                  "whether or not it is independent. Carloman governs it from "
                  "c. 863 but is not crowned king until 876, so a rank-2 Bavaria "
                  "would assert a crown nine years early. The realms are "
                  "independent by design - no vassalage anywhere in this mod - so "
                  "the tier is the only place any hierarchy is still expressed, "
                  "and it has to be right here.",
        areas=(
            # Bavaria - Carloman, granted his own appanage in 855
            # Bavaria proper, the Nordgau/Regensburg, the Austrian march, Tyrol,
            # Carinthia and the Carantanian march. NOT Swabia or Franconia: those
            # were East Frankish. Bayreuth (Nordgau) is Bavarian but shares EU4's
            # upper_franconia_area with clearly East Franconian provinces.
            "upper_bavaria_area", "lower_bavaria_area",
            "east_bavaria_area", "tirol_area", "austria_proper_area",
            "inner_austria_area",
        ),
        provinces=(
            # Bayreuth sat in the Nordgau around Regensburg, which was Bavarian. Its
            # area-mates (Bamberg, Nuremberg, Coburg) are East Franconian, hence the
            # split.
            4717,   # Bayreuth
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
            1868,   # Augsburg   (CK3 c_augsburg  -> d_augsburg -> k_bavaria)
            68,   # Memmingen  (CK3 barony Memmingen -> c_kempten -> d_augsburg)
            # carinthia_area is EU4's Slovenian area, not Carinthia: it holds Carniola
            # proper (Krain, Cilli) plus the Aquileian coast (Istria, Gorz, Trieste).
            # The area goes to Italy, but Carniola is carved back out and stays
            # Bavarian, since the Heptarchy was Frankish and Lotharingian, never
            # Italian, in 867.
            129,   # Krain      (carinthia_area; vanilla HAB)
            4751,   # Cilli      (carinthia_area; vanilla CLI)
        )),

    Tag(tag="SOR", country="fresh", name="Lusatia", rank=1, capital=60, culture="sorbian",
        ck3_title="d_lausitz", in_alloc=True,
        rank_note="Lusatia: a Sorbian duchy, small in 867 on any measure.",
        areas=(
            # Lusatia - a free Sorbian principality, not a Carolingian realm
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
        ),
        provinces=(
            # Vogtland goes to Lusatia with the Sorbian lands, carved out of
            # thuringia_area: Plauen and Zwickau were the two halves of the
            # Sudeten/Voigtland march that kept one foot in each sphere.
            2965,   # Vogtland   (thuringia_area; vanilla THU)
        )),

    # -- Iberia and the west -----------------------------------------------------
    Tag(tag="NAV", rank=2, capital=210, ck3_title="k_navarra", in_alloc=True,
        grants=(), rank_note="The Kingdom of Pamplona under Garcia I, a kingdom "
                             "in 867 and a peer of the Asturians.",
        provinces=(
            # Vizcaya and Huesca (Osca) to Navarra. Biscay was a Basque county under
            # Navarre's sphere, and Huesca came with the Sobrarbe/Appalachian march that
            # straddled the Pyrenees. Both are carved out one at a time because neither
            # area changes hands as a whole - Navarra's own province (210) and Rioja
            # (2989) stay put, and Aragon keeps the rest of aragon_area. NAV is a
            # vanilla tag, so it needs no country file from this mod.
            209,   # Vizcaya (Giscaya)   (basque_country; vanilla CAS)
            211,   # Huesca  (Osca)      (aragon_area;     vanilla ARA)
        )),

    Tag(tag="ASU", rank=2, capital=207, ck3_title="k_asturias", in_alloc=True,
        grant_order=10,
        grants=("ASU_ALL",),
        rank_note="Asturias: Alfonso III inherited the kingship in 866, one year "
                  "before the start date, so it is a kingdom and not a county."),

    Tag(tag="ADU", rank=2, capital=204, ck3_title="c_granada", in_alloc=True,
        grant_order=9,
        grants=("ADU_ALL",),
        rank_note="The Nayihid emirate of Granada, a principality that by 867 "
                  "ruled the whole of al-Andalus."),

    Tag(tag="CRT", rank=1, capital=1450, ck3_title=None, in_alloc=True,
        grant_order=2,
        grants=("CRETE",),
        no_ck3="no CK3 model: CK3 has no Crete, so there is no character to "
               "compare",
        rank_note="Crete: an Emirate of Crete is a single-island emirate under "
                  "Abu Hafs Umar; a duchy is the closest tier EU4 offers."),

    # -- the Islamic east --------------------------------------------------------
    Tag(tag="ARB", rank=3, capital=385, ck3_title="e_arabia", in_alloc=True,
        grant_order=7,
        grants=("ARABIA_ALL",),
        rank_note="The Abbasid Caliphate, which in 867 is the empire of the "
                  "Islamic world and no realm in this table rivals it."),

    Tag(tag="EGY", rank=2, capital=361, ck3_title="k_egypt", in_alloc=True,
        grant_order=8,
        grants=("EGY_ALL",),
        rank_note="CONTESTED. The Tulunids held Egypt and Syria as a de facto "
                  "independent beylikh, but a beylikh is a principality, and EU4's "
                  "only tiers are duchy and kingdom. Kept at 2 so the Tulunids are "
                  "not ranked level with Silesia on the strength of a naming gap; "
                  "drop to 1 if the literal principality reading is preferred."),

    # -- Italy, the Balkans and the Aegean ---------------------------------------
    Tag(tag="SIL", rank=1, capital=264, ck3_title="d_lower_silesia", in_alloc=True,
        rank_note="Silesia: a Piast duchy, small but not a titular one.",
        provinces=(
            # silesia_area changes hands entirely but splits down the middle: the
            # Breslau/Liegnitz/Glogau west goes to Silesia, the Opole/Ratibor east to
            # Great Moravia. Note that file names and in-game names diverge here - the
            # player sees Wroclaw, Legnica and Glogow, and the game stores those as
            # "Breslau", "Liegnitz" and "Glogau".
            264,   # Breslau (Wroclaw)    (silesia_area; vanilla OPL)
            4238,   # Liegnitz (Legnica)   (silesia_area; vanilla GLG)
            2966,   # Glogau   (Glogow)    (silesia_area; vanilla GLG)
        )),

    Tag(tag="GMA", rank=2, capital=4237, ck3_title="k_moravia", in_alloc=True,
        rank_note="Great Moravia under Rastislav, a kingdom in its own right.",
        provinces=(
            4723,   # Opole                (silesia_area; vanilla OPL)
            263,   # Ratibor  (Racibor)   (silesia_area; vanilla OPL)
            # Great Moravia takes the whole of moravia_area - Brno, Olomouc and
            # Ostrava - giving it a real Moravian heartland instead of existing only as
            # a formable nation. GMA is vanilla, so again no country file is needed.
            265,   # Brno                 (moravia_area; vanilla BOH)
            4237,   # Olomouc              (moravia_area; vanilla BOH)
            4726,   # Ostrava              (moravia_area; vanilla BOH)
            # ...and the whole of slovakia_area, so Great Moravia starts as a real
            # landholder rather than a formable name. There is no nitra_area in EU4
            # 1.37 and no province called Nitra; slovakia_area is the region meant, and
            # it holds five: Hont, Zemplen, Spis, Pozsony and Trencin. Spis and Zemplen
            # are Ruthenian rather than Slovak, but they are the eastern half of the
            # same Slovak march lands, so they go over as a block.
            154,   # Hont                 (slovakia_area; vanilla HUN)
            162,   # Zemplen              (slovakia_area; vanilla HUN)
            1318,   # Spis                 (slovakia_area; vanilla HUN)
            1772,   # Pozsony              (slovakia_area; vanilla HUN)
            4236,   # Trencin              (slovakia_area; vanilla HUN)
        )),

    Tag(tag="DAL", rank=1, capital=136, ck3_title="d_dalmatia", in_alloc=True,
        grant_order=6,
        grants=("DAL_CORE",),
        rank_note="Dalmatia: a coastal duchy of city-states, nominally one realm."),

    Tag(tag="BYZ", rank=3, capital=4698, ck3_title="e_byzantium", in_alloc=True,
        grant_order=0,
        grants=("BYZ_ALL",),
        rank_note="The Empire itself. 867 is Basil I's first full year."),

    Tag(tag="BUL", rank=2, capital=1764, ck3_title="k_bulgaria", in_alloc=True,
        grant_order=1,
        grants=("BUL_ALL",),
        rank_note="The First Bulgarian Empire under Boris, a kingdom by 867 and a "
                  "peer of Byzantium's neighbours rather than a vassal duchy."),

    # -- the steppe and the Danube ----------------------------------------------
    Tag(tag="HUN", rank=1, capital=283, ck3_title=None, in_alloc=True,
        grant_order=3,
        grants=("MOGYERS_LEVIDIA",),
        no_ck3="vanilla: keeps vanilla's 1444.11.10 Hunyadi block",
        rank_note="CONTESTED. The Principality of Hungary under the Arpad was a "
                  "principality, not a kingdom, until 1000 - so 1 is the literal "
                  "answer, yet the realm is a major power in 867 and EU4 has no "
                  "tier between a duchy and a kingdom to say so. Kept at 1 on the "
                  "name; raise to 2 if a stronger starting Hungary is wanted."),

    Tag(tag="MON", rank=1, capital=138, ck3_title="c_duklja", in_alloc=True,
        grant_order=5,
        grants=("MON_ADRIATIC",),
        rank_note="Duklja under Miroslav, a coastal Serbian principality."),

    # CRI is the one realm where the question is not "which CK3 character" but
    # "does this polity exist in 867". The tag is vanilla Crimea, whose ruler in
    # 867 was a Golden Horde appointee - the Crimean Khanate is not founded until
    # 1441. Its one mod province is Azov, which in 867 is Khazar/Bulgar steppe,
    # and CK3's nearest real 867 powers are d_khazaria and k_caspian_steppe, both
    # held by Manasseh of the Bulanid house. Authoring CRI needs a decision about
    # what a Crimean realm IS in 867, so it is left unmapped rather than given a
    # plausible-looking anachronism.
    #
    # Rank 1 is provisionally in place so the tag stays playable while its
    # identity is settled.
    Tag(tag="CRI", rank=1, capital=286, ck3_title=None, in_alloc=True,
        grant_order=4,
        grants=("CRI_AZOV",),
        no_ck3="undecided: no 867 Crimean polity exists to map - see the "
               "note above",
        deferred="Vanilla Crimea, holding Azow (286) only. There is no Crimean "
                 "polity in 867 to write: the Crimean Khanate is a Golden Horde "
                 "appanage founded in 1441, and vanilla's file arrives with a "
                 "1444 khan. CK3 has no 867 holder for d_crimea, k_pontic_steppe "
                 "or e_mongol_empire; its nearest real 867 powers are d_khazaria "
                 "and k_caspian_steppe, both held by Manasseh of the Bulanid "
                 "house. Authoring this needs a decision about what a Crimean "
                 "realm IS in 867, which is the same Pontic steppe question as "
                 "the provinces Hungary currently holds. Deliberately deferred, "
                 "not overlooked.",
        rank_note="CONTESTED, and see the deferral above: there is no Crimean "
                  "polity in 867 at all. Rank 1 is provisionally in place so the "
                  "tag is playable while its identity is settled."),

    # -- kept realms whose land this mod never reassigns -------------------------
    # Not in ALL_TAGS because the mod does not hand out their land: they keep
    # vanilla's provinces untouched. They are still realms this mod maintains a
    # court and a size for, so they still get a deliberate rank.
    Tag(tag="BOH", rank=1, capital=266, ck3_title=None,
        no_ck3="mod-invented: Borivoj is the mod's own Bohemian ruler; CK3 "
               "records no 867 holder for k_bohemia to verify against",
        rank_note="Bohemia: a duchy of the Empire under Borivoj I. Rank 1 is the "
                  "literal 867 answer and is NOT demotion for standing outside the "
                  "partition: Bohemia is a small march here for the ordinary "
                  "reason, that in 867 it was a small duchy."),

    Tag(tag="SAR", rank=1, capital=127, ck3_title=None,
        no_ck3="no CK3 model: d_sardinia is vacant in 867 and k_sardinia unheld, "
               "and no Sardinian ruler of that date is attested to name instead",
        rank_note="Sardinia, from vanilla, holding Sassari (127), Arborea (4735) "
                  "and Cagliari (2986). All three are in NOT_IMPERIAL_867, so "
                  "Sardinia was never part of the imperial core and releasing it "
                  "changes nothing about the 226 the empire decision requires. A "
                  "duchy is the right size: in 867 Sardinia is a Byzantine "
                  "province governed by the giudicati of Torres and Cagliari, not "
                  "a kingdom of its own."),

    # -- the Papal State ---------------------------------------------------------
    # PAP holds Rome: 118 Roma is deliberately not taken, so it still holds one
    # province on the mod's own account. Its 867 holder is Pope Nicholas I
    # (CK3 7853, "Niccolo"), the one mapped character with NO dynasty and no
    # dynasty_house at all - which is historically ordinary, since the papacy is
    # not a hereditary house in CK3's model. So the name lifts and the dynasty
    # does not exist to lift; ck3ruler treats a missing dynasty as a reason to
    # write none rather than to invent one.
    #
    # country="none" and no rank: PAP is tracked here so the CK3 audit can resolve
    # its title, but it is deliberately NOT a realm this mod maintains. It keeps
    # vanilla's Rome and vanilla's ruler, so there is nothing to sync a ruler into
    # and no tier to decide.
    Tag(tag="PAP", rank=None, capital=118, ck3_title="k_papal_state",
        country="none"),
]

BY_TAG: dict[str, Tag] = {t.tag: t for t in TAGS}


# --------------------------------------------------------------------------------------
# Derived views. Every one of these is a projection of TAGS, never a second copy.
# --------------------------------------------------------------------------------------

def _r(t: Tag):
    return t.tag


#: The tags the allocation may hand a province to. Not the same set as the managed
#: realms: BOH and SAR are maintained but their land is never reassigned.
ALL_TAGS: list[str] = [t.tag for t in TAGS if t.in_alloc]

#: Every realm the mod maintains a country file for, which must therefore have a
#: deliberate rank. This is what stops a realm being added without deciding how
#: big it is.
KEPT_REALMS: set = {t.tag for t in TAGS if t.managed}

#: Realms kept but not yet authored, each with the reason. Reported on every build.
DEFERRED_REALMS: dict = {t.tag: t.deferred for t in TAGS if t.deferred}

#: government_rank per realm.
RANK: dict = {t.tag: t.rank for t in TAGS if t.rank is not None}

#: CK3 title per realm. A realm here has its ruler's name and dynasty lifted.
TITLES: dict = {t.tag: t.ck3_title for t in TAGS if t.ck3_title}

#: Vanilla tags the allocation hands land to, which keep vanilla's own file and
#: vanilla's own ruler. Not Tags: the mod maintains no realm for them, it only
#: takes some of their land. They are listed so ck3ruler's audit has no blind
#: spot - a land-holder appearing in neither TITLES nor NOT_CK3 is reported and
#: fails the build. Without this, adding a land-holder silently escapes the check.
#:
#: Deliberately absent: tags the mod never touches at all. Brittany and Venice are
#: left as vanilla free agents, and the electors other than BOH hold a vote and
#: nothing else. None of them is this mod's business, so none is tracked here.
VANILLA_HOLDERS: dict = {
    "BRA": "vanilla: keeps vanilla's Brandenburg file and 1440 Hohenzollern ruler",
    "DTT": "vanilla: keeps vanilla's Leitha ruler",
    "HSA": "vanilla: keeps vanilla's ruler",
    "MKL": "vanilla: keeps vanilla's Montferrat ruler",
    "SHL": "vanilla: keeps vanilla's Schauenburg ruler",
    "STE": "vanilla: keeps vanilla's Stettin ruler",
    "TEU": "vanilla: keeps vanilla's Teutonic ruler",
    "WOL": "vanilla: keeps vanilla's Wolgast ruler",
}

#: Realms that own land but whose ruler is not CK3's to supply, with the reason.
#: Merged rather than chosen: a managed realm with no CK3 title, plus every vanilla
#: land-holder above. ck3ruler reads this.
NOT_CK3: dict = {**{t.tag: t.no_ck3 for t in TAGS
                    if t.no_ck3 and t.tag not in TITLES},
                 **VANILLA_HOLDERS}

#: Capitals for the from-scratch country files, with their culture. FRA is absent
#: on purpose: it keeps vanilla's French history and only overrides the ruler, so
#: it has no header of its own to write.
HEADER: dict = {t.tag: (t.capital, t.culture) for t in TAGS
                if t.country == "fresh" and t.capital and t.culture}

#: Realms whose country file is written from scratch, in write order.
FRESH_REALMS: list = [t.tag for t in TAGS if t.country == "fresh"]

#: Layer 1 of the allocation: which areas each realm takes whole. gen_provinces
#: walks this to seed ownership, then layer 2 carves provinces back out.
AREA_OWNERS: dict = {t.tag: t.areas for t in TAGS if t.areas}

#: Layer 2 of the allocation: the province-level corrections, inverted back to the
#: province -> tag shape the allocator wants. Per-realm on the Tag, because the
#: reasoning is per-realm - Trieste is Italy's but Krain is Bavaria's.
#:
#: Venice's own province is NOT here. VEN is deliberately not a Tag (it is not a
#: realm this mod maintains) and provinces held by untracked tags stay declared
#: where the allocator reads them, in gen_provinces.UNTRACKED_OWNERS.
PROVINCE_OWNERS: dict = {pid: t.tag for t in TAGS for pid in t.provinces}

#: Layer 3 of the allocation, by block NAME. Order is load-bearing, not cosmetic:
#: the allocation lets a later transfer win an overlap, so reordering these moves
#: provinces silently. grant_order is what preserves that order independently of
#: the order Tags happen to be declared in.
GRANTS: tuple = tuple(
    (t.tag, t.grants)
    for t in sorted((x for x in TAGS if x.grants),
                    key=lambda x: (x.grant_order is None, x.grant_order)))


def _resolve(names):
    """Flatten a tag's block names into one province list.

    Concatenating rather than wrapping matters: the allocation treats each entry
    as a flat list of province ids, so returning [BLOCK] instead of BLOCK would
    nest a list inside a list and silently drop every province in it.
    """
    import landblocks
    out = []
    for n in names:
        out.extend(getattr(landblocks, n))
    return out


#: Layer 3 as gen_provinces consumes it: (tag, [province ids]). Same order as
#: GRANTS, because the names are the declaration and this is the resolution.
TRANSFERS: tuple = tuple((tag, _resolve(names)) for tag, names in GRANTS)


def selfcheck() -> None:
    """Fail loudly on a database that contradicts itself."""
    seen = set()
    for t in TAGS:
        if t.tag in seen:
            raise ValueError(f"{t.tag}: declared twice in TAGS")
        seen.add(t.tag)
        if t.rank is not None and not t.rank_note.strip():
            raise ValueError(f"{t.tag}: rank {t.rank} with no rank_note")
        if t.ck3_title and t.no_ck3:
            raise ValueError(
                f"{t.tag}: both ck3_title and no_ck3 are set - CK3 is the "
                f"authority or it is not")
    missing = KEPT_REALMS - set(RANK) - set(DEFERRED_REALMS)
    if missing:
        raise ValueError(f"managed realms with neither a rank nor a deferral: "
                         f"{sorted(missing)}")
    for tag, blocks in TRANSFERS:
        if tag not in seen:
            raise ValueError(f"TRANSFERS names {tag}, which is not a Tag")


selfcheck()
