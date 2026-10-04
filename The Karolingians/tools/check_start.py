#!/usr/bin/env python3
"""Replay province history up to the start date and report the real owner.

The undated header of a province file is only a baseline: EU4 then fires every
dated entry up to and including the start date, in file order. A file can
therefore read "owner = ITA" and still hand the province to Venice on 1405.
This replays that so the mod is checked on the state the game will actually
produce, not on the text we wrote.
"""
import json, os, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

START = (1444, 11, 11)
MOD = str(HERE.parent)
PDIR = os.path.join(MOD, "history", "provinces")
# The allocation is not re-derived here. It comes from gen_provinces, which is
# the single specification of who owns what; this file's only job is to replay
# the written province files up to the start date and check the result. An
# earlier version read cache/alloc.json directly, which checked none of the
# eastern transfers because those live in the generator, and a still earlier one
# kept its own copy of the tag list, which drifted.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_provinces import ALL_TAGS as TAGS, build  # noqa: E402

DATE_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)\s*=\s*\{")
KV_RE = re.compile(r"\b(owner|controller|add_core|remove_core)\s*=\s*([A-Za-z0-9_]+)")
HRE_RE = re.compile(r"\bhre\s*=\s*(\w+)")


def split_header_and_blocks(lines):
    """Yield (date_or_None, block_text) for the header and each dated block."""
    i = 0
    n = len(lines)
    header = []
    while i < n and not DATE_RE.match(lines[i].strip()):
        header.append(lines[i])
        i += 1
    yield None, "\n".join(header)
    while i < n:
        m = DATE_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        date = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        depth = lines[i].count("{") - lines[i].count("}")
        body = [lines[i]]
        i += 1
        while i < n and depth > 0:
            depth += lines[i].count("{") - lines[i].count("}")
            body.append(lines[i])
            i += 1
        yield date, "\n".join(body)


def effective(text):
    """Owner/controller/cores as of START."""
    owner = controller = None
    cores = set()
    hre = None
    for date, block in split_header_and_blocks(text.splitlines()):
        if date is not None and date > START:
            continue
        for key, val in KV_RE.findall(block):
            if key == "owner":
                owner = val
            elif key == "controller":
                controller = val
            elif key == "add_core":
                cores.add(val)
            elif key == "remove_core":
                cores.discard(val)
        h = HRE_RE.search(block)
        if h:
            hre = h.group(1)
    return owner, controller, cores, hre


def main():
    alloc = build()
    expected = {}
    for t in TAGS:
        for p in alloc.get(t, []):
            expected[int(p)] = t

    bad_owner, bad_ctrl, bad_hre, contested = [], [], [], []
    for fn in sorted(os.listdir(PDIR)):
        pid = int(re.match(r"^(\d+)", fn).group(1))
        text = open(os.path.join(PDIR, fn), encoding="utf-8",
                    errors="surrogateescape").read()
        owner, controller, cores, hre = effective(text)
        want = expected.get(pid)
        if want is None:
            continue
        if owner != want:
            bad_owner.append((pid, fn, want, owner))
        if controller != want:
            bad_ctrl.append((pid, fn, want, controller))
        if hre == "yes":
            bad_hre.append((pid, fn))
        if want in cores:
            contested.append((pid, fn))

    print(f"provinces checked against the {START[0]}.{START[1]}.{START[2]} start: {len(expected)}")
    print(f"  owner    != intended : {len(bad_owner)}")
    print(f"  controller!= intended: {len(bad_ctrl)}")
    print(f"  hre = yes at start   : {len(bad_hre)}")
    for pid, fn, want, got in bad_owner[:20]:
        print(f"     {pid:5} {fn[:30]:30} want {want} got {got}")
    for pid, fn in bad_hre[:10]:
        print(f"     {pid:5} {fn[:30]:30} hre = yes")
    if bad_owner or bad_ctrl or bad_hre:
        print("\nFAIL: pre-1444 vanilla events still win at the start date")
        return 1
    print("\nOK: every intended province is held at the start date")
    return 0


if __name__ == "__main__":
    sys.exit(main())