#!/usr/bin/env python3
"""Base-game events and decisions the mod keeps, and the script the mod writes: no tag references, no stray limits."""

import os
import re
from checks.report import note
from checks.context import COUNTRY_OUT, GAME, MOD


def kept_events_and_decisions() -> None:
    """Events carry no tag references; decisions carry no tag references; vanilla HRE electorate decisions stubbed dead."""
    print("\n== events carry no tag references ==")
    from steps.vanilla_scripts import all_known_tags, event_mentions_tag, split_event_blocks

    tagset = all_known_tags()
    vdir = os.path.join(GAME, "events")
    vanilla_events = {fn for fn in os.listdir(vdir) if fn.endswith(".txt")}
    edir = os.path.join(MOD, "events")
    n_files, dirty = 0, []
    for fn in sorted(os.listdir(edir)):
        if not fn.endswith(".txt") or fn not in vanilla_events:
            continue
        n_files += 1
        text = open(os.path.join(edir, fn), encoding="utf-8", errors="replace").read()
        for kind, lines in split_event_blocks(text):
            if kind == "event" and event_mentions_tag("\n".join(lines), tagset):
                dirty.append(fn)
                break
    note(not dirty, f"no tag-specific events in {n_files} files ({len(dirty)} dirty)")
    for b in dirty[:10]:
        print("        " + b)

    print("\n== decisions carry no tag references ==")
    from steps.vanilla_scripts import VANILLA_FORMATION_FILES, split_decision_blocks

    vddir = os.path.join(GAME, "decisions")
    vanilla_decs = {fn for fn in os.listdir(vddir) if fn.endswith(".txt")}
    ddir = os.path.join(MOD, "decisions")
    n_files, dirty = 0, []
    for fn in sorted(os.listdir(ddir)):
        if not fn.endswith(".txt") or fn not in vanilla_decs:
            continue
        if fn in VANILLA_FORMATION_FILES:
            continue
        n_files += 1
        text = open(os.path.join(ddir, fn), encoding="utf-8", errors="replace").read()
        for kind, key, lines in split_decision_blocks(text):
            if kind == "decision" and event_mentions_tag("\n".join(lines), tagset):
                dirty.append(f"{fn}:{key}")
                break
    note(not dirty, f"no tag-specific decisions in {n_files} files ({len(dirty)} dirty)")
    for b in dirty[:10]:
        print("        " + b)

    print("\n== vanilla HRE electorate decisions stubbed dead ==")
    from steps.vanilla_scripts import VANILLA_STUB_DECISION_FILES

    for fn, keys in sorted(VANILLA_STUB_DECISION_FILES.items()):
        text = open(
            os.path.join(ddir, fn), encoding="utf-8", errors="replace"
        ).read()
        dead = [
            k
            for k in keys
            if re.search(rf"^\s*{k}\s*=\s*\{{", text, re.M)
            and re.search(r"^\s*always\s*=\s*no", text, re.M)
        ]
        note(
            len(dead) == len(keys),
            f"{fn} stubbed dead ({len(dead)}/{len(keys)})",
        )


def custom_script_has_no_per_pid_limit_blocks() -> None:
    """Custom script has no per-pid limit blocks."""
    print("\n== custom script has no per-pid limit blocks ==")
    # A bare `PID = { ... }` effect block takes no `limit` child (the
    # engine rejects it and drops surrounding effects): condition province
    # work with `if = { limit = { PID = { ... } } }` (Brazil pattern) and
    # keep area scopes (which do take limits) for the rest. Only our own
    # files can carry the bug: vendored vanilla files stay byte-identical.
    import glob as _glob

    def _mod_only(subdir, vanilla_dir):
        vanilla = {
            fn for fn in os.listdir(vanilla_dir) if fn.endswith(".txt")
        }
        return sorted(
            p
            for p in _glob.glob(os.path.join(MOD, subdir, "*.txt"))
            if os.path.basename(p) not in vanilla
        )

    scope_bad = []
    for path in (
        _mod_only("events", os.path.join(GAME, "events"))
        + _mod_only("common/scripted_effects", os.path.join(GAME, "common", "scripted_effects"))
        + _mod_only("common/on_actions", os.path.join(GAME, "common", "on_actions"))
    ):
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"(?m)^\t*(\d+) = \{$", text):
            depth, i = 1, m.end()
            while depth > 0 and i < len(text):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            inner, d = text[m.end() : i], 0
            for ln in inner.splitlines():
                code = ln.split("#", 1)[0]
                if d == 0 and re.match(r"^\s*limit\s*=", code):
                    scope_bad.append(
                        f"{os.path.basename(path)}:{m.group(1)}"
                    )
                    break
                d += code.count("{") - code.count("}")
    note(not scope_bad, f"no per-pid limits in {len(scope_bad)} blocks ({len(scope_bad)} bad)")
    for b in scope_bad[:10]:
        print("        " + b)


def country_history_uses_vanilla_key_shapes() -> None:
    """Country history uses vanilla key shapes."""
    print("\n== country history uses vanilla key shapes ==")
    # EU4's country-history parser rejects `general = {`/`advisor = {`
    # ("Unknown effect type" in error.log - the block silently vanishes;
    # generals are `leader = { type = general }`, advisors belong in
    # history/advisors/). Guarded because tags.extra is hand-written and
    # this killed ADU's 867 general silently once.
    badkey = []
    for fn in sorted(os.listdir(COUNTRY_OUT)):
        if not fn.endswith(".txt"):
            continue
        text = open(os.path.join(COUNTRY_OUT, fn),
                    encoding="cp1252", errors="replace").read()
        for m in re.finditer(r"(?m)^\s*(general|advisor)\s*=\s*\{", text):
            badkey.append(f"{fn}: {m.group(0).strip()}")
    note(not badkey, "no general/advisor keys in country history"
         if not badkey else
         f"{len(badkey)} wrong-key country-history blocks")
    for b in badkey[:8]:
        print("        " + b)


def ages_wait_for_their_year() -> None:
    """No age can start before its own year: the game starts in 867, and the base game's ages assume 1444."""
    print("\n== ages wait for their year ==")
    text = open(os.path.join(MOD, "common", "ages", "00_default.txt"), encoding="cp1252", errors="replace").read()
    bad = []
    for m in re.finditer(r"(?ms)^(age_\w+) = \{\s*start = (\d+)(.*?)^\}", text):
        name, start, body = m.group(1), int(m.group(2)), m.group(3)
        cs = re.search(r"can_start = \{(.*?)\n\t\}", body, re.S)
        y = re.search(r"\byear = (\d+)", cs.group(1)) if cs else None
        if not y or int(y.group(1)) < start:
            bad.append(f"{name} (start {start}, can_start year {y.group(1) if y else 'none'})")
    note(not bad, "every age's can_start waits for the age's start year" + (": " + ", ".join(bad) if bad else ""))


def run() -> None:
    ages_wait_for_their_year()
    kept_events_and_decisions()
    custom_script_has_no_per_pid_limit_blocks()
    country_history_uses_vanilla_key_shapes()
