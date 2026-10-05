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
    Tag(tag="FRA", name="West Francia", rank=3, capital=183, culture="frankish",
        ck3_title="k_france", in_alloc=True,
        rank_note="West Francia, the largest of the partitions, whose ruler "
                  "claimed to rule the Franks as a whole."),

    Tag(tag="LOT", country="fresh", name="Lotharingia", rank=2, capital=1878, culture="burgundian",
        ck3_title="k_lotharingia", in_alloc=True,
        rank_note="Lotharingia: a kingdom, though a hollow and contested one."),

    Tag(tag="GER", country="fresh", name="East Francia", rank=2, capital=1876, culture="hessian",
        ck3_title="k_east_francia", in_alloc=True,
        rank_note="East Francia: a kingdom ruled in its own right."),

    Tag(tag="ITA", country="fresh", name="Italy", rank=2, capital=4728, culture="lombard",
        ck3_title="k_italy", in_alloc=True,
        rank_note="Italy: Louis II was king of Italy as well as emperor, so Italy "
                  "is a kingdom held under an imperial claim, not the empire "
                  "itself."),

    Tag(tag="BAV", country="fresh", name="Bavaria", rank=1, capital=65, culture="bavarian",
        ck3_title="d_bavaria", in_alloc=True,
        rank_note="Bavaria is a DUCHY in 867, not a kingdom, and that is true "
                  "whether or not it is independent. Carloman governs it from "
                  "c. 863 but is not crowned king until 876, so a rank-2 Bavaria "
                  "would assert a crown nine years early. The realms are "
                  "independent by design - no vassalage anywhere in this mod - so "
                  "the tier is the only place any hierarchy is still expressed, "
                  "and it has to be right here."),

    Tag(tag="SOR", country="fresh", name="Lusatia", rank=1, capital=60, culture="sorbian",
        ck3_title="d_lausitz", in_alloc=True,
        rank_note="Lusatia: a Sorbian duchy, small in 867 on any measure."),

    # -- Iberia and the west -----------------------------------------------------
    Tag(tag="NAV", rank=2, capital=210, ck3_title="k_navarra", in_alloc=True,
        grants=(), rank_note="The Kingdom of Pamplona under Garcia I, a kingdom "
                             "in 867 and a peer of the Asturians."),

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
        rank_note="Silesia: a Piast duchy, small but not a titular one."),

    Tag(tag="GMA", rank=2, capital=4237, ck3_title="k_moravia", in_alloc=True,
        rank_note="Great Moravia under Rastislav, a kingdom in its own right."),

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
