#!/usr/bin/env python3
"""No firing of an event that does not exist: the references the event cuts leave behind in the rest of the script.

The base game fires events from missions, on_actions, scripted effects, rebel types, disasters, parliament issues, imperial
reforms, incidents and government reforms. After `step_events` has dropped the events of other worlds those calls name
events nobody defines, and the game logs each one. This step writes an override of every such file with the dead calls
removed; `dangling()` is what validate counts. Folders the descriptor `replace_path`s (missions, history, gfx/flags,
government names and ranks, cultures, bookmarks) load no base-game file, so base-game files there never count."""

import glob
import os
import re

from steps.layout import GAME, MOD
from steps.output import write_out

CALL = re.compile(r"\b(country_event|province_event|news_event)\s*=\s*\{")
ID = re.compile(r'\bid\s*=\s*"?([A-Za-z_0-9.]+)"?')
LIST = re.compile(r"\b(random_events|events)\s*=\s*\{([^{}]*)\}")
SKIP_DIRS = ("localisation", "gfx", "interface", "map", "history", "music", "sound", "tutorial")


def replaced_paths():
    """The `replace_path` entries of descriptor.mod: base-game files under them do not load."""
    text = open(os.path.join(MOD, "descriptor.mod"), encoding="utf-8").read()
    return tuple(p.replace("/", os.sep) for p in re.findall(r'(?m)^replace_path="([^"]+)"', text))


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
            if base == GAME and (os.path.exists(os.path.join(MOD, rel)) or rel.startswith(replaced_paths())):
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


def step_dangling():
    """Strip every call to a missing event from the files that still load."""
    defined = defined_event_ids()
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
    print(f"dangling events: {stripped} files lost {calls} calls to missing events; "
          f"{sum(len(v) for v in left.values())} left")
    if left:
        raise SystemExit(f"still firing missing events: {dict(list(left.items())[:5])}")
