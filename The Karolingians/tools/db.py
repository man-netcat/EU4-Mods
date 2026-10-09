#!/usr/bin/env python3
"""Connection to tools/tags.db, the mod's tag database."""

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tags.db")

engine = create_engine(f"sqlite:///{DB_PATH}")

event.listens_for(engine, "connect")(
    lambda conn, _record: conn.execute("PRAGMA foreign_keys=ON")
)

Session = sessionmaker(bind=engine)
