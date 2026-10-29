#!/usr/bin/env python3
"""Base-game events and decisions: keep what a 867 world can use, strip tag references, and neutralise the rest."""

import os
import re
from steps.layout import GAME, MOD
from steps.output import write_out


VANILLA_FORMATION_FILES = {
    # Vanilla decision file -> formation keys we neutralize there.
    "IrishNation.txt": ["irish_nation"],
    "EnglishNation.txt": ["english_nation"],
    "HungarianNation.txt": ["hungarian_nation"],
    "PolishNation.txt": ["polish_nation"],
    "BritishNation.txt": ["british_nation", "british_nation_diplomatically"],
    "MiscCountryFormations.txt": ["icelandic_nation"],
    "HRE_FormableNations.txt": ["pomerania_nation"],
    "ScandinavianNation.txt": ["scandinavian_nation"],
    "TibetanNation.txt": ["tibetan_nation"],
    "RestoreRomanEmpire.txt": ["restore_roman_empire"],
}


# Vanilla electorate decisions: 867 has no emperor and no electors (our
# history/diplomacy carries none), so the keys are stubbed dead by
# same-filename file override.
VANILLA_STUB_DECISION_FILES = {
    "ElectorateDecisions.txt": (
        "purchase_the_electorate",
        "request_the_electorate",
        "usurp_the_electorate",
    ),
}


def all_known_tags():
    """Every 3-letter tag vanilla can name. Ours are irrelevant here: we
    want vanilla's tag-specific content invalid, whatever names it uses."""
    found = set()
    vd = os.path.join(GAME, "common", "country_tags")
    for fn in os.listdir(vd):
        if fn.endswith(".txt"):
            found.update(
                re.findall(r"^([A-Z]{3})\s*=",
                           open(os.path.join(vd, fn), encoding="cp1252",
                                errors="replace").read(), re.M))
    return found


def event_mentions_tag(block, tagset):
    """True when an event block names any tag (comments stripped first, so
    prose like '# England wins' never counts)."""
    for ln in block.splitlines():
        code = ln.split("#", 1)[0]
        for tok in re.findall(r"\b([A-Z]{3})\b", code):
            if tok in tagset:
                return True
    return False


def split_event_blocks(text):
    """Yield (kind, lines) with kind 'event' for country_/province_event
    blocks and 'other' for everything else (namespace, headers, blanks)."""
    out, cur, depth = [], None, 0
    for ln in text.splitlines():
        s = ln.strip()
        if cur is None:
            if re.match(r"^(country_event|province_event)\s*=\s*\{", s):
                cur = [ln]
                code = ln.split("#", 1)[0]
                depth = code.count("{") - code.count("}")
                if depth <= 0:
                    out.append(("event", cur))
                    cur = None
            else:
                out.append(("other", [ln]))
        else:
            cur.append(ln)
            code = ln.split("#", 1)[0]
            depth += code.count("{") - code.count("}")
            if depth <= 0:
                out.append(("event", cur))
                cur = None
    if cur is not None:
        out.append(("event", cur))
    return out


def step_events() -> None:
    """Vendor vanilla events with tag-specific events cut out: any event
    naming a tag goes (it belongs to another century or a dead realm),
    everything generic stays byte-identical. Our own files (non-vanilla
    names) are never touched."""
    tagset = all_known_tags()
    vdir = os.path.join(GAME, "events")
    edir = os.path.join(MOD, "events")
    os.makedirs(edir, exist_ok=True)
    vanilla = {fn for fn in os.listdir(vdir) if fn.endswith(".txt")}
    kept_files, kept_events, dropped = 0, 0, 0
    for fn in sorted(vanilla):
        text = open(os.path.join(vdir, fn), encoding="utf-8",
                    errors="replace").read()
        segs = split_event_blocks(text)
        keep = []
        for kind, lines in segs:
            if kind == "event" and event_mentions_tag("\n".join(lines), tagset):
                dropped += 1
                continue
            keep.append(lines)
            if kind == "event":
                kept_events += 1
        body = ["\n".join(ls) for ls in keep]
        while len(body) > 1 and not body[-1].strip():
            body.pop()
        out = "\n".join(body)
        if not out.endswith("\n"):
            out += "\n"
        dest = os.path.join(edir, fn)
        old = None
        if os.path.exists(dest):
            old = open(dest, encoding="utf-8", errors="replace").read()
        if old != out:
            write_out(dest, out, encoding="utf-8", errors="strict")
        kept_files += 1
    print(f"events: {kept_files} files, {kept_events} generic events kept, "
          f"{dropped} tag-specific dropped")


def split_decision_blocks(text):
    """Yield (kind, key, lines): 'decision' for named blocks at the top
    level or directly inside the *_decisions wrappers, 'other' for
    wrappers, comments and blanks."""
    out, cur, key, base, depth = [], None, None, 0, 0
    for ln in text.splitlines():
        s = ln.strip()
        code = ln.split("#", 1)[0]
        opens = code.count("{") - code.count("}")
        if cur is None:
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{", s)
            if (
                m
                and m.group(1) not in ("if", "else", "else_if")
                and not m.group(1).endswith("_decisions")
                and depth <= 1
            ):
                cur, key, base = [ln], m.group(1), depth
                depth += opens
                if depth <= base:
                    out.append(("decision", key, cur))
                    cur, key = None, None
                continue
            depth += opens
            out.append(("other", None, [ln]))
        else:
            cur.append(ln)
            depth += opens
            if depth <= base:
                out.append(("decision", key, cur))
                cur, key = None, None
    if cur is not None:
        out.append(("decision", key, cur))
    return out


def step_filter_decisions() -> None:
    """Vendor vanilla decisions minus tag-specific ones: same-filename
    files win whole, so dropped keys stay dead. Files already curated by
    hand (VANILLA_FORMATION_FILES) are left alone, as are our own
    decisions (non-vanilla names)."""
    tagset = all_known_tags()
    vdir = os.path.join(GAME, "decisions")
    ddir = os.path.join(MOD, "decisions")
    os.makedirs(ddir, exist_ok=True)
    vanilla = {fn for fn in os.listdir(vdir) if fn.endswith(".txt")}
    kept_files, kept_decisions, dropped = 0, 0, []
    for fn in sorted(vanilla):
        if fn in VANILLA_FORMATION_FILES:
            continue
        if fn in VANILLA_STUB_DECISION_FILES:
            continue
        text = open(os.path.join(vdir, fn), encoding="utf-8",
                    errors="replace").read()
        segs = split_decision_blocks(text)
        body = []
        for kind, key, lines in segs:
            if kind == "decision" and event_mentions_tag("\n".join(lines), tagset):
                dropped.append(f"{fn}:{key}")
                continue
            body.append(lines)
            if kind == "decision":
                kept_decisions += 1
        out = "\n".join("\n".join(ls) for ls in body)
        if not out.endswith("\n"):
            out += "\n"
        dest = os.path.join(ddir, fn)
        old = None
        if os.path.exists(dest):
            old = open(dest, encoding="utf-8", errors="replace").read()
        if old != out:
            write_out(dest, out, encoding="utf-8", errors="strict")
        kept_files += 1
    print(f"decisions: {kept_files} files, {kept_decisions} kept, "
          f"{len(dropped)} tag-specific dropped")

    # Vanilla keys stubbed dead: same-filename file wins whole, and the
    # stubs (always-no potential, empty effect) do nothing for anyone.
    for fn, keys in sorted(VANILLA_STUB_DECISION_FILES.items()):
        stubs = "\n".join(
            f"\t{k} = {{\n"
            f"\t\tpotential = {{\n"
            f"\t\t\talways = no\n"
            f"\t\t}}\n"
            f"\t\tallow = {{\n"
            f"\t\t}}\n"
            f"\t\teffect = {{\n"
            f"\t\t}}\n"
            f"\t}}"
            for k in keys
        )
        sp = os.path.join(ddir, fn)
        write_out(
            sp,
            f"# dummy: 867 has no emperor and no electors\n"
            f"country_decisions = {{\n{stubs}\n}}\n",
        )
        print(f"wrote {sp} (stub, {len(keys)} keys dead)")
