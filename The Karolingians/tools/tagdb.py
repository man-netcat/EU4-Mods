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
from collections import namedtuple
from dataclasses import dataclass, field
from typing import Optional

from db import DB_PATH, Session
from models import (
    Diplomacy as DiplomacyRow,
    Province as ProvinceRow,
    Tag as TagRow,
    TagArea,
    TagFormArea,
    TagProvince,
    TagReform,
    TagSuppress,
)


@dataclass(frozen=True)
class Tag:

    tag: str
    rank: int

    name: Optional[str] = None
    capital: Optional[int] = None
    culture: Optional[str] = None
    religion: Optional[str] = None
    ck3_title: Optional[str] = None
    ruler_title: Optional[str] = None
    areas: tuple = ()
    provinces: frozenset = field(default_factory=frozenset)
    government: str = "monarchy"
    technology_group: str = "western"
    reforms: tuple = ()
    extra: str = ""
    no_heir_sync: bool = False

    color: Optional[tuple] = None
    country_file: Optional[str] = None
    historical_score: int = 250
    revolutionary_colors: tuple = (5, 0, 10)
    historical_units: tuple = ()
    monarch_names: tuple = ()
    leader_names: tuple = ()
    ship_names: tuple = ()

    forms: Optional[str] = None
    form_areas: tuple = ()
    form_rank: Optional[int] = None
    decision: Optional[str] = None

    flag_from: Optional[str] = None
    flag_source: Optional[str] = None
    suppress: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, "provinces", frozenset(self.provinces))


TITLE_TIER_RANK = {"c": 1, "d": 2, "k": 3, "e": 4}


def rank_of(t: Tag) -> int:
    """The EU4 government rank the CK3 title behind the tag implies
    (c_=county, d_=duchy, k_=kingdom, e_=empire -> ranks 1-4). Falls back
    to the tag's declared rank when there is no CK3 title to read."""
    if t.ck3_title:
        got = TITLE_TIER_RANK.get(t.ck3_title.split("_", 1)[0])
        if got:
            return got
    return t.rank


@dataclass(frozen=True)
class Diplomacy:
    """One start-date relationship, written into history/diplomacy by
    step_diplomacy. `relation` is "vassal" for a plain vassalage, or the name
    of a subject type from common/subject_types (e.g. "appanage") which is
    then emitted as a dependency block."""

    liege: str
    subject: str
    relation: str = "vassal"


CTRY_DATE = "867.1.1"

ProvinceInfo = namedtuple("ProvinceInfo", "pid name culture religion")


def _load() -> tuple[list[Tag], list[Diplomacy], dict[int, ProvinceInfo]]:
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"{DB_PATH} is missing - the tag database lives in git")
    with Session() as s:
        rows = s.query(TagRow).order_by(TagRow.seq).all()
        areas: dict[str, list] = {}
        for r in s.query(TagArea).order_by(TagArea.area):
            areas.setdefault(r.tag, []).append(r.area)
        lands: dict[str, list] = {}
        for r in s.query(TagProvince).order_by(TagProvince.pid):
            lands.setdefault(r.tag, []).append(r.pid)
        reforms: dict[str, list] = {}
        for r in s.query(TagReform).order_by(TagReform.tag, TagReform.pos):
            reforms.setdefault(r.tag, []).append(r.reform)
        forms: dict[str, list] = {}
        for r in s.query(TagFormArea).order_by(TagFormArea.area):
            forms.setdefault(r.tag, []).append(r.area)
        suppress: dict[str, list] = {}
        for r in s.query(TagSuppress).order_by(TagSuppress.key):
            suppress.setdefault(r.tag, []).append(r.key)
        dips = [
            Diplomacy(r.liege, r.subject, r.relation)
            for r in s.query(DiplomacyRow).order_by(
                DiplomacyRow.liege, DiplomacyRow.subject
            )
        ]
        provs = {
            r.pid: ProvinceInfo(r.pid, r.name, r.culture, r.religion)
            for r in s.query(ProvinceRow).order_by(ProvinceRow.pid)
        }

    tags = [
        Tag(
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
            form_areas=tuple(forms.get(r.tag, ())),
            form_rank=r.form_rank,
            decision=r.decision,
            flag_from=r.flag_from,
            flag_source=r.flag_source,
            suppress=tuple(suppress.get(r.tag, ())),
        )
        for r in rows
    ]
    return tags, dips, provs


TAGS, DIPLOMACY, PROVINCES = _load()

BY_TAG: dict[str, Tag] = {t.tag: t for t in TAGS}

ALL_TAGS: list[str] = [t.tag for t in TAGS]

KEPT_REALMS: set = {t.tag for t in TAGS}

RANK: dict = {t.tag: rank_of(t) for t in TAGS}

TITLES: dict = {t.tag: t.ck3_title for t in TAGS if t.ck3_title}

RULER_TITLES: dict = {t.tag: t.ruler_title for t in TAGS if t.ruler_title}

DIPLOMACY: tuple = tuple(DIPLOMACY)

AREA_OWNERS: dict = {t.tag: t.areas for t in TAGS if t.areas}

PROVINCE_OWNERS: dict = {pid: t.tag for t in TAGS for pid in t.provinces}

TRANSFERS: tuple = tuple((t.tag, tuple(t.provinces)) for t in TAGS if t.provinces)


def selfcheck() -> None:
    seen = set()
    known = {t.tag for t in TAGS}
    for d in DIPLOMACY:
        if d.liege not in known or d.subject not in known or d.liege == d.subject:
            raise ValueError(
                f"{d.liege} -> {d.subject}: a Diplomacy must link two different "
                f"known tags"
            )

    for t in TAGS:
        if t.tag in seen:
            raise ValueError(f"{t.tag}: declared twice in the database")
        seen.add(t.tag)
        if not (t.capital and t.culture and t.religion):
            raise ValueError(
                f"{t.tag}: needs capital, culture and religion - build "
                f"cannot make them up"
            )
        if t.ruler_title and not t.ck3_title:
            raise ValueError(
                f"{t.tag}: ruler_title is set but ck3_title is not - a ruler "
                f"title only means something next to the realm title it overrides"
            )
        if t.forms and not (t.form_areas and t.decision):
            raise ValueError(
                f"{t.tag}: forms is set, so form_areas and decision must be too"
            )
    for tag, blocks in TRANSFERS:
        if tag not in seen:
            raise ValueError(f"TRANSFERS names {tag}, which is not a Tag")


selfcheck()
