#!/usr/bin/env python3
"""The tag database: tools/tags.db, loaded into Tag dataclasses.

Every realm is one row on the tags table with its land, reforms and
suppression on their own tables - adding a tag is an INSERT, not a Python
edit. Each Tag here carries everything a realm may declare, custom or not:
the country file the mod writes, the definition and flag data for realms
vanilla has never heard of, and the land it holds in 867.
"""

from __future__ import annotations

import os
import re
from abc import ABC
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Optional

from db import DB_PATH, Session
from models import (
    Diplomacy as DiplomacyRow,
    Formable as FormableRow,
    FormableArea,
    FormableProvince,
    FormableRename,
    Friendship as FriendshipRow,
    Province as ProvinceRow,
    Rivalry as RivalryRow,
    SeedCore as SeedCoreRow,
    Tag as TagRow,
    TagArea,
    TagProvince,
    TagReform,
    TagSuppress,
    War as WarRow,
    WarSide as WarSideRow,
)


@dataclass(frozen=True)
class Tag(ABC):
    """Abstract realm: every landed, formable or releasable tag.

    Only the identity, rank, display name, CK3 title link and map colour
    live here; everything else belongs on the subclasses."""

    tag: str
    rank: int

    name: Optional[str] = None
    ck3_title: Optional[str] = None
    color: Optional[tuple] = None
    capital: Optional[int] = None

    def __post_init__(self):
        if type(self) is Tag:
            raise TypeError(
                "Tag is abstract - use LandedTag, FormableTag or ReleasableTag"
            )
        if hasattr(self, "provinces"):
            object.__setattr__(self, "provinces", frozenset(self.provinces))


@dataclass(frozen=True)
class LandedTag(Tag):
    """A realm holding land on the 867 start date."""

    culture: Optional[str] = None
    religion: Optional[str] = None
    ruler_title: Optional[str] = None
    areas: tuple = ()
    provinces: frozenset = field(default_factory=frozenset)
    government: str = "monarchy"
    technology_group: str = "western"
    reforms: tuple = ()
    extra: str = ""
    no_heir_sync: bool = False

    country_file: Optional[str] = None
    historical_score: int = 250
    revolutionary_colors: tuple = (5, 0, 10)
    historical_units: tuple = ()
    monarch_names: tuple = ()
    leader_names: tuple = ()
    ship_names: tuple = ()

    forms: Optional[str] = None
    decision: Optional[str] = None

    flag_from: Optional[str] = None
    flag_source: Optional[str] = None
    suppress: tuple = ()
    rivals: tuple = ()
    friends: tuple = ()


@dataclass(frozen=True)
class FormableTag(Tag):
    """A formable tag with its requirement land: EU4 areas plus explicit
    provinces. HLR-style dynamic requirements stay in code (empire_core)."""

    adj: Optional[str] = None
    areas: tuple = ()
    provinces: frozenset = field(default_factory=frozenset)
    percent: Optional[int] = None
    own_capital: bool = False
    home_capital: bool = False
    rank_required: Optional[int] = None
    culture: Optional[str] = None
    culture_group: tuple = ()
    renames: tuple = ()
    dynasty: Optional[str] = None
    exclusive: bool = False


@dataclass(frozen=True)
class ReleasableTag(Tag):
    """A tag that starts dead but can be released in-game. Unused for now."""


#: Tags that hold no land at the start date and enter play only through a
#: scripted release (the Jerusalem pattern: cores are seeded and `release`
#: creates the country - no rebels, no dormant cores, no pre-existence).
#: The Pecheneg successors sleep until magyar_settlement.1 releases them;
#: Dublin sleeps until rebels or a manual release wake it (cores seeded via
#: seed_cores). Listed here so validate exempts them from the
#: landed checks, and selfcheck fails any unlisted landless tag.
DORMANT = frozenset({"YED", "ODS", "DNI", "DUB", "GAL", "HUB", "TAE", "WNN", "JIA", "TNO", "NIP", "ADI", "HEN", "NIN", "TUV", "SIB", "OVO", "ARI", "DAI"})


#: CK3 title prefixes -> the government rank they imply. The declared
#: tags.rank IS this number (selfcheck enforces equality); h_ hegemon
#: realms are the only rank 5.
TITLE_TIER_RANK = {"c": 1, "d": 2, "k": 3, "e": 4, "h": 5}


def required_count(total: int, percent: Optional[int]) -> int:
    """How many of total requirement provinces a percent needs (rounded up,
    so the enacted share is never below the mark; NULL means all of it)."""
    pct = percent if percent is not None else 100
    return (total * pct + 99) // 100


def rank_of(t: Tag) -> int:
    """The EU4 government rank the CK3 title behind the tag implies
    (c_=county, d_=duchy, k_=kingdom, e_=empire, h_=hegemony -> ranks
    1-5; selfcheck also enforces declared rank == this). Falls back
    to the tag's declared rank when there is no CK3 title to read."""
    if t.ck3_title:
        got = TITLE_TIER_RANK.get(t.ck3_title.split("_", 1)[0])
        if got:
            return got
    return t.rank


MUSLIM_EU4 = {"sunni", "ibadi", "shiite"}


def ck3_government(t: Tag) -> str:
    """The CK3 government at the 867 start: the title history's own pick
    when it pins one (Byzantine themes are administrative), otherwise the
    engine's dynamic choice modelled through the EU4 government - tribal,
    theocratic, republic, clan for a Muslim monarchy, feudal for the rest.
    Also the `kar_gov_*` start flag country history carries."""
    from ck3 import title_government
    got = title_government(t.ck3_title) if t.ck3_title else None
    if got:
        return got
    g = (t.government or "monarchy").lower()
    if g == "tribal":
        return "tribal_government"
    if g == "theocracy":
        return "ecclesiastical_government"
    if g == "republic":
        return "republic_government"
    if (t.religion or "") in MUSLIM_EU4:
        return "clan_government"
    return "feudal_government"


@dataclass(frozen=True)
class Diplomacy:
    """One start-date relationship, written into history/diplomacy by
    step_diplomacy. `relation` is "vassal" for a plain vassalage, or the name
    of a subject type from common/subject_types (e.g. "appanage") which is
    then emitted as a dependency block."""

    liege: str
    subject: str
    relation: str = "vassal"


@dataclass(frozen=True)
class War:
    """One preset start-date war, written into history/wars by step_wars."""

    slug: str
    title: str
    cb: str
    goal: str
    goal_tag: Optional[str]
    goal_province: Optional[int]
    date: str
    attackers: tuple = ()
    defenders: tuple = ()


CTRY_DATE = "867.1.1"

ProvinceInfo = namedtuple("ProvinceInfo", "pid name culture religion fort")


def _grouped(rows, key, value=None):
    """{row.key: [row.value...]} in query order; value defaults to the row."""
    out = {}
    for r in rows:
        out.setdefault(getattr(r, key), []).append(r if value is None else value(r))
    return out


def _load() -> tuple[
    list[LandedTag],
    list[Diplomacy],
    dict[int, ProvinceInfo],
    list[FormableTag],
    list[War],
    dict[int, list],
]:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"{DB_PATH} is missing - the tag database lives in git")
    with Session() as s:
        rows = s.query(TagRow).order_by(TagRow.seq).all()
        areas = _grouped(s.query(TagArea).order_by(TagArea.area), "tag", lambda r: r.area)
        lands = _grouped(s.query(TagProvince).order_by(TagProvince.pid), "tag", lambda r: r.pid)
        reforms = _grouped(
            s.query(TagReform).order_by(TagReform.tag, TagReform.pos), "tag", lambda r: r.reform
        )
        suppress = _grouped(s.query(TagSuppress).order_by(TagSuppress.key), "tag", lambda r: r.key)
        seeds = _grouped(s.query(SeedCoreRow).order_by(SeedCoreRow.tag), "pid", lambda r: r.tag)
        rivals = _grouped(
            s.query(RivalryRow).order_by(RivalryRow.other), "tag", lambda r: r.other
        )
        friends = _grouped(
            s.query(FriendshipRow).order_by(FriendshipRow.other), "tag", lambda r: r.other
        )
        fareas = _grouped(
            s.query(FormableArea).order_by(FormableArea.area), "formable", lambda r: r.area
        )
        fprovs = _grouped(
            s.query(FormableProvince).order_by(FormableProvince.pid),
            "formable",
            lambda r: r.pid,
        )
        frenames = _grouped(
            s.query(FormableRename).order_by(FormableRename.culture, FormableRename.tag),
            "formable",
            lambda r: (r.culture, r.tag, r.name),
        )
        formables = [
            FormableTag(
                tag=r.tag,
                rank=r.rank,
                name=r.name,
                adj=r.adj,
                ck3_title=r.ck3_title,
                color=(r.color_r, r.color_g, r.color_b)
                if r.color_r is not None
                else None,
                areas=tuple(fareas.get(r.tag, ())),
                provinces=frozenset(fprovs.get(r.tag, ())),
                percent=r.percent,
                capital=r.capital,
                own_capital=bool(r.own_capital),
                home_capital=bool(r.home_capital),
                rank_required=r.rank_required,
                culture=r.culture,
                culture_group=tuple(r.culture_group.split())
                if r.culture_group
                else (),
                renames=tuple(frenames.get(r.tag, ())),
                dynasty=r.dynasty,
                exclusive=bool(r.exclusive),
            )
            for r in s.query(FormableRow).order_by(FormableRow.tag)
        ]
        dips = [
            Diplomacy(r.liege, r.subject, r.relation)
            for r in s.query(DiplomacyRow).order_by(
                DiplomacyRow.liege, DiplomacyRow.subject
            )
        ]
        sides: dict[str, dict[str, list]] = {}
        for r in s.query(WarSideRow).order_by(WarSideRow.war, WarSideRow.tag):
            sides.setdefault(r.war, {}).setdefault(r.side, []).append(r.tag)
        wars = [
            War(
                r.slug,
                r.title,
                r.cb,
                r.goal,
                r.goal_tag,
                r.goal_province,
                r.date,
                tuple(sides.get(r.slug, {}).get("attacker", ())),
                tuple(sides.get(r.slug, {}).get("defender", ())),
            )
            for r in s.query(WarRow).order_by(WarRow.slug)
        ]
        provs = {
            r.pid: ProvinceInfo(r.pid, r.name, r.culture, r.religion, bool(r.fort))
            for r in s.query(ProvinceRow).order_by(ProvinceRow.pid)
        }

    tags = [
        LandedTag(
            tag=r.tag,
            rank=r.rank,
            name=r.name,
            capital=r.capital,
            culture=r.culture,
            religion=r.religion,
            ck3_title=r.ck3_title,
            ruler_title=r.ruler_title,
            areas=tuple(areas.get(r.tag, ())),
            provinces=lands.get(r.tag, ()),
            government=r.government,
            technology_group=r.technology_group,
            reforms=tuple(reforms.get(r.tag, ())),
            extra=r.extra,
            no_heir_sync=r.no_heir_sync,
            color=(r.color_r, r.color_g, r.color_b) if r.color_r is not None else None,
            country_file=r.country_file,
            historical_score=r.historical_score,
            revolutionary_colors=(r.rev_r, r.rev_g, r.rev_b),
            historical_units=tuple(r.historical_units),
            monarch_names=tuple(tuple(p) for p in r.monarch_names),
            leader_names=tuple(r.leader_names),
            ship_names=tuple(r.ship_names),
            forms=r.forms,
            decision=r.decision,
            flag_from=r.flag_from,
            flag_source=r.flag_source,
            suppress=tuple(suppress.get(r.tag, ())),
            rivals=tuple(rivals.get(r.tag, ())),
            friends=tuple(friends.get(r.tag, ())),
        )
        for r in rows
    ]
    return tags, dips, provs, formables, wars, seeds


TAGS, DIPLOMACY, PROVINCES, FORMABLES, WARS, SEED_CORES = _load()

BY_TAG: dict[str, LandedTag] = {t.tag: t for t in TAGS}

BY_FORMABLE: dict[str, FormableTag] = {f.tag: f for f in FORMABLES}

FORMABLE_TAGS: set = set(BY_FORMABLE)

KEPT_REALMS: set = {t.tag for t in TAGS}

RANK: dict = {t.tag: rank_of(t) for t in TAGS}

TITLES: dict = {t.tag: t.ck3_title for t in TAGS if t.ck3_title}

RULER_TITLES: dict = {t.tag: t.ruler_title for t in TAGS if t.ruler_title}

DIPLOMACY: tuple = tuple(DIPLOMACY)

AREA_OWNERS: dict = {t.tag: t.areas for t in TAGS if t.areas}

PROVINCE_OWNERS: dict = {pid: t.tag for t in TAGS for pid in t.provinces}


_GROUPS: dict[str, list[str]] = {}


def culture_groups() -> dict[str, list[str]]:
    """Top-level group -> member cultures, parsed from the mod's own
    cultures file: the single source of truth, read once per process."""
    global _GROUPS
    if not _GROUPS:
        path = os.path.join(
            os.path.dirname(DB_PATH),
            "..",
            "common",
            "cultures",
            "00_cultures.txt",
        )
        depth = 0
        cur = None
        with open(path, encoding="cp1252", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                m = re.match(r"^([a-z_]+)\s*=\s*\{", s)
                if m and depth == 0:
                    cur = m.group(1)
                    _GROUPS[cur] = []
                elif m and depth == 1 and cur is not None:
                    _GROUPS[cur].append(m.group(1))
                depth += line.count("{") - line.count("}")
    return _GROUPS


def selfcheck() -> None:
    seen = set()
    known = {t.tag for t in TAGS}
    for d in DIPLOMACY:
        if d.liege not in known or d.subject not in known or d.liege == d.subject:
            raise ValueError(
                f"{d.liege} -> {d.subject}: a Diplomacy must link two different "
                f"known tags"
            )
    for w in WARS:
        if not w.attackers or not w.defenders:
            raise ValueError(f"war {w.slug}: needs attackers and defenders")
        for s in w.attackers + w.defenders:
            if s not in known:
                raise ValueError(f"war {w.slug}: unknown side {s}")
        if bool(w.goal_tag) == bool(w.goal_province):
            raise ValueError(
                f"war {w.slug}: needs exactly one of goal_tag/goal_province"
            )
        if w.goal_tag and w.goal_tag not in known:
            raise ValueError(f"war {w.slug}: unknown goal tag {w.goal_tag}")

    for t in TAGS:
        if t.tag in seen:
            raise ValueError(f"{t.tag}: declared twice in the database")
        seen.add(t.tag)
        if not (t.capital and t.culture and t.religion):
            raise ValueError(
                f"{t.tag}: needs capital, culture and religion - build "
                f"cannot make them up"
            )
        if not (t.rank and 1 <= t.rank <= 5):
            raise ValueError(
                f"{t.tag}: needs a government rank 1..5 - the explicit tier "
                f"anchor for government_names titles"
            )
        if not t.ck3_title:
            raise ValueError(
                f"{t.tag}: needs ck3_title - every TAG must have a real CK3 "
                f"title; the ruler_title lane is deprecated"
            )
        want = TITLE_TIER_RANK.get(t.ck3_title[:1])
        if want and t.rank != want:
            raise ValueError(
                f"{t.tag}: rank {t.rank} but {t.ck3_title} implies rank "
                f"{want} - the tier the CK3 title grants is what ranks"
            )
        if t.forms and not t.decision:
            raise ValueError(f"{t.tag}: forms is set, so decision must be too")
        if t.forms and t.forms not in BY_FORMABLE:
            raise ValueError(f"{t.tag}: forms {t.forms}, which is no formable")
        if not t.provinces and not t.areas and t.tag not in DORMANT:
            raise ValueError(
                f"{t.tag}: holds no land - either give it provinces or list "
                f"it in DORMANT"
            )
        if t.tag in DORMANT and (t.provinces or t.areas):
            raise ValueError(
                f"{t.tag}: listed DORMANT but holds land - dormant tags "
                f"enter play only through their scripted release"
            )
    for fb in FORMABLES:
        if not fb.areas and not fb.provinces and fb.tag != "HLR":
            raise ValueError(
                f"formable {fb.tag}: needs areas or provinces (HLR alone "
                "takes its requirement from empire_core)"
            )
        if fb.own_capital and not fb.capital:
            raise ValueError(
                f"formable {fb.tag}: own_capital is set but capital is not"
            )
        if fb.own_capital and fb.home_capital:
            raise ValueError(
                f"formable {fb.tag}: own_capital and home_capital exclude each other"
            )
    starters: dict[str, list] = {}
    for t in TAGS:
        if t.forms:
            starters.setdefault(t.forms, []).append(t)
    for fcode, sts in starters.items():
        keys = {s.decision for s in sts}
        if len(keys) != 1:
            raise ValueError(
                f"formable {fcode}: starters share one decision, got {keys}"
            )
        fb = BY_FORMABLE[fcode]
        if fb.culture:
            off = sorted({s.tag for s in sts
                          if s.culture not in fb.culture.split()})
            if off:
                raise ValueError(
                    f"formable {fcode}: {off} are not {fb.culture}"
                )
        if fb.culture_group:
            want = {
                c for g in fb.culture_group for c in culture_groups().get(g, [])
            }
            off = sorted({s.tag for s in sts if s.culture not in want})
            if off:
                raise ValueError(
                    f"formable {fcode}: {off} are in none of "
                    f"{sorted(fb.culture_group)}"
                )
        for culture, stag, name in fb.renames:
            if bool(culture) == bool(stag) or not name:
                raise ValueError(
                    f"formable {fcode}: a rename sets exactly one of "
                    "culture/tag, plus a name"
                )
            if stag and stag not in {s.tag for s in sts}:
                raise ValueError(
                    f"formable {fcode}: rename tag {stag} is no starter"
                )
            if culture and culture not in {s.culture for s in sts}:
                raise ValueError(
                    f"formable {fcode}: rename culture {culture} "
                    "covers no starter"
                )


selfcheck()
