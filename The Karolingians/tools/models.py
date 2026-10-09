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

    # formation: this tag is formed from other tags' land
    forms = Column(String)
    form_rank = Column(Integer)
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


class TagFormArea(Base):
    __tablename__ = "tag_form_areas"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    area = Column(String, primary_key=True)


class TagSuppress(Base):
    __tablename__ = "tag_suppress"

    tag = Column(String, ForeignKey("tags.tag"), primary_key=True)
    key = Column(String, primary_key=True)


class Diplomacy(Base):
    __tablename__ = "diplomacy"

    liege = Column(String, ForeignKey("tags.tag"), primary_key=True)
    subject = Column(String, ForeignKey("tags.tag"), primary_key=True)
    relation = Column(String, nullable=False, default="vassal")


class Province(Base):
    __tablename__ = "provinces"

    pid = Column(Integer, primary_key=True)
    name = Column(String)
    culture = Column(String, ForeignKey("cultures.name"))
    religion = Column(String, ForeignKey("religions.name"))


class Culture(Base):
    __tablename__ = "cultures"

    name = Column(String, primary_key=True)


class Religion(Base):
    __tablename__ = "religions"

    name = Column(String, primary_key=True)
