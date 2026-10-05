#!/usr/bin/env python3
"""Which tags this mod gives land to - a re-export, not a source.

The list itself moved into tagdb.py, where it is derived from the Tag objects:
ALL_TAGS is every tag whose land the mod hands out, which is not the same set as
the realms the mod maintains (BOH and SAR are maintained but keep vanilla's land).

This module stays because four scripts import ALL_TAGS by this name and there is
no reason to churn all of them at once. It deliberately no longer defines
EMPIRE_KINGDOMS: that list of five was how the old mod privileged five tags over
the rest, and nothing reads it any more. The empire's extent is defined by
geography in gen_provinces.EMPIRE_CORE_AREAS instead.
"""
from tagdb import ALL_TAGS  # noqa: F401
