#!/usr/bin/env python3
"""The only script that touches tools/tags.db: every tool goes through here.

SQLAlchemy (engine/Session) serves the ORM layer in tagdb/models;
connect() serves the query users (addtag, culturelift, eu4, validate)
so connection setup lives in exactly one place.
"""

import os

from models import CoreDeny
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tags.db")


def session():
    """A SQLAlchemy session on the tag database. The caller owns the
    transaction: commit() to keep work, close() without commit to drop it."""
    return Session()


def core_deny_map():
    """{owner: {holders}} for the judged-dormant claim pairs."""
    s = Session()
    rows = s.query(CoreDeny.holder, CoreDeny.owner).all()
    s.close()
    denied = {}
    for holder, owner in rows:
        denied.setdefault(owner, set()).add(holder)
    return denied

engine = create_engine(f"sqlite:///{DB_PATH}")

event.listens_for(engine, "connect")(
    lambda conn, _record: conn.execute("PRAGMA foreign_keys=ON")
)

Session = sessionmaker(bind=engine)
