#!/usr/bin/env python3
"""SQLAlchemy models for tools/tags.db, the tag database.

One row per realm: every field a Tag can carry lives on the tags table, so a
new realm is one INSERT (plus its land rows) rather than a Python edit.
Province facts - which culture and religion it has in 867 - live on the
provinces table, with cultures and religions as their own lookup tables.
"""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tag(Base):
    __tablename__ = "tags"

    tag = Column(String, primary_key=True)
    seq = Column(Integer, nullable=False, unique=True)
    rank = Column(Integer, nullable=False)
    name = Column(String)
    capital = Column(Integer, ForeignKey("provinces.pid"))
    culture = Column(String, ForeignKey("cultures.name"))
    religion = Column(String, ForeignKey("religions.name"))
    ck3_title = Column(String)
    ruler_title = Column(String)

    government = Column(String, nullable=False, default="monarchy")
    technology_group = Column(String, nullable=False, default="western")
    extra = Column(Text, nullable=False, default="")
    no_heir_sync = Column(Boolean, nullable=False, default=False)

    # country definition data, written when vanilla has no definition for the tag
    color_r = Column(Integer)
    color_g = Column(Integer)
    color_b = Column(Integer)
    country_file = Column(String)
    historical_score = Column(Integer, nullable=False, default=250)
    rev_r = Column(Integer, nullable=False, default=5)
    rev_g = Column(Integer, nullable=False, default=0)
    rev_b = Column(Integer, nullable=False, default=10)
    historical_units = Column(JSON, nullable=False, default=list)
    monarch_names = Column(JSON, nullable=False, default=list)
    leader_names = Column(JSON, nullable=False, default=list)
    ship_names = Column(JSON, nullable=False, default=list)

    # formation: this tag can form another tag via a decision
    forms = Column(String)
    decision = Column(String)

    # flag to borrow when vanilla ships no flag for the tag
    flag_from = Column(String)
    flag_source = Column(String)


class TagArea(Base):
    __tablename__ = "tag_areas"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    area = Column(String, primary_key=True)


class TagProvince(Base):
    __tablename__ = "tag_provinces"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    pid = Column(Integer, ForeignKey("provinces.pid"), primary_key=True)


class TagReform(Base):
    __tablename__ = "tag_reforms"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    pos = Column(Integer, primary_key=True)
    reform = Column(String, nullable=False)


class Formable(Base):
    """A tag that does not exist at the start date but can be formed in-game.
    Requirements live on formable_areas (EU4 areas) and formable_provinces
    (explicit provinces); the HRE-style dynamic requirement stays in code."""

    __tablename__ = "formables"

    tag = Column(String, primary_key=True)
    name = Column(String)
    adj = Column(String)
    ck3_title = Column(String)
    rank = Column(Integer, nullable=False)
    color_r = Column(Integer)
    color_g = Column(Integer)
    color_b = Column(Integer)
    # percent of the requirement land needed to form (NULL = all of it)
    percent = Column(Integer)
    # would-be capital, held to form only when own_capital is set
    capital = Column(Integer, ForeignKey("provinces.pid"))
    # require holding the capital province to form
    own_capital = Column(Boolean, nullable=False, default=False)
    # require the firing tag's capital to sit inside the requirement land
    # (homeland rule for Denmark/Norway/Sweden); never with own_capital
    home_capital = Column(Boolean, nullable=False, default=False)
    # require an exact government rank to fire (Scandinavia: kings only)
    rank_required = Column(Integer)
    # primary culture that may fire the decision (NULL = listed starters only)
    culture = Column(String, ForeignKey("cultures.name"))
    # culture groups that may fire it, space-separated (GBR: the isles'
    # groups; NULL = not gated). Used instead of culture, never with it.
    culture_group = Column(String)
    # dynasty that may fire the decision (HLR: Karlings; NULL = not gated)
    dynasty = Column(String)
    # listed starters are mutually exclusive rivals: each may fire only
    # once the others are gone (Galicia-Volhynia: Halych/Volodymyr)
    exclusive = Column(Boolean, nullable=False, default=False)


class FormableArea(Base):
    __tablename__ = "formable_areas"

    formable = Column(String, ForeignKey("formables.tag"), primary_key=True)
    area = Column(String, primary_key=True)


class FormableProvince(Base):
    __tablename__ = "formable_provinces"

    formable = Column(String, ForeignKey("formables.tag"), primary_key=True)
    pid = Column(Integer, ForeignKey("provinces.pid"), primary_key=True)


class FormableRename(Base):
    """A rename for a formable: when the former is TAG or of CULTURE
    (exactly one set, "" means unset), the decision runs
    override_country_name with NAME (a loc key) - the Armenia pattern.
    Emitted most-specific first: tag rows, then culture rows."""

    __tablename__ = "formable_renames"

    formable = Column(String, ForeignKey("formables.tag"), primary_key=True)
    culture = Column(String, primary_key=True)
    tag = Column(String, primary_key=True)
    name = Column(String, nullable=False)


class TagSuppress(Base):
    __tablename__ = "tag_suppress"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    key = Column(String, primary_key=True)


class SeedCore(Base):
    """A dormant core seeded onto its province at build: the tag holds no
    land there (often no land at all), but rebels or a manual release can
    wake it. Dublin's cores on Sudreyjar-held Dyflin are the precedent."""

    __tablename__ = "seed_cores"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    pid = Column(Integer, ForeignKey("provinces.pid"), primary_key=True)


class CoreDeny(Base):
    """A judged-dormant claim: HOLDER keeps no cores on OWNER's land."""

    __tablename__ = "core_deny"

    holder = Column(String, ForeignKey("tags.tag"), primary_key=True)
    owner = Column(String, ForeignKey("tags.tag"), primary_key=True)


class Diplomacy(Base):
    __tablename__ = "diplomacy"

    liege = Column(String, ForeignKey("tags.tag"), primary_key=True)
    subject = Column(String, ForeignKey("tags.tag"), primary_key=True)
    relation = Column(String, nullable=False, default="vassal")


class Rivalry(Base):
    __tablename__ = "rivalries"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    other = Column(String, ForeignKey("tags.tag"), primary_key=True)


class Friendship(Base):
    __tablename__ = "friendships"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    other = Column(String, ForeignKey("tags.tag"), primary_key=True)


class War(Base):
    """A preset start-date war, written to history/wars by step_wars."""

    __tablename__ = "wars"

    slug = Column(String, primary_key=True)
    title = Column(String)
    cb = Column(String)
    goal = Column(String)
    goal_tag = Column(String, ForeignKey("tags.tag"))
    goal_province = Column(Integer)
    date = Column(String)


class WarSide(Base):
    __tablename__ = "war_sides"

    war = Column(String, ForeignKey("wars.slug"), primary_key=True)
    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    side = Column(String)


class Province(Base):
    __tablename__ = "provinces"

    pid = Column(Integer, primary_key=True)
    name = Column(String)
    culture = Column(String, ForeignKey("cultures.name"))
    religion = Column(String, ForeignKey("religions.name"))
    fort = Column(Boolean, nullable=False, default=False)
    # the province keeps (or gains) a vanilla fort in the generated file;
    # everything else is stripped, so Bessarabia-grade surprises need one
    # row here, not a build exception


class Culture(Base):
    __tablename__ = "cultures"

    name = Column(String, primary_key=True)


class Religion(Base):
    __tablename__ = "religions"

    name = Column(String, primary_key=True)
