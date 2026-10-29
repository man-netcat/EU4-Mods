#!/usr/bin/env python3
"""Writing generated files: one place that encodes and writes text and localisation."""

import os


def write_loc(path, pairs) -> None:
    """Write one generated localisation file: UTF-8 with BOM (the game
    ignores BOM-less files), one `key:0 "value"` pair per line."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        fh.write("l_english:\n")
        for k, v in pairs:
            fh.write(f' {k}:0 "{v}"\n')


def write_out(path, text, encoding="cp1252", errors="pdx"):
    """Write one generated file: cp1252 with the pdx handler like every
    generated game file (the events/decisions vendoring passes utf-8)."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    open(path, "w", encoding=encoding, errors=errors).write(text)
