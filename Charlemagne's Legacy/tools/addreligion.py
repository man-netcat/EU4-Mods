#!/usr/bin/env python3
"""Add a new religion the whole way: block, loc, DB, icon strips, gfx.

Usage: python3 tools/addreligion.py KEY [--faith NAME] [--clone SRC]
       [--into GROUP] [--after SIBLING] [--name STR] [--desc STR]
       [--color R G B] [--icon N] [--holy-sites PID ...] [--heretics X ...]
       [--icon-only]

The four house religion-icon strips
(gfx/interface/{icon_religion,country_icon_religion,icon_religion_small,
province_view_religion}.dds) are extended in place, row by row (BGRA,
uncompressed exactly like vanilla): the CK3 icon
(game/gfx/interface/icons/faith/<faith>.dds, resolved by --faith or a
path) is decoded, row-strided onto every strip at that strip's frame
size, and the noOfFrames lines of the religion sprites in
interface/countryview.gfx (three sprites), interface/ledger.gfx and
interface/provinceview.gfx are bumped to match. The religion's `icon`
value is the NEW 1-based frame count (the last frame). Vanilla
references must be re-synced after a base-game patch - validate guards
both side.

Everything already done for a KEY is left alone, so a call is safe to
re-run after a step failed. The religion block comes from --clone SRC
(copy SRC's block, rekey, insert into --into GROUP after --after
SIBLING, otherwise just before the group's harmonized_modifier line),
or is patched in place when the KEY already exists in
common/religions/00_religion.txt. Loc goes to
localisation/replace/karolingian_religion_l_english.yml (name + desc,
BOM kept), the registry to tools/tags.db.
"""
import argparse
import os
from paths import CK3_GAME
import re
import sqlite3
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CK3 = CK3_GAME
MOD = os.path.join(HERE, "..")
REL_FILE = os.path.join(MOD, "common", "religions", "00_religion.txt")
LOC_FILE = os.path.join(MOD, "localisation", "replace",
                        "karolingian_religion_l_english.yml")
DB = os.path.join(HERE, "tags.db")

STRIPS = [
    ("gfx/interface/icon_religion.dds", 64),
    ("gfx/interface/country_icon_religion.dds", 64),
    ("gfx/interface/icon_religion_small.dds", 32),
    ("gfx/interface/province_view_religion.dds", 32),
]
GFX_FILES = ["interface/countryview.gfx", "interface/ledger.gfx",
             "interface/provinceview.gfx"]


def read_dds(path):
    data = open(path, "rb").read()
    if data[:4] != b"DDS ":
        sys.exit(f"{path}: not a DDS")
    h, w = struct.unpack("<II", data[12:20])
    fourcc = data[84:88]
    if fourcc != b"\x00\x00\x00\x00":
        sys.exit(f"{path}: compressed DDS (fourcc {fourcc!r}) - decode by hand")
    body = data[128:128 + w * h * 4]
    if len(body) != w * h * 4:
        sys.exit(f"{path}: body is {len(body)} bytes, not {w * h * 4}")
    return h, w, data[:128], body


def ck3_icon_path(name):
    if os.path.isabs(name) or os.sep in name:
        return name if os.path.exists(name) else None
    cand = os.path.join(CK3, "gfx", "interface", "icons", "faith",
                        name if name.endswith(".dds") else name + ".dds")
    return cand if os.path.exists(cand) else None


def append_frames(icon_path):
    """Append the icon as the last frame of every strip, row-strided,
    and bump the gfx noOfFrames lines. Returns the new 1-based icon."""
    from PIL import Image
    src = Image.open(icon_path).convert("RGBA")
    icon = None
    for rel, frame in STRIPS:
        path = os.path.join(MOD, rel)
        h, w, head, body = read_dds(path)
        assert w % frame == 0, f"{rel}: width {w} not a multiple of {frame}"
        fc = w // frame
        if icon is None:
            icon = fc + 1
        head = bytearray(head)
        # resample the CK3 icon to this strip's frame size, then build
        # the frame's BGRA rows
        small = src.resize((frame, frame), Image.LANCZOS)
        rows = []
        for y in range(frame):
            line = bytearray()
            for x in range(frame):
                r, g, b, a = small.getpixel((x, y))
                line += bytes((b, g, r, a))
            rows.append(bytes(line))
        # extend row by row: each old row keeps its bytes and gains the
        # frame's row; a contiguous append would garble the icons
        step = w * 4
        out = bytearray()
        for i in range(h):
            out += body[i * step:(i + 1) * step]
            out += rows[i]
        assert len(out) == (w + frame) * h * 4
        struct.pack_into("<II", head, 12, h, w + frame)
        with open(path, "wb") as fh:
            fh.write(bytes(head) + bytes(out))
        print(f"  {rel}: {fc} -> {fc + 1} frames ({frame}px)")
    old = icon - 1
    for rel in GFX_FILES:
        path = os.path.join(MOD, rel)
        t = open(path, encoding="cp1252").read()
        t2, n = re.subn(r"(?m)^(\t+noOfFrames\s*=\s*)%d\s*$" % old,
                        r"\g<1>%d" % icon, t)
        if not n:
            sys.exit(f"{rel}: no noOfFrames = {old} line at strip frame count")
        open(path, "w", encoding="cp1252", newline="").write(t2)
        print(f"  {os.path.basename(rel)}: {n} noOfFrames lines -> {icon}")
    return icon


def block_range(t, key):
    m = re.search(r"(?m)^\t%s = \{.*?^\t\}(?=\n)" % re.escape(key), t, re.S)
    return m


def patch_icon(key, icon):
    t = open(REL_FILE, encoding="cp1252").read().replace("\r\n", "\n")
    m = block_range(t, key)
    if not m:
        print(f"  {key}: no block in 00_religion.txt - nothing to patch")
        return False
    body = m.group(0)
    if not re.search(r"(?m)^\t\ticon\s*=", body):
        sys.exit(f"{key}: block has no icon line - add one first")
    nb = re.sub(r"(?m)^(\t\ticon\s*=\s*)\d+", r"\g<1>%d" % icon, body, count=1)
    if nb == body:
        print(f"  {key}: icon already {icon}")
        return True
    t = t.replace(m.group(0), nb, 1)
    open(REL_FILE, "w", encoding="cp1252", newline="").write(
        t.replace("\n", "\r\n"))
    print(f"  {key}: icon -> {icon}")
    return True


def clone_block(key, src, group, after, color, sites, heretics):
    t = open(REL_FILE, encoding="cp1252").read().replace("\r\n", "\n")
    if block_range(t, key):
        print(f"  {key}: block already present - skipping clone")
        return
    sm = block_range(t, src)
    if not sm:
        sys.exit(f"--clone {src}: source block not found")
    block = re.sub(r"^\t%s = \{" % re.escape(src),
                   r"\t%s = {" % key, sm.group(0), count=1)
    if color:
        block = re.sub(r"(?m)^(\t\tcolor\s*=\s*)\{\s*\d+\s+\d+\s+\d+\s*\}",
                       r"\g<1>{ %d %d %d }" % tuple(color), block, count=1)
    if sites:
        block = re.sub(r"(?m)^(\t\tholy_sites\s*=\s*\{)[^}]*\}",
                       r"\g<1> %s }" % " ".join(str(s) for s in sites),
                       block, count=1)
    if heretics:
        block = re.sub(r"(?m)^(\t\theretic\s*=\s*\{)[^}]*\}",
                       r"\g<1> %s }" % " ".join(heretics), block, count=1)
    if group:
        if after:
            am = block_range(t, after)
            if not am:
                sys.exit(f"--after {after}: sibling not found")
            pos = am.end()
            block = block + "\n"
        else:
            im = re.search(r"(?m)^\tharmonized_modifier = harmonized_%s\s*$"
                           % re.escape(group), t)
            if not im:
                sys.exit(f"--into {group}: no harmonized_modifier anchor")
            pos = im.start()
            block = block + "\n\n"
        t = t[:pos] + block + t[pos:]
    open(REL_FILE, "w", encoding="cp1252", newline="").write(
        t.replace("\n", "\r\n"))
    print(f"  {key}: cloned from {src}"
          + (f" into {group}" if group else "") +
          (f" after {after}" if after else ""))


def registry(key):
    con = sqlite3.connect(DB)
    if con.execute("select 1 from religions where name = ?",
                   (key,)).fetchone():
        print(f"  registry: {key} already present")
    else:
        con.execute("insert into religions values (?)", (key,))
        con.commit()
        print(f"  registry: {key} added")
    con.close()


def loc_keys(key, name, desc):
    t = open(LOC_FILE, encoding="utf-8-sig").read()
    if re.search(r"(?m)^ %s:" % re.escape(key), t):
        print(f"  loc: {key} already present")
        return
    end = t.rstrip("\n") + "\n"
    end += f" {key}:0 \"{name}\"\n {key}_desc:0 \"{desc}\"\n"
    open(LOC_FILE, "w", encoding="utf-8-sig", newline="").write(end)
    print(f"  loc: {key} + desc written")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("key")
    ap.add_argument("--faith", help="CK3 faith icon name or .dds path")
    ap.add_argument("--clone", help="religion whose block to copy")
    ap.add_argument("--into", help="religion group in 00_religion.txt")
    ap.add_argument("--after", help="sibling religion to insert after")
    ap.add_argument("--name")
    ap.add_argument("--desc")
    ap.add_argument("--color", nargs=3, type=int, metavar=("R", "G", "B"))
    ap.add_argument("--icon", type=int, help="set the icon value by hand "
                    "(default: the new last frame)")
    ap.add_argument("--holy-sites", nargs="+", type=int, metavar="PID")
    ap.add_argument("--heretics", nargs="+", metavar="HERETIC")
    ap.add_argument("--icon-only", action="store_true",
                    help="touch strips + icon line only, no loc/registry")
    a = ap.parse_args(argv)

    if a.clone:
        clone_block(a.key, a.clone, a.into, a.after, a.color,
                    a.holy_sites, a.heretics)
    elif a.color or a.holy_sites or a.heretics:
        print("note: --color/--holy-sites/--heretics apply only with --clone")

    if a.faith:
        p = ck3_icon_path(a.faith)
        if not p:
            sys.exit(f"CK3 icon for {a.faith} not found in the faith dir")
        icon = append_frames(p)
        print(f"  new icon value = {icon}")
    elif a.icon:
        icon = a.icon
    else:
        return 0
    if a.icon:
        icon = a.icon

    existing = block_range(
        open(REL_FILE, encoding="cp1252").read().replace("\r\n", "\n"),
        a.key)
    if existing:
        patch_icon(a.key, icon)
    elif not a.clone:
        sys.exit(f"{a.key}: block not in 00_religion.txt - pass --clone to "
                 "create it")
    if not a.icon_only:
        registry(a.key)
        name = a.name or a.key.capitalize()
        desc = a.desc or f"The {name} faith."
        loc_keys(a.key, name, desc)
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
