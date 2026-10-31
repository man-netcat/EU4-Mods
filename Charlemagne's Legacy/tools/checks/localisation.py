#!/usr/bin/env python3
"""Localisation files: they load, use glyphs EU4 renders, and cover every formable."""

import os
import re
from checks.report import note
from checks.context import FORMABLE_TAGS, GAME, MOD, TAGS, _REALMS


LOC = os.path.join(MOD, "localisation")


def localisation_files_load() -> None:
    """Localisation files load."""
    print("\n== localisation files load ==")
    for root, _dirs, files in os.walk(LOC):
        for fn in sorted(files):
            if not fn.endswith("_l_english.yml"):
                continue
            raw = open(os.path.join(root, fn), "rb").read()
            rel = os.path.relpath(os.path.join(root, fn), MOD)
            note(raw.startswith(b"\xef\xbb\xbf"), f"{rel} starts with a UTF-8 BOM")
            # A headerless file segfaults the loc parser at startup
            # (SLanguageData::AddKeyValuePair -> LocalizeYmlAddKey, no
            # language registered): the l_english: line must come first.
            body = raw[3:].decode("utf-8", errors="replace")
            head = next((ln for ln in body.splitlines()
                         if ln.strip() and not ln.strip().startswith("#")), "")
            note(head.strip() == "l_english:",
                 f"{rel} declares the l_english: header first (got {head.strip()!r})"
                 if head.strip() != "l_english:" else f"{rel} declares l_english: first")


def loc_values_use_glyphs_eu4_renders() -> None:
    """Loc values use glyphs EU4 renders."""
    print("\n== loc values use glyphs EU4 renders ==")
    # EU4's text pipeline drops any character its font set lacks (error.log
    # "Couldn't find Latin1 character" e.g. the CK3 macrons a-ogonek
    # title rows) while still rendering vanilla's Polish/Celtic marks, so
    # the honest baseline is the glyph set vanilla English loc itself uses.
    ALLOWED = {
        chr(c) for c in range(0x20, 0x7F)
    } | {
        chr(c) for c in range(0xA0, 0x100)
    }
    vdir = os.path.join(
        GAME,
        "localisation")
    for fn in sorted(os.listdir(vdir)):
        if not fn.endswith("_l_english.yml"):
            continue
        raw = open(os.path.join(vdir, fn), "rb").read()
        try:
            txt = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            txt = raw.decode("cp1252", errors="replace")
        ALLOWED |= set(txt)   # chars directly, not findall chunks
    ALLOWED |= {chr(c) for c in range(0x20, 0x7F)}
    # e-ogonek: beyond vanilla's set? proven rendered either way (never
    # logged as dropped with our Polish names live); keep it allowed so the
    # check measures what drops, not what lotr-writers used.
    ALLOWED |= set("ę")   # e-ogonek: renders (never logged, our Polish names live)
    ALLOWED |= set("Ł")   # capital L-stroke: renders the same way (no log drops)
    bad_glyph = []
    for root, _dirs, files in os.walk(LOC):
        for fn in sorted(files):
            if not fn.endswith("_l_english.yml"):
                continue
            for ln in open(os.path.join(root, fn), encoding="utf-8-sig").read().splitlines():
                if '"' not in ln:
                    continue
                val = ln.split('"')[1]
                bad = [c for c in val if c not in ALLOWED]
                if bad:
                    bad_glyph.append(
                        f"{fn}: {val.strip()!r} "
                        f"(unrenderable: {''.join(bad)!r} - the game drops "
                        f"the string, see error.log 'Couldn't find Latin1 "
                        f"character'; fold via encname)")
    note(not bad_glyph,
         f"all loc glyphs render ({len(bad_glyph)} bad)"
         if bad_glyph else "all loc glyphs render")
    for b in bad_glyph[:8]:
        print("        " + b)


def formables_carry_their_loc() -> None:
    """Formables carry their loc."""
    print("\n== formables carry their loc ==")
    allloc = ""
    for root, _dirs, files in os.walk(LOC):
        for fn in files:
            if fn.endswith("_l_english.yml"):
                allloc += open(os.path.join(root, fn),
                               encoding="utf-8-sig").read() + "\n"

    def has_loc(key):
        return re.search(rf"(?m)^ {re.escape(key)}:\d* ", allloc) is not None

    dkeys = sorted({t.decision for t in _REALMS if getattr(t, "decision", None)})
    missing = [f"{k}{suf}" for k in dkeys for suf in ("_title", "", "_desc")
               if not has_loc(f"{k}{suf}")]
    note(not missing, "every formation decision has title, name and desc loc"
         + (f" (missing: {', '.join(missing)})" if missing else ""))
    gameloc = ""
    gdir = os.path.join(GAME, "localisation")
    for fn in os.listdir(gdir):
        if fn.endswith("_l_english.yml"):
            gameloc += open(os.path.join(gdir, fn),
                            encoding="utf-8-sig").read() + "\n"
    unnamed = [f"{t}{suf}" for t in sorted(FORMABLE_TAGS) for suf in ("", "_ADJ")
               if not has_loc(f"{t}{suf}")
               and not re.search(rf"(?m)^ {t}{suf}:\d* ", gameloc)]
    note(not unnamed, "every formable tag has its name and adjective loc (ours or the base game's)"
         + (f" (missing: {', '.join(unnamed)})" if unnamed else ""))

    unnamed_landed = [f"{t}{suf}" for t in sorted(TAGS) for suf in ("", "_ADJ")
                      if not has_loc(f"{t}{suf}")
                      and not re.search(rf"(?m)^ {t}{suf}:\d* ", gameloc)]
    note(not unnamed_landed, "every landed tag has its name and adjective loc (ours or the base game's)"
         + (f" (missing: {', '.join(unnamed_landed)})" if unnamed_landed else ""))


def tag_names_are_unique() -> None:
    """No two tags of the mod show the same name (the Abbasid governors are not all "Abbasids")."""
    print("\n== tag names are unique ==")
    modloc = ""
    for root, _dirs, files in os.walk(LOC):
        for fn in files:
            if fn.endswith("_l_english.yml"):
                modloc += open(os.path.join(root, fn), encoding="utf-8-sig").read() + "\n"
    gameloc = ""
    gdir = os.path.join(GAME, "localisation")
    for fn in os.listdir(gdir):
        if fn.endswith("_l_english.yml"):
            gameloc += open(os.path.join(gdir, fn), encoding="utf-8-sig").read() + "\n"

    def name_of(tag, text):
        m = re.search(rf'(?m)^ {tag}:\d* "([^"]*)"', text)
        return m.group(1) if m else None

    names = {}
    for tag in sorted(set(TAGS) | set(FORMABLE_TAGS)):
        n = name_of(tag, modloc) or name_of(tag, gameloc)
        if n:
            names.setdefault(n, []).append(tag)
    starts = {t.tag: getattr(t, "forms", None) for t in _REALMS if getattr(t, "forms", None)}
    # a starter may share its name with the formable it forms (Bohemia and the Bohemian duchy)
    dups = {n: g for n, g in ((n, [t for t in ts if starts.get(t) not in ts]) for n, ts in names.items())
            if len(g) > 1}
    note(not dups, "no two tags share a name (a starter may share its formable's)"
         + ("".join(f" ({n}: {', '.join(ts)})" for n, ts in sorted(dups.items())) if dups else ""))


def _resolved_english():
    """{key: value} of the base game's English localisation with the mod's laid over it (the mod wins)."""
    loc = {}
    for base in (os.path.join(GAME, "localisation"), LOC):
        for root, _dirs, files in sorted(os.walk(base)):
            for fn in sorted(files):
                if fn.endswith("_l_english.yml"):
                    for m in re.finditer(r'(?m)^\s+([\w.\-]+):\d*\s+"(.*)"', open(os.path.join(root, fn), encoding="utf-8-sig", errors="replace").read()):
                        loc[m.group(1)] = m.group(2)
    return loc


def _grouped_keys(rel, member_marker):
    """(groups, members) of a common/ file whose top-level blocks are groups and whose second-level blocks holding
    `member_marker` are the members (cultures in culture groups, religions in religion groups)."""
    text = re.sub(r"#[^\n]*", "", open(os.path.join(MOD, rel), encoding="utf-8", errors="replace").read())
    groups, members, depth, stack, i = [], [], 0, [], 0
    for m in re.finditer(r"(\w+)\s*=\s*\{|[{}]", text):
        if m.group(0) == "}":
            depth -= 1
            stack.pop()
            continue
        if m.group(0) == "{":
            depth += 1
            stack.append(None)
            continue
        depth += 1
        stack.append((m.group(1), m.end()))
        if depth == 1:
            groups.append(m.group(1))
        elif depth == 2:
            end, d = m.end(), 1
            while d:
                d += {"{": 1, "}": -1}.get(text[end], 0)
                end += 1
            if re.search(rf"(?m)^\s*{member_marker}\b", text[m.end():end]):
                members.append(m.group(1))
    return groups, members


PARTICLES = {"of", "the", "de", "del", "della", "di", "da", "do", "la", "le", "al", "el", "bin", "ibn", "von", "van", "and", "y", "in", "ap", "an", "ul"}


def cultures_and_religions_are_named_and_capitalised() -> None:
    """Every culture, culture group, religion and religion group has an English name, and every word of it starts with a capital
    (small connecting words such as 'of' or 'de' excepted)."""
    print("\n== cultures, culture groups, religions and religion groups are named and capitalised ==")
    loc = _resolved_english()
    cgroups, cultures = _grouped_keys("common/cultures/00_cultures.txt", "male_names")
    rgroups, religions = _grouped_keys("common/religions/00_religion.txt", "icon")
    for label, keys in (("culture groups", cgroups), ("cultures", cultures), ("religion groups", rgroups), ("religions", religions)):
        missing = [k for k in keys if not loc.get(k, "").strip()]
        low = []
        for k in keys:
            name = loc.get(k, "")
            words = re.split(r"[\s\-]+", name.replace("\u00a7", " ")) if name else []
            for w in words:
                core = re.sub(r"^[^\w]+", "", w)
                if core and core[0].isalpha() and core[0].islower() and core.lower() not in PARTICLES:
                    low.append(f"{k}={name!r}")
                    break
        note(not missing and not low, f"{len(keys)} {label} are named and capitalised"
             + (f" ({len(missing)} unnamed: {', '.join(missing[:8])})" if missing else "")
             + (f" ({len(low)} not capitalised: {', '.join(low[:8])})" if low else ""))


def run() -> None:
    cultures_and_religions_are_named_and_capitalised()
    localisation_files_load()
    loc_values_use_glyphs_eu4_renders()
    formables_carry_their_loc()
    tag_names_are_unique()
