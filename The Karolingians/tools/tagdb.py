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
    deferred  Why no country file is written yet, or None.

What is not here yet
--------------------
Nothing about land lives outside this file. AREA_OWNERS and PROVINCE_OWNERS below
are derived from Tag.areas and Tag.provinces, and build.py derives its
allocation from the same two lists - there is no second copy to drift.
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
    #: CK3 title to read the 867 ruler from when the realm's own title is vacant
    #: then. SAR: d_sardinia is empty 843-1164, so c_arborea rules it.
    ruler_title: Optional[str] = None
    #: Why CK3 is not the authority, when ck3_title is None. Required if ck3_title
    #: is None and the realm is not deferred - an unexplained gap is a silent one.
    no_ck3: Optional[str] = None
    #: EU4 areas this tag claims. With `provinces` below, this is the whole
    #: declaration of a realm's land: there is no third list and no block table.
    areas: tuple = ()
    #: Why no country file is written yet. A deferral, not an exemption.
    deferred: Optional[str] = None
    #: True for realms the allocation may hand land to. BOH and PAP turn it off;
    #: selfcheck refuses a tag that declares land with it off.
    in_alloc: bool = True

    #: Areas this realm takes whole, by EU4 area name. Layer 1 of the allocation.
    areas: tuple = ()

    #: Individual provinces this realm takes, applied after every area claim and
    #: before the transfers. Layer 2. A frozenset, not a list: once the layers are
    #: applied the order carries no meaning, and a province appearing twice was
    #: only ever a sign that two blocks had overlapped - 12 did, and 12 are now
    #: gone rather than deduplicated away. Most realms still need a handful
    #: because EU4 areas straddle 867 borders: an area is a modern administrative
    #: unit, not a Carolingian one, so the province inside it that belongs
    #: elsewhere has to be pulled back out by hand. Each entry below carries the
    #: evidence.
    provinces: frozenset = field(default_factory=frozenset)
    #: What build.py does with this realm's country file. This is the whole
    #: instruction: build reads no other list.
    #:   "fresh"   - written from scratch (capital, culture, rank, own ruler)
    #:   "vanilla" - vanilla's file copied, patching capital/rank/ruler as asked
    #:   "elector" - vanilla's file copied with only its 1444 vote dissolved
    #:   "written" - owned by the repo, never generated; build must not touch it
    #:   "none"    - no file; the realm is deferred or deliberately untouched
    country: str = "vanilla"
    #: True when this realm is an elector of the HRE, so its 1444 vote goes.
    elector: bool = False
    #: True for the five Carolingian kingdoms the mod presents as the empire.
    imperial_kingdom: bool = False
    #: The mod's own 1444 ruler, written by hand instead of read from CK3.
    ruler_block: Optional[str] = None
    #: Prose spliced above this realm's 1444.1.1 block in its shipped country
    #: file, saying where the 867 reading came from. Never generated.
    provenance: Optional[str] = None
    #: True when this realm's heir starts a new house, so --fix must not
    #: overwrite the heir's dynasty from CK3. No realm sets it yet.
    no_heir_sync: bool = False

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
        """True if build.py emits a file for this realm.

        False for a deferred realm, and false for a realm the mod only strips an
        electorate from - those keep vanilla's file untouched.
        """
        return self.deferred is None and self.rank is not None

    def __post_init__(self):
        # Callers may write either a tuple or a set literal; the field is a set
        # either way, so nothing downstream has to care which was typed.
        object.__setattr__(self, "provinces", frozenset(self.provinces))
        # A realm with no CK3 title must say why, or the audit cannot tell "we
        # looked and there is nothing there" from "nobody has looked".
        if self.ck3_title is None and self.no_ck3 is None and self.deferred is None:
            raise ValueError(
                f"{self.tag}: ck3_title is None but neither no_ck3 nor deferred "
                f"explains it - give one or the other, so the gap is deliberate")
        if (self.rank is None and not self.deferred
                and self.country not in ("none", "elector")):
            raise ValueError(
                f"{self.tag}: a Tag must have a rank, be deferred, or declare "
                f'country "none" or "elector" - otherwise it is a realm of '
                f'unclear status')


CTRY_DATE = "1444.1.1"
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

TAGS: list[Tag] = [

    # -- the 867 Carolingian partition ------------------------------------------
    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of k_france
# at 867.1.1 is character 90104, "Charles", of dynasty 25061 "Karling". CK3 gives
# him no epithet, so the earlier hand-written "Charles the Bald" is gone; that is
# what verbatim means here. Do not hand-edit name or dynasty - run
# `python3 tools/build.py --fix` instead, and validate.py will fail if the file
# and CK3 disagree.
""",
    ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="FRA", imperial_kingdom=True, name="West Francia", rank=2, capital=183, culture="frankish",
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

    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# k_lotharingia at 867.1.1 is character 144998, "Lothaire", of dynasty 25061
# "Karling". Note CK3 writes that name unquoted, with no epithet; the earlier
# hand-written "Lothair II" is gone. Do not hand-edit name or dynasty - run
# `python3 tools/build.py --fix` instead.
""",
    ruler_block=f"""
# Lothair II died childless in 869, which is why Lotharingia came apart. He is
# deliberately left without an heir so the scripted fragmentation still works.
{CTRY_DATE} = {{
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
    tag="LOT", imperial_kingdom=True, country="fresh", name="Lotharingia", rank=2, capital=1878, culture="burgundian",
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

    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# k_east_francia at 867.1.1 is character 90107, "Ludwig", of dynasty 25061
# "Karling". CK3 gives him no epithet, so the earlier hand-written "Louis the
# German" is gone; that is what verbatim means here. Do not hand-edit name or
# dynasty - run `python3 tools/build.py --fix` instead.
""",
    ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="GER", imperial_kingdom=True, country="fresh", name="East Francia", rank=2, capital=1876, culture="hessian",
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

    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# d_bavaria at 867.1.1 is character 42018, "Karlmann", of dynasty 25061
# "Karling".
#
# The duchy is deliberate, and the reason is in build.py: CK3 has no
# independent Bavaria in 867. Its k_bavaria is held by Ludwig (90107) - the same
# man as k_east_francia - continuously from 826.1.1 until 876.1.1, and Carloman
# only takes it in 876. Since this mod does split Bavaria off as its own realm,
# d_bavaria is the title whose 867 holder is him. Mapping to k_bavaria would have
# made this a second "Ludwig"/"Karling" and erased the realm.
#
# Do not hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
    ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="BAV", imperial_kingdom=True, country="fresh", name="Bavaria", rank=1, capital=65, culture="bavarian",
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

    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of k_italy
# at 867.1.1 is character 30228, "Louis", of dynasty 25061 "Karling". CK3 gives
# him no regnal number, so the earlier hand-written "Louis II" is gone. Do not
# hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
    ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="ITA", imperial_kingdom=True, country="fresh", name="Italy", rank=2, capital=4728, culture="lombard",
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

    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# d_lausitz at 867.1.1 is character 184007, "Radomil", of the Milczanow dynasty.
#
# CK3 models no Sorbian title at all - k_sorbs and d_sorbs both have no holder -
# so d_lausitz is the nearest title with an actual 867 ruler. That replaces the
# hand-written "Mstivoj"/"of Lusatia". Mstivoj is historically the better-known
# Lusatian ruler of the period and survives as the heir below; CK3's choice is
# followed because it is what the rest of this mod's western Slavic realms do.
#
# Do not hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
    ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="SOR", country="fresh", name="Lusatia", rank=1, capital=60, culture="sorbian",
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
        rank_note="The Kingdom of Pamplona under Garcia I, a kingdom "
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

    Tag(tag="ASU", country="written", rank=2, capital=207, ck3_title="k_asturias", in_alloc=True,
        areas=("asturias_area", "galicia_area", "leon_area"),
        # what the areas above do not already give:
        provinces={
            4789,   # Segovia                (castille_area; vanilla CAS)
        },
        rank_note="Asturias: Alfonso III inherited the kingship in 866, one year "
                  "before the start date, so it is a kingdom and not a county."),

    Tag(tag="ADU", country="written", rank=2, capital=225, ck3_title="k_andalusia", in_alloc=True,
        areas=("alentejo_area", "baleares_area", "beieras_area", "extremadura_area", "lower_andalucia_area", "toledo_area", "upper_andalucia_area", "valencia_area"),
        # what the areas above do not already give:
        provinces={
            214,   # Aragon                 (aragon_area; vanilla ARA)
            217,   # Madrid                 (castille_area; vanilla CAS)
            367,   # The Azores             (macaronesia_area; vanilla -)
            368,   # Madeira                (macaronesia_area; vanilla -)
            1751,   # Ceuta                  (northern_morocco_area; vanilla MOR)
            2755,   # Soria                  (castille_area; vanilla CAS)
            2988,   # Tarragona              (catalonia_area; vanilla ARA)
            2989,   # Rioja                  (basque_country; vanilla CAS)
            2990,   # Teruel                 (aragon_area; vanilla ARA)
            4551,   # Avila                  (castille_area; vanilla CAS)
            4557,   # Lleida                 (aragon_area; vanilla ARA)
        },
        rank_note="Al Andalus: the Umayyad emirate, seated at Cordoba (225) and "
                  "supplied its 867 ruler by CK3's k_andalusia. Rank 2 is a "
                  "kingdom, not a duchy: it holds all of al-Andalus plus Aragon, "
                  "Madrid, the Canaries, Madeira and Ceuta, and a smaller tier "
                  "would misstate it."),

    Tag(tag="CRT", rank=1, capital=163, ck3_title="d_krete", in_alloc=True,
        provinces={
            163,   # Crete                  (morea_area; vanilla VEN)
        },
        rank_note="Crete: an Emirate of Crete is a single-island emirate under "
                  "Abu Hafs Umar; a duchy is the closest tier EU4 offers. CK3's "
                  "d_krete is already held in 867, by Shuayb - Abu Hafs' father, "
                  "who lost the island to his own son in 870, ten years before the "
                  "start date. k_krete is unheld, so the duchy is the only seat."),

    # -- the Islamic east --------------------------------------------------------
    Tag(tag="ARB", country="written", rank=3, capital=385, ck3_title="e_arabia", in_alloc=True,
        areas=("al_jazira_area", "aleppo_area", "bahrain_area", "basra_area", "dulkadir_area", "iraq_arabi_area", "medina_area", "palestine_area", "syria_area", "syrian_desert_area", "tabuk_area", "trans_jordan_area"),
        # what the areas above do not already give:
        provinces={
            327,   # Adana                  (cukurova_area; vanilla RAM)
            331,   # Erzurum                (erzurum_area; vanilla AKK)
            385,   # Mecca                  (mecca_area; vanilla HED)
            412,   # Khuzestan              (khuzestan_area; vanilla MSY)
            415,   # Shahrizor              (shahrizor_area; vanilla TIM)
            416,   # Tabriz                 (tabriz_area; vanilla QAR)
            418,   # Diyarbakir             (north_kurdistan_area; vanilla AKK)
            419,   # Yerevan                (armenia_area; vanilla TIM)
            420,   # Ganja                  (armenia_area; vanilla QAR)
            2205,   # Nakhchivan             (armenia_area; vanilla TIM)
            2206,   # Urmia                  (tabriz_area; vanilla QAR)
            2207,   # Maragheh               (tabriz_area; vanilla QAR)
            2209,   # Ilam                   (luristan_area; vanilla TIM)
            2305,   # Erzincan               (erzurum_area; vanilla TIM)
            2306,   # Mush                   (north_kurdistan_area; vanilla AKK)
            4272,   # Jawf                   (nafud_area; vanilla ANZ)
            4289,   # Shushtar               (khuzestan_area; vanilla MSY)
            4290,   # Hoveyzeh               (khuzestan_area; vanilla MSY)
            4293,   # Arbil                  (shahrizor_area; vanilla QAR)
            4294,   # Sulimaniyeh            (shahrizor_area; vanilla TIM)
            4304,   # Khoy                   (tabriz_area; vanilla QAR)
        },
        rank_note="The Abbasid Caliphate, which in 867 is the empire of the "
                  "Islamic world and no realm in this table rivals it."),

    Tag(tag="EGY", country="written", rank=2, capital=361, ck3_title="k_egypt", in_alloc=True,
        areas=("al_wahat_area", "bahari_area", "cyrenaica_area", "delta_area", "gulf_of_arabia_area", "said_area", "vostani_area"),
        # what the areas above do not already give:
        provinces={
            1232,   # Suakin                 (red_sea_coast_area; vanilla MAM)
            2324,   # Halaib                 (red_sea_coast_area; vanilla MAM)
        },
        rank_note="CONTESTED. The Tulunids held Egypt and Syria as a de facto "
                  "independent beylikh, but a beylikh is a principality, and EU4's "
                  "only tiers are duchy and kingdom. Kept at 2 so the Tulunids are "
                  "not ranked level with Silesia on the strength of a naming gap; "
                  "drop to 1 if the literal principality reading is preferred."),

    # -- Italy, the Balkans and the Aegean ---------------------------------------
    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of
# d_lower_silesia at 867.1.1 is character 82293, "Gardomir", of the dynasty
# CK3 spells "Slezan" with diacritics. The hand-written "Gardomir Slezan"/"Slezan"
# was already a guess at exactly this, so only the spelling is new. Do not
# hand-edit name or dynasty - run `python3 tools/build.py --fix` instead.
""",
    ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="SIL", rank=1, capital=264, ck3_title="d_lower_silesia", in_alloc=True,
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

    Tag(provenance="""# Ruler lifted verbatim from CK3 by build.py: CK3's holder of k_moravia
# at 867.1.1 is character 187002, "Rostislav", of the Mojmird dynasty.
#
# This realm holds the two Moravian provinces (Brno 265, Olomouc 4237) as well as
# Galicia, and its ruler was already Rostislav, so k_moravia is the title whose 867
# holder the mod was reaching for. The hand-written dynasty "of Rostislav" was
# invented; CK3 calls the house Mojmird. Do not hand-edit name or dynasty - run
# `python3 tools/build.py --fix` instead.
""",
    ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="GMA", rank=2, capital=4237, ck3_title="k_moravia", in_alloc=True,
        rank_note="Great Moravia under Rastislav, a kingdom in its own right.",
        # Great Moravia takes the whole of moravia_area - Brno, Olomouc and
        # Ostrava - giving it a real Moravian heartland instead of existing only
        # as a formable nation. GMA is vanilla, so again no country file is needed.
        # ...and the whole of slovakia_area, so Great Moravia starts as a real
        # landholder rather than a formable name. There is no nitra_area in EU4
        # 1.37 and no province called Nitra; slovakia_area is the region meant, and
        # it holds five: Hont, Zemplen, Spis, Pozsony and Trencin. Spis and Zemplen
        # are Ruthenian rather than Slovak, but they are the eastern half of the
        # same Slovak march lands, so they go over as a block.
        areas=("moravia_area", "slovakia_area"),
        # Opole and Ratibor are all that is left of silesia_area here.
        provinces={
            263,   # Ratibor                (silesia_area; vanilla OPL)
            4723,   # Opole                  (silesia_area; vanilla OPL)
        }),

    Tag(tag="DAL", country="written", rank=1, capital=136, ck3_title="d_dalmatia", in_alloc=True,
        provinces={
            136,   # Dalmatia               (east_adriatic_coast_area; vanilla DAL)
            4753,   # Zadar                  (east_adriatic_coast_area; vanilla DAL)
        },
        rank_note="Dalmatia: a coastal duchy of city-states, nominally one realm."),

    Tag(tag="BYZ", country="written", rank=3, capital=151, ck3_title="e_byzantium", in_alloc=True,
        areas=("aegean_archipelago_area", "albania_area", "ankara_area", "aydin_area", "germiyan_area", "hudavendigar_area", "karaman_area", "kastamonu_area", "northern_greece_area", "rum_area"),
        # what the areas above do not already give:
        provinces={
            122,   # Apulia                 (apulia_area; vanilla NAP)
            145,   # Morea                  (morea_area; vanilla BYZ)
            146,   # Athens                 (morea_area; vanilla VEN)
            148,   # Thessaloniki           (macedonia_area; vanilla TUR)
            149,   # Edirne                 (thrace_area; vanilla TUR)
            151,   # Constantinople         (thrace_area; vanilla BYZ)
            285,   # Kaffa                  (crimea_area; vanilla GEN)
            321,   # Cyprus                 (cukurova_area; vanilla CYP)
            330,   # Trebizond              (erzurum_area; vanilla TRE)
            1773,   # Achaea                 (morea_area; vanilla ACH)
            1853,   # Kastoria               (macedonia_area; vanilla TUR)
            2302,   # Icel                   (cukurova_area; vanilla KAR)
            2410,   # Theodoro               (crimea_area; vanilla TRE)
            2447,   # Mantrega               (crimea_area; vanilla GEN)
            2757,   # Kaffa                  (southern_ethiopia_area; vanilla KAF)
            2982,   # Syracuse               (sicily_area; vanilla SIC)
            4701,   # Corinth                (morea_area; vanilla ACH)
            4702,   # Siroz                  (macedonia_area; vanilla TUR)
            4705,   # Gumulcine              (thrace_area; vanilla TUR)
            4779,   # Gallipoli              (thrace_area; vanilla TUR)
        },
        rank_note="The Empire itself. 867 is Basil I's first full year."),

    Tag(tag="BUL", country="written", rank=2, capital=150, ck3_title="k_bulgaria", in_alloc=True,
        areas=("alfold_area", "bulgaria_area", "serbia_area", "silistria_area", "southern_transylvania_area", "transylvania_area", "wallachia_area"),
        # what the areas above do not already give:
        provinces={
            153,   # Pest                   (transdanubia_area; vanilla HUN)
            1756,   # Budjak                 (moldavia_area; vanilla MOL)
            1764,   # Burgas                 (thrace_area; vanilla TUR)
            1766,   # Kosovo                 (rascia_area; vanilla SER)
            1827,   # Raska                  (rascia_area; vanilla SER)
            3001,   # Skopje                 (macedonia_area; vanilla TUR)
            4126,   # Bacs                   (transdanubia_area; vanilla HUN)
            4173,   # Syrmia                 (slavonia_area; vanilla HUN)
            4780,   # Ohrid                  (macedonia_area; vanilla TUR)
        },
        rank_note="The First Bulgarian Empire under Boris, a kingdom by 867 and a "
                  "peer of Byzantium's neighbours rather than a vassal duchy."),

    # -- the steppe and the Danube ----------------------------------------------
    Tag(tag="HUN", country="written", rank=1, capital=283, ck3_title=None, in_alloc=True,
        provinces={
            282,   # Yedisan                (yedisan_area; vanilla CRI)
            283,   # Zaporozhia             (zaporizhia_area; vanilla CRI)
            1943,   # Bratslav               (podolia_volhynia_area; vanilla LIT)
            1944,   # Cherkasy               (west_dniepr_area; vanilla LIT)
            2406,   # Ingil                  (yedisan_area; vanilla CRI)
            4540,   # Winnica                (podolia_volhynia_area; vanilla LIT)
        },
        no_ck3="vanilla: keeps vanilla's 1444.11.10 Hunyadi block",
        rank_note="CONTESTED. The Principality of Hungary under the Arpad was a "
                  "principality, not a kingdom, until 1000 - so 1 is the literal "
                  "answer, yet the realm is a major power in 867 and EU4 has no "
                  "tier between a duchy and a kingdom to say so. Kept at 1 on the "
                  "name; raise to 2 if a stronger starting Hungary is wanted."),

    Tag(tag="MON", rank=1, capital=138, ck3_title="c_duklja", in_alloc=True,
        provinces={
            138,   # Zeta                   (rascia_area; vanilla MON)
            4754,   # Kotor                  (rascia_area; vanilla VEN)
        },
        rank_note="Duklja under Miroslav, a coastal Serbian principality."),

    Tag(tag="PRU", rank=1, capital=1841, ck3_title="d_prussia", in_alloc=True,
        rank_note="Prussia from CK3's d_prussia: the Pruthenians, whom EU4 can "
                  "only seat in a Catholic duchy.",
        # Vanilla PRU holds nothing at 1444. Both Prussian areas are entirely the
        # Order's, so they pass across whole.
        areas=("east_prussia_area", "west_prussia_area")),

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
    Tag(tag="CRI", rank=1, capital=286, ck3_title=None,
        country="none", in_alloc=True,
        provinces={
            286,   # Azow                   (azov_area; vanilla GEN)
        },
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
    Tag(ruler_block=f"""
{CTRY_DATE} = {{
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
    tag="BOH", elector=True, rank=1, capital=266, ck3_title=None, in_alloc=False,
        no_ck3="mod-invented: Borivoj is the mod's own Bohemian ruler; CK3 "
               "records no 867 holder for k_bohemia to verify against",
        rank_note="Bohemia: a duchy of the Empire under Borivoj I. Rank 1 is the "
                  "literal 867 answer and is NOT demotion for standing outside the "
                  "partition: Bohemia is a small march here for the ordinary "
                  "reason, that in 867 it was a small duchy."),

    Tag(tag="SAR", rank=1, capital=127, ck3_title="d_sardinia",
        ruler_title="c_arborea",
        rank_note="Sardinia, holding Sassari (127), Arborea (4735) and Cagliari "
                  "(2986). All three are in NOT_IMPERIAL_867, so Sardinia was "
                  "never part of the imperial core and releasing it changes "
                  "nothing about the 226 the empire decision requires. A duchy is "
                  "the right size: in 867 Sardinia is a Byzantine province "
                  "governed by the giudicati of Torres and Cagliari, not a "
                  "kingdom of its own. CK3's d_sardinia is vacant in 867, so the "
                  "ruler comes from c_arborea.",
        # Vanilla takes the island in 1420, so all three are ARA's until claimed.
        provinces={
            127,   # Sassari               (corsica_sardinia_area; vanilla ARA)
            2986,  # Cagliari              (corsica_sardinia_area; vanilla ARA)
            4735,  # Arborea               (corsica_sardinia_area; vanilla ARA)
        }),

    # -- the Papal State ---------------------------------------------------------
    # PAP holds Rome: 118 Roma is deliberately not taken, so it still holds one
    # province on the mod's own account. Its 867 holder is Pope Nicholas I
    # (CK3 7853, "Niccolo"), the one mapped character with NO dynasty and no
    # dynasty_house at all - which is historically ordinary, since the papacy is
    # not a hereditary house in CK3's model. So the name lifts and the dynasty
    # does not exist to lift; build.py treats a missing dynasty as a reason to
    # write none rather than to invent one.
    #
    # country="none" and no rank: PAP is tracked here so the CK3 audit can resolve
    # its title, but it is deliberately NOT a realm this mod maintains. It keeps
    # vanilla's Rome and vanilla's ruler, so there is nothing to sync a ruler into
    # and no tier to decide.
    # The Order's last three provinces, handed back out. Not realms of the mod's
    # own: no rank, no capital, no CK3 title, just the land.
    Tag(tag="BRA", elector=True, rank=None, country="elector", ck3_title=None,
        no_ck3="vanilla Brandenburg, given the Order's Neumark provinces; the "
               "mod runs no court of its own here",
        provinces={
            49,    # Neumark               (neumark_area; vanilla TEU)
            4747,  # Dramburg              (neumark_area; vanilla TEU)
        }),

    Tag(tag="POL", rank=None, country="none", ck3_title=None, in_alloc=True,
        no_ck3="vanilla Poland, given Torun back; the mod runs no court of its "
               "own here",
        provinces={
            1859,  # Torun                 (kuyavia_area; vanilla TEU)
        }),

    Tag(tag="KOL", elector=True, rank=None, country="elector", ck3_title=None, in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote"),
    Tag(tag="MAI", elector=True, rank=None, country="elector", ck3_title=None, in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote"),
    Tag(tag="PAL", elector=True, rank=None, country="elector", ck3_title=None, in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote"),
    Tag(tag="SAX", elector=True, rank=None, country="elector", ck3_title=None, in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote"),
    Tag(tag="TRI", elector=True, rank=None, country="elector", ck3_title=None, in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote"),
    Tag(tag="PAP", rank=None, capital=118, ck3_title="k_papal_state",
        country="none", in_alloc=False),
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

#: The seven electors of the HRE. Every realm here is stripped of its 1444 vote,
#: which is the whole of the mod's diplomacy with a dissolved empire.
IMPERIAL_ELECTORS: list = [t.tag for t in TAGS if t.elector]

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
#: The few realms whose ruler is read from a CK3 title other than their own.
RULER_TITLES: dict = {t.tag: t.ruler_title for t in TAGS if t.ruler_title}

#: Realms that own land but whose ruler is not CK3's to supply, with the reason.
#: Only for a realm this mod decides something about. A vanilla tag that owns land
#: is not in here and does not need to be: nothing in the mod touched it, so it
#: keeps its vanilla ruler. Listing those by hand would just be the vanilla game
#: data retyped, and would go stale the moment a province moved.
NOT_CK3: dict = {t.tag: t.no_ck3 for t in TAGS
                 if t.no_ck3 and t.tag not in TITLES}

#: The five kingdoms of the empire, in the order the mod presents them: West
#: Francia, Lotharingia, East Francia, Bavaria, Italy. Lusatia is deliberately not
#: here - it is a principality outside the empire, not a sixth kingdom.
#:
#: Stated rather than derived, because no single field picks these five out. Rank
#: gives four of them and misses Bavaria, which is a duchy; country gives them plus
#: Lusatia. Any rule that produced the set would be a rule that could also produce a
#: different one, which is what a named list avoids.
#:
#: This was a private literal in validate.py, where nothing connected it to the
#: order the realms are declared in. selfcheck below pins the two together.
EMPIRE_KINGDOMS: list = [t.tag for t in TAGS if t.imperial_kingdom]

#: Layer 1 of the allocation: which areas each realm takes whole. build.py
#: walks this to seed ownership, then layer 2 carves provinces back out.
AREA_OWNERS: dict = {t.tag: t.areas for t in TAGS if t.areas}

#: Layer 2 of the allocation: the province-level corrections, inverted back to the
#: province -> tag shape the allocator wants. Per-realm on the Tag, because the
#: reasoning is per-realm - Trieste is Italy's but Krain is Bavaria's.
#:
#: Venice's own province is NOT here. VEN is deliberately not a Tag (it is not a
#: realm this mod maintains) and provinces held by untracked tags stay declared
#: where the allocator reads them, in build.UNTRACKED_OWNERS.
PROVINCE_OWNERS: dict = {pid: t.tag for t in TAGS for pid in t.provinces}

#: Layer 3 as build.py consumes it: (tag, province ids), in declaration
#: order. These were once named blocks resolved by name at build time. The ids
#: are declared here, on the tag, so no block table can drift away from the
#: realm it describes.
TRANSFERS: tuple = tuple((t.tag, tuple(t.provinces)) for t in TAGS if t.provinces)


def selfcheck() -> None:
    """Fail loudly on a database that contradicts itself."""
    seen = set()
    managed = [t.tag for t in TAGS if t.managed]
    if managed[:len(EMPIRE_KINGDOMS)] != EMPIRE_KINGDOMS:
        raise ValueError(
            f"EMPIRE_KINGDOMS {EMPIRE_KINGDOMS} is not the first "
            f"{len(EMPIRE_KINGDOMS)} managed realms in declaration order "
            f"({managed[:len(EMPIRE_KINGDOMS) + 1]}) - the five kingdoms and the "
            f"order the mod presents them are meant to be the same list")

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
        if t.country not in ("fresh", "vanilla", "elector", "written", "none"):
            raise ValueError(f"{t.tag}: country={t.country!r} is not one of "
                             f"fresh/vanilla/elector/written/none")
        if t.country == "fresh" and not (t.capital and t.culture):
            raise ValueError(
                f"{t.tag}: a fresh realm needs capital and culture - build "
                f"cannot make them up")
        if t.country == "none" and t.rank is not None and not t.deferred:
            raise ValueError(
                f"{t.tag}: country none but rank {t.rank} - a realm with a "
                f"size writes a file")
        if t.country == "elector" and not t.elector:
            raise ValueError(
                f"{t.tag}: country elector, but the Tag is not flagged elector")
        if t.elector and t.country not in ("elector", "vanilla"):
            raise ValueError(
                f"{t.tag}: flagged elector but country {t.country} would leave "
                f"its 1444 vote in place")
        if (t.areas or t.provinces) and not t.in_alloc:
            raise ValueError(
                f"{t.tag}: declares {len(t.areas)} areas and "
                f"{len(t.provinces)} provinces but has in_alloc off - the "
                f"allocation would silently hand it nothing")
        if t.ruler_title and not t.ck3_title:
            raise ValueError(
                f"{t.tag}: ruler_title is set but ck3_title is not - a ruler "
                f"title only means something next to the realm title it overrides")
    missing = KEPT_REALMS - set(RANK) - set(DEFERRED_REALMS)
    if missing:
        raise ValueError(f"managed realms with neither a rank nor a deferral: "
                         f"{sorted(missing)}")
    for tag, blocks in TRANSFERS:
        if tag not in seen:
            raise ValueError(f"TRANSFERS names {tag}, which is not a Tag")


selfcheck()


#: Balaton, Krain and the Danube bend: Hungary keeps the basin, and these
#: three are carved out of it rather than added to it.
BALATON_RESERVED: tuple = (135, 1864, 4240)
