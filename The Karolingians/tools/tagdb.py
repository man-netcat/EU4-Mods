#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Tag:

    tag: str

    name: Optional[str] = None
    rank: Optional[int] = None
    capital: Optional[int] = None
    culture: Optional[str] = None
    ck3_title: Optional[str] = None
    ruler_title: Optional[str] = None
    no_ck3: Optional[str] = None
    areas: tuple = ()
    deferred: Optional[str] = None
    in_alloc: bool = True
    provinces: frozenset = field(default_factory=frozenset)
    country: str = "vanilla"
    elector: bool = False
    imperial_kingdom: bool = False
    ruler_block: Optional[str] = None
    no_heir_sync: bool = False

    @property
    def managed(self) -> bool:
        return self.rank is not None

    @property
    def writes_country_file(self) -> bool:
        return self.deferred is None and self.rank is not None

    def __post_init__(self):
        object.__setattr__(self, "provinces", frozenset(self.provinces))

        if self.ck3_title is None and self.no_ck3 is None and self.deferred is None:
            raise ValueError(
                f"{self.tag}: ck3_title is None but neither no_ck3 nor deferred "
                f"explains it - give one or the other, so the gap is deliberate"
            )
        if (
            self.rank is None
            and not self.deferred
            and self.country not in ("none", "elector")
        ):
            raise ValueError(
                f"{self.tag}: a Tag must have a rank, be deferred, or declare "
                f'country "none" or "elector" - otherwise it is a realm of '
                f"unclear status"
            )


CTRY_DATE = "1444.1.1"

DYNASTY = "de Carolingie"
SHIFT = 577


def shifted(y, m=1, d=1):
    return f"{y + SHIFT}.{m}.{d}"


TAGS: list[Tag] = [
    Tag(
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
        tag="FRA",
        imperial_kingdom=True,
        name="West Francia",
        rank=2,
        capital=183,
        culture="frankish",
        ck3_title="k_france",
        in_alloc=True,
        areas=(
            "ile_de_france_area",
            "normandy_area",
            "loire_area",
            "orleans_area",
            "poitou_area",
            "guyenne_area",
            "languedoc_area",
            "massif_central_area",
            "pyrenees_area",
            "champagne_area",
            "picardy_area",
            "west_burgundy_area",
            "flanders_area",
        ),
        provinces=(
            192,  # Bourgogne (Dijon)  (bourgogne_area; vanilla BUR)
            197,  # Roussillon (Rosello)  (catalonia_area; vanilla ARA)
            212,  # Girona                 (catalonia_area; vanilla ARA)
            213,  # Barcelona              (catalonia_area; vanilla ARA)
            2987,  # Urgell                 (catalonia_area; vanilla ARA)
        ),
    ),
    Tag(
        ruler_block=f"""
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
        tag="LOT",
        imperial_kingdom=True,
        country="fresh",
        name="Lotharingia",
        rank=2,
        capital=1878,
        culture="burgundian",
        ck3_title="k_lotharingia",
        in_alloc=True,
        areas=(
            "lower_rhineland_area",
            "lorraine_area",
            "alsace_area",
            "wallonia_area",
            "brabant_area",
            "north_brabant_area",
            "holland_area",
            "frisia_area",
            "bourgogne_area",
            "romandie_area",
            "savoy_dauphine_area",
        ),
        provinces=(
            85,  # Koln
            84,  # Berg
            1743,  # Cambray
        ),
    ),
    Tag(
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
        tag="GER",
        imperial_kingdom=True,
        country="fresh",
        name="East Francia",
        rank=2,
        capital=1876,
        culture="hessian",
        ck3_title="k_east_francia",
        in_alloc=True,
        areas=(
            "hesse_area",
            "upper_rhineland_area",
            "palatinate_area",
            "north_rhine_area",
            "westphalia_area",
            "north_westphalia_area",
            "weser_area",
            "lower_saxony_area",
            "braunschweig_area",
            "thuringia_area",
            "northern_saxony_area",
            "lower_swabia_area",
            "upper_swabia_area",
            "switzerland_area",
            "franconia_area",
            "upper_franconia_area",
        ),
        provinces=(
            80,  # Trier
            1760,  # Koblenz
            62,  # Leipzig (Leipzig)  (south_saxony_area; vanilla THU)
        ),
    ),
    Tag(
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
        tag="BAV",
        imperial_kingdom=True,
        country="fresh",
        name="Bavaria",
        rank=1,
        capital=65,
        culture="bavarian",
        ck3_title="d_bavaria",
        in_alloc=True,
        areas=(
            "upper_bavaria_area",
            "lower_bavaria_area",
            "east_bavaria_area",
            "tirol_area",
            "austria_proper_area",
            "inner_austria_area",
        ),
        provinces=(
            4717,  # Bayreuth
            1868,  # Augsburg   (CK3 c_augsburg  -> d_augsburg -> k_bavaria)
            68,  # Memmingen  (CK3 barony Memmingen -> c_kempten -> d_augsburg)
            129,  # Krain      (carinthia_area; vanilla HAB)
            4751,  # Cilli      (carinthia_area; vanilla CLI)
        ),
    ),
    Tag(
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
        tag="ITA",
        imperial_kingdom=True,
        country="fresh",
        name="Italy",
        rank=2,
        capital=4728,
        culture="lombard",
        ck3_title="k_italy",
        in_alloc=True,
        areas=(
            "lombardy_area",
            "piedmont_area",
            "po_valley_area",
            "liguria_area",
            "venetia_area",
            "emilia_romagna_area",
            "tuscany_area",
            "provence_area",
            "carinthia_area",
        ),
        provinces=(
            4720,  # Geneva
            205,  # Savoie
            110,  # Trent      (tirol_area; vanilla TNT)
            2976,  # Umbria     (lazio_area; vanilla PGA)
            4731,  # Spoleto    (lazio_area; vanilla PAP)
            4732,  # Terracina  (lazio_area; vanilla PAP)
            119,  # Ancona     (central_italy_area; vanilla PAP)
            2977,  # Urbino    (central_italy_area; vanilla URB)
            1247,  # Corsica    (corsica_sardinia_area; vanilla GEN)
        ),
    ),
    Tag(
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
        tag="SOR",
        country="fresh",
        name="Lusatia",
        rank=1,
        capital=60,
        culture="sorbian",
        ck3_title="d_lausitz",
        in_alloc=True,
        areas=(
            "lusatia_area",
            "south_saxony_area",
        ),
        provinces=(2965,),  # Vogtland   (thuringia_area; vanilla THU)
    ),
    Tag(
        tag="NAV",
        rank=2,
        capital=210,
        ck3_title="k_navarra",
        in_alloc=True,
        provinces=(
            209,  # Vizcaya (Giscaya)   (basque_country; vanilla CAS)
            211,  # Huesca  (Osca)      (aragon_area;     vanilla ARA)
        ),
    ),
    Tag(
        tag="ASU",
        country="written",
        rank=2,
        capital=207,
        ck3_title="k_asturias",
        in_alloc=True,
        areas=("asturias_area", "galicia_area", "leon_area"),
        provinces={
            4789,  # Segovia                (castille_area; vanilla CAS)
        },
    ),
    Tag(
        tag="ADU",
        country="written",
        rank=2,
        capital=225,
        ck3_title="k_andalusia",
        in_alloc=True,
        areas=(
            "alentejo_area",
            "baleares_area",
            "beieras_area",
            "extremadura_area",
            "lower_andalucia_area",
            "toledo_area",
            "upper_andalucia_area",
            "valencia_area",
        ),
        provinces={
            214,  # Aragon                 (aragon_area; vanilla ARA)
            217,  # Madrid                 (castille_area; vanilla CAS)
            367,  # The Azores             (macaronesia_area; vanilla -)
            368,  # Madeira                (macaronesia_area; vanilla -)
            1751,  # Ceuta                  (northern_morocco_area; vanilla MOR)
            2755,  # Soria                  (castille_area; vanilla CAS)
            2988,  # Tarragona              (catalonia_area; vanilla ARA)
            2989,  # Rioja                  (basque_country; vanilla CAS)
            2990,  # Teruel                 (aragon_area; vanilla ARA)
            4551,  # Avila                  (castille_area; vanilla CAS)
            4557,  # Lleida                 (aragon_area; vanilla ARA)
        },
    ),
    Tag(
        tag="CRT",
        rank=1,
        capital=163,
        ck3_title="d_krete",
        in_alloc=True,
        provinces={
            163,  # Crete                  (morea_area; vanilla VEN)
        },
    ),
    Tag(
        tag="ARB",
        country="written",
        rank=3,
        capital=385,
        ck3_title="e_arabia",
        in_alloc=True,
        areas=(
            "al_jazira_area",
            "aleppo_area",
            "bahrain_area",
            "basra_area",
            "dulkadir_area",
            "iraq_arabi_area",
            "medina_area",
            "palestine_area",
            "syria_area",
            "syrian_desert_area",
            "tabuk_area",
            "trans_jordan_area",
        ),
        provinces={
            327,  # Adana                  (cukurova_area; vanilla RAM)
            331,  # Erzurum                (erzurum_area; vanilla AKK)
            385,  # Mecca                  (mecca_area; vanilla HED)
            412,  # Khuzestan              (khuzestan_area; vanilla MSY)
            415,  # Shahrizor              (shahrizor_area; vanilla TIM)
            416,  # Tabriz                 (tabriz_area; vanilla QAR)
            418,  # Diyarbakir             (north_kurdistan_area; vanilla AKK)
            419,  # Yerevan                (armenia_area; vanilla TIM)
            420,  # Ganja                  (armenia_area; vanilla QAR)
            2205,  # Nakhchivan             (armenia_area; vanilla TIM)
            2206,  # Urmia                  (tabriz_area; vanilla QAR)
            2207,  # Maragheh               (tabriz_area; vanilla QAR)
            2209,  # Ilam                   (luristan_area; vanilla TIM)
            2305,  # Erzincan               (erzurum_area; vanilla TIM)
            2306,  # Mush                   (north_kurdistan_area; vanilla AKK)
            4272,  # Jawf                   (nafud_area; vanilla ANZ)
            4289,  # Shushtar               (khuzestan_area; vanilla MSY)
            4290,  # Hoveyzeh               (khuzestan_area; vanilla MSY)
            4293,  # Arbil                  (shahrizor_area; vanilla QAR)
            4294,  # Sulimaniyeh            (shahrizor_area; vanilla TIM)
            4304,  # Khoy                   (tabriz_area; vanilla QAR)
        },
    ),
    Tag(
        tag="EGY",
        country="written",
        rank=2,
        capital=361,
        ck3_title="k_egypt",
        in_alloc=True,
        areas=(
            "al_wahat_area",
            "bahari_area",
            "cyrenaica_area",
            "delta_area",
            "gulf_of_arabia_area",
            "said_area",
            "vostani_area",
        ),
        provinces={
            1232,  # Suakin                 (red_sea_coast_area; vanilla MAM)
            2324,  # Halaib                 (red_sea_coast_area; vanilla MAM)
        },
    ),
    Tag(
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
        tag="SIL",
        rank=1,
        capital=264,
        ck3_title="d_lower_silesia",
        in_alloc=True,
        provinces=(
            264,  # Breslau (Wroclaw)    (silesia_area; vanilla OPL)
            4238,  # Liegnitz (Legnica)   (silesia_area; vanilla GLG)
            2966,  # Glogau   (Glogow)    (silesia_area; vanilla GLG)
        ),
    ),
    Tag(
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
        tag="GMA",
        rank=2,
        capital=4237,
        ck3_title="k_moravia",
        in_alloc=True,
        areas=("moravia_area", "slovakia_area"),
        provinces={
            263,  # Ratibor                (silesia_area; vanilla OPL)
            4723,  # Opole                  (silesia_area; vanilla OPL)
        },
    ),
    Tag(
        tag="DAL",
        country="written",
        rank=1,
        capital=136,
        ck3_title="d_dalmatia",
        in_alloc=True,
        provinces={
            136,  # Dalmatia               (east_adriatic_coast_area; vanilla DAL)
            4753,  # Zadar                  (east_adriatic_coast_area; vanilla DAL)
        },
    ),
    Tag(
        tag="BYZ",
        country="written",
        rank=3,
        capital=151,
        ck3_title="e_byzantium",
        in_alloc=True,
        areas=(
            "aegean_archipelago_area",
            "albania_area",
            "ankara_area",
            "aydin_area",
            "germiyan_area",
            "hudavendigar_area",
            "karaman_area",
            "kastamonu_area",
            "northern_greece_area",
            "rum_area",
        ),
        provinces={
            122,  # Apulia                 (apulia_area; vanilla NAP)
            145,  # Morea                  (morea_area; vanilla BYZ)
            146,  # Athens                 (morea_area; vanilla VEN)
            148,  # Thessaloniki           (macedonia_area; vanilla TUR)
            149,  # Edirne                 (thrace_area; vanilla TUR)
            151,  # Constantinople         (thrace_area; vanilla BYZ)
            285,  # Kaffa                  (crimea_area; vanilla GEN)
            321,  # Cyprus                 (cukurova_area; vanilla CYP)
            330,  # Trebizond              (erzurum_area; vanilla TRE)
            1773,  # Achaea                 (morea_area; vanilla ACH)
            1853,  # Kastoria               (macedonia_area; vanilla TUR)
            2302,  # Icel                   (cukurova_area; vanilla KAR)
            2410,  # Theodoro               (crimea_area; vanilla TRE)
            2447,  # Mantrega               (crimea_area; vanilla GEN)
            2757,  # Kaffa                  (southern_ethiopia_area; vanilla KAF)
            2982,  # Syracuse               (sicily_area; vanilla SIC)
            4701,  # Corinth                (morea_area; vanilla ACH)
            4702,  # Siroz                  (macedonia_area; vanilla TUR)
            4705,  # Gumulcine              (thrace_area; vanilla TUR)
            4779,  # Gallipoli              (thrace_area; vanilla TUR)
        },
    ),
    Tag(
        tag="BUL",
        country="written",
        rank=2,
        capital=150,
        ck3_title="k_bulgaria",
        in_alloc=True,
        areas=(
            "alfold_area",
            "bulgaria_area",
            "serbia_area",
            "silistria_area",
            "southern_transylvania_area",
            "transylvania_area",
            "wallachia_area",
        ),
        provinces={
            153,  # Pest                   (transdanubia_area; vanilla HUN)
            1756,  # Budjak                 (moldavia_area; vanilla MOL)
            1764,  # Burgas                 (thrace_area; vanilla TUR)
            1766,  # Kosovo                 (rascia_area; vanilla SER)
            1827,  # Raska                  (rascia_area; vanilla SER)
            3001,  # Skopje                 (macedonia_area; vanilla TUR)
            4126,  # Bacs                   (transdanubia_area; vanilla HUN)
            4173,  # Syrmia                 (slavonia_area; vanilla HUN)
            4780,  # Ohrid                  (macedonia_area; vanilla TUR)
        },
    ),
    Tag(
        tag="HUN",
        country="written",
        rank=1,
        capital=283,
        ck3_title=None,
        in_alloc=True,
        provinces={
            282,  # Yedisan                (yedisan_area; vanilla CRI)
            283,  # Zaporozhia             (zaporizhia_area; vanilla CRI)
            1943,  # Bratslav               (podolia_volhynia_area; vanilla LIT)
            1944,  # Cherkasy               (west_dniepr_area; vanilla LIT)
            2406,  # Ingil                  (yedisan_area; vanilla CRI)
            4540,  # Winnica                (podolia_volhynia_area; vanilla LIT)
        },
        no_ck3="vanilla: keeps vanilla's 1444.11.10 Hunyadi block",
    ),
    Tag(
        tag="MON",
        rank=1,
        capital=138,
        ck3_title="c_duklja",
        in_alloc=True,
        provinces={
            138,  # Zeta                   (rascia_area; vanilla MON)
            4754,  # Kotor                  (rascia_area; vanilla VEN)
        },
    ),
    Tag(
        tag="PRU",
        rank=1,
        capital=1841,
        ck3_title="d_prussia",
        in_alloc=True,
        areas=("east_prussia_area", "west_prussia_area"),
    ),
    Tag(
        tag="CRI",
        rank=1,
        capital=286,
        ck3_title=None,
        country="none",
        in_alloc=True,
        provinces={
            286,  # Azow                   (azov_area; vanilla GEN)
        },
        no_ck3="no 867 Crimean polity exists to map",
        deferred="no Crimean polity in 867: vanilla's file is a 1444 Golden "
        "Horde appanage",
    ),
    Tag(
        ruler_block=f"""
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
        tag="BOH",
        elector=True,
        rank=1,
        capital=266,
        ck3_title=None,
        in_alloc=False,
        no_ck3="mod-invented: Borivoj is the mod's own Bohemian ruler; CK3 "
        "records no 867 holder for k_bohemia to verify against",
    ),
    Tag(
        tag="SAR",
        rank=1,
        capital=127,
        ck3_title="d_sardinia",
        ruler_title="c_arborea",
        provinces={
            127,  # Sassari               (corsica_sardinia_area; vanilla ARA)
            2986,  # Cagliari              (corsica_sardinia_area; vanilla ARA)
            4735,  # Arborea               (corsica_sardinia_area; vanilla ARA)
        },
    ),
    Tag(
        tag="BRA",
        elector=True,
        rank=None,
        country="elector",
        ck3_title=None,
        no_ck3="vanilla Brandenburg, given the Order's Neumark provinces; the "
        "mod runs no court of its own here",
        provinces={
            49,  # Neumark               (neumark_area; vanilla TEU)
            4747,  # Dramburg              (neumark_area; vanilla TEU)
        },
    ),
    Tag(
        tag="POL",
        rank=None,
        country="none",
        ck3_title=None,
        in_alloc=True,
        no_ck3="vanilla Poland, given Torun back; the mod runs no court of its "
        "own here",
        provinces={
            1859,  # Torun                 (kuyavia_area; vanilla TEU)
        },
    ),
    Tag(
        tag="KOL",
        elector=True,
        rank=None,
        country="elector",
        ck3_title=None,
        in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote",
    ),
    Tag(
        tag="MAI",
        elector=True,
        rank=None,
        country="elector",
        ck3_title=None,
        in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote",
    ),
    Tag(
        tag="PAL",
        elector=True,
        rank=None,
        country="elector",
        ck3_title=None,
        in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote",
    ),
    Tag(
        tag="SAX",
        elector=True,
        rank=None,
        country="elector",
        ck3_title=None,
        in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote",
    ),
    Tag(
        tag="TRI",
        elector=True,
        rank=None,
        country="elector",
        ck3_title=None,
        in_alloc=False,
        no_ck3="vanilla elector; the mod only dissolves its vote",
    ),
    Tag(
        tag="PAP",
        rank=None,
        capital=118,
        ck3_title="k_papal_state",
        country="none",
        in_alloc=False,
    ),
]

BY_TAG: dict[str, Tag] = {t.tag: t for t in TAGS}


def _r(t: Tag):
    return t.tag


ALL_TAGS: list[str] = [t.tag for t in TAGS if t.in_alloc]

IMPERIAL_ELECTORS: list = [t.tag for t in TAGS if t.elector]

KEPT_REALMS: set = {t.tag for t in TAGS if t.managed}

DEFERRED_REALMS: dict = {t.tag: t.deferred for t in TAGS if t.deferred}

RANK: dict = {t.tag: t.rank for t in TAGS if t.rank is not None}

TITLES: dict = {t.tag: t.ck3_title for t in TAGS if t.ck3_title}

RULER_TITLES: dict = {t.tag: t.ruler_title for t in TAGS if t.ruler_title}

NOT_CK3: dict = {t.tag: t.no_ck3 for t in TAGS if t.no_ck3 and t.tag not in TITLES}

EMPIRE_KINGDOMS: list = [t.tag for t in TAGS if t.imperial_kingdom]

AREA_OWNERS: dict = {t.tag: t.areas for t in TAGS if t.areas}

PROVINCE_OWNERS: dict = {pid: t.tag for t in TAGS for pid in t.provinces}

TRANSFERS: tuple = tuple((t.tag, tuple(t.provinces)) for t in TAGS if t.provinces)


def selfcheck() -> None:
    seen = set()
    managed = [t.tag for t in TAGS if t.managed]
    if managed[: len(EMPIRE_KINGDOMS)] != EMPIRE_KINGDOMS:
        raise ValueError(
            f"EMPIRE_KINGDOMS {EMPIRE_KINGDOMS} is not the first "
            f"{len(EMPIRE_KINGDOMS)} managed realms in declaration order "
            f"({managed[:len(EMPIRE_KINGDOMS) + 1]}) - the five kingdoms and the "
            f"order the mod presents them are meant to be the same list"
        )

    for t in TAGS:
        if t.tag in seen:
            raise ValueError(f"{t.tag}: declared twice in TAGS")
        seen.add(t.tag)
        if t.ck3_title and t.no_ck3:
            raise ValueError(
                f"{t.tag}: both ck3_title and no_ck3 are set - CK3 is the "
                f"authority or it is not"
            )
        if t.country not in ("fresh", "vanilla", "elector", "written", "none"):
            raise ValueError(
                f"{t.tag}: country={t.country!r} is not one of "
                f"fresh/vanilla/elector/written/none"
            )
        if t.country == "fresh" and not (t.capital and t.culture):
            raise ValueError(
                f"{t.tag}: a fresh realm needs capital and culture - build "
                f"cannot make them up"
            )
        if t.country == "none" and t.rank is not None and not t.deferred:
            raise ValueError(
                f"{t.tag}: country none but rank {t.rank} - a realm with a "
                f"size writes a file"
            )
        if t.country == "elector" and not t.elector:
            raise ValueError(
                f"{t.tag}: country elector, but the Tag is not flagged elector"
            )
        if t.elector and t.country not in ("elector", "vanilla"):
            raise ValueError(
                f"{t.tag}: flagged elector but country {t.country} would leave "
                f"its 1444 vote in place"
            )
        if (t.areas or t.provinces) and not t.in_alloc:
            raise ValueError(
                f"{t.tag}: declares {len(t.areas)} areas and "
                f"{len(t.provinces)} provinces but has in_alloc off - the "
                f"allocation would silently hand it nothing"
            )
        if t.ruler_title and not t.ck3_title:
            raise ValueError(
                f"{t.tag}: ruler_title is set but ck3_title is not - a ruler "
                f"title only means something next to the realm title it overrides"
            )
    missing = KEPT_REALMS - set(RANK) - set(DEFERRED_REALMS)
    if missing:
        raise ValueError(
            f"managed realms with neither a rank nor a deferral: " f"{sorted(missing)}"
        )
    for tag, blocks in TRANSFERS:
        if tag not in seen:
            raise ValueError(f"TRANSFERS names {tag}, which is not a Tag")


selfcheck()

BALATON_RESERVED: tuple = (135, 1864, 4240)
