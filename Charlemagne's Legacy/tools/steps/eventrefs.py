#!/usr/bin/env python3
"""No firing of an event that does not exist: the references the event cuts leave behind in the rest of the script.

The base game fires events from missions, on_actions, scripted effects, rebel types, disasters, parliament issues, imperial
reforms, incidents and government reforms. After `step_events` has dropped the events of other worlds those calls name
events nobody defines, and the game logs each one. This step writes an override of every such file with the dead calls
removed (a mission series that names a tag goes whole, like the decisions do); `dangling()` is what validate counts."""

import glob
import os
import re

from steps.layout import GAME, MOD
from steps.output import write_out
from steps.vanilla_scripts import all_known_tags, event_mentions_tag

CALL = re.compile(r"\b(country_event|province_event|news_event)\s*=\s*\{")
ID = re.compile(r'\bid\s*=\s*"?([A-Za-z_0-9.]+)"?')
LIST = re.compile(r"\b(random_events|events)\s*=\s*\{([^{}]*)\}")
SKIP_DIRS = ("events", "localisation", "gfx", "interface", "map", "history", "music", "sound", "tutorial", "decisions")


def _code(text):
    return "\n".join(ln.split("#", 1)[0] for ln in text.splitlines())


def defined_event_ids():
    """Every event id the mod defines (vendored vanilla events and its own)."""
    found = set()
    for path in glob.glob(os.path.join(MOD, "events", "*.txt")):
        for m in re.finditer(r"\b(?:country_event|province_event)\s*=\s*\{[^{}]*?\bid\s*=\s*\"?([\w.]+)\"?",
                             _code(open(path, encoding="utf-8", errors="replace").read())):
            found.add(m.group(1))
    return found


def _match_brace(text, open_at):
    depth = 0
    for i in range(open_at, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def strip_missing(text, defined):
    """(new text, calls removed): drop every event call whose id is not defined, and every undefined id in an
    `events = { }` / `random_events = { }` list. Comments are left alone."""
    removed = 0
    out, pos = [], 0
    for m in CALL.finditer(text):
        if m.start() < pos:
            continue
        end = _match_brace(text, m.end() - 1)
        body = _code(text[m.end():end])
        ident = ID.search(body)
        if ident and ident.group(1) not in defined:
            out.append(text[pos:m.start()])
            pos = end + 1
            removed += 1
    out.append(text[pos:])
    text = "".join(out)

    def fix(m):
        nonlocal removed
        kept = []
        for ln in m.group(2).splitlines(True):
            tok = re.match(r"^\s*(?:\d+\s*=\s*)?\"?([A-Za-z_0-9.]+)\"?\s*(?:#.*)?$", ln)
            if tok and tok.group(1) not in defined and not tok.group(1).isdigit():
                removed += 1
                continue
            kept.append(ln)
        return f"{m.group(1)} = {{{''.join(kept)}}}"

    return LIST.sub(fix, text), removed


def dangling(root_pairs=None):
    """{relative path: [undefined ids]} over the mod's own files and the base-game files the mod does not override."""
    defined = defined_event_ids()
    seen = {}
    for base in (MOD, GAME):
        for path in glob.glob(os.path.join(base, "**", "*.txt"), recursive=True):
            rel = os.path.relpath(path, base)
            if rel.split(os.sep)[0] in SKIP_DIRS or rel in seen:
                continue
            if base == GAME and os.path.exists(os.path.join(MOD, rel)):
                continue
            code = _code(open(path, encoding="utf-8", errors="replace").read())
            bad = []
            for m in CALL.finditer(code):
                ident = ID.search(code[m.end():_match_brace(code, m.end() - 1)])
                if ident and ident.group(1) not in defined:
                    bad.append(ident.group(1))
            for m in LIST.finditer(code):
                for ln in m.group(2).splitlines():
                    tok = re.match(r"^\s*(?:\d+\s*=\s*)?\"?([A-Za-z_0-9.]+)\"?\s*$", ln)
                    if tok and tok.group(1) not in defined and not tok.group(1).isdigit():
                        bad.append(tok.group(1))
            if bad:
                seen[rel] = bad
            else:
                seen[rel] = []
    return {k: v for k, v in seen.items() if v}


def _series(text):
    """Split a mission file into its top-level blocks: [(is_block, lines)]."""
    out, cur, depth = [], None, 0
    for ln in text.splitlines():
        code = ln.split("#", 1)[0]
        if cur is None:
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s*\{", ln.strip()) and depth == 0:
                cur = [ln]
                depth = code.count("{") - code.count("}")
                if depth <= 0:
                    out.append((True, cur))
                    cur, depth = None, 0
            else:
                out.append((False, [ln]))
        else:
            cur.append(ln)
            depth += code.count("{") - code.count("}")
            if depth <= 0:
                out.append((True, cur))
                cur, depth = None, 0
    if cur:
        out.append((True, cur))
    return out


def step_dangling():
    """Vendor the vanilla missions without the tag-specific series, then strip every call to a missing event."""
    tagset = all_known_tags()
    defined = defined_event_ids()
    # missions: a series that names a tag belongs to another world
    mdir = os.path.join(MOD, "missions")
    os.makedirs(mdir, exist_ok=True)
    vdir = os.path.join(GAME, "missions")
    series_cut = files = 0
    for fn in sorted(os.listdir(vdir)):
        if not fn.endswith(".txt"):
            continue
        text = open(os.path.join(vdir, fn), encoding="utf-8", errors="replace").read()
        keep = []
        for is_block, lines in _series(text):
            if is_block and event_mentions_tag("\n".join(lines), tagset):
                series_cut += 1
                continue
            keep.append("\n".join(lines))
        out, _n = strip_missing("\n".join(keep), defined)
        write_out(os.path.join(mdir, fn), out if out.endswith("\n") else out + "\n", encoding="utf-8", errors="strict")
        files += 1
    # every other file that still fires a missing event, vanilla or the mod's patched copy
    stripped = calls = 0
    for rel in sorted(dangling()):
        src = os.path.join(MOD, rel)
        if not os.path.exists(src):
            src = os.path.join(GAME, rel)
        text = open(src, encoding="utf-8", errors="replace").read()
        out, n = strip_missing(text, defined)
        write_out(os.path.join(MOD, rel), out, encoding="utf-8", errors="strict")
        stripped += 1
        calls += n
    left = dangling()
    print(f"missions: {files} files, {series_cut} tag-specific series dropped; {stripped} other files lost {calls} "
          f"calls to missing events; {sum(len(v) for v in left.values())} left")
    if left:
        raise SystemExit(f"still firing missing events: {dict(list(left.items())[:5])}")
