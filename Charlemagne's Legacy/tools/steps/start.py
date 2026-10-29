#!/usr/bin/env python3
"""Checks after a build: probe the generated map and compare ownership at the start date with the database."""

import os
import re
from tagdb import CTRY_DATE, TITLES
from steps.allocation import build
from steps.layout import PDIR
from steps.parsing import effective


def step_start():
    alloc = build()
    expected = {}

    for t in TITLES:
        for p in alloc.get(t, []):
            expected[int(p)] = t

    bad_owner, bad_ctrl, contested = [], [], []
    for fn in sorted(os.listdir(PDIR)):
        pid = int(re.match(r"^(\d+)", fn).group(1))
        text = open(
            os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
        ).read()
        owner, controller, cores = effective(text)
        want = expected.get(pid)
        if want is None:
            continue
        if owner != want:
            bad_owner.append((pid, fn, want, owner))
        if controller != want:
            bad_ctrl.append((pid, fn, want, controller))
        if want in cores:
            contested.append((pid, fn))

    print(
        f"provinces checked against the {CTRY_DATE} start: {len(expected)}"
    )
    print(f"  owner    != intended : {len(bad_owner)}")
    print(f"  controller!= intended: {len(bad_ctrl)}")
    for pid, fn, want, got in bad_owner[:20]:
        print(f"     {pid:5} {fn[:30]:30} want {want} got {got}")
    if bad_owner or bad_ctrl:
        print("\nFAIL: vanilla events still win at the start date")
        return 1
    print("\nOK: every intended province is held at the start date")
    return 0
