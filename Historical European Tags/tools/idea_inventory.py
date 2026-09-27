#!/usr/bin/env python3
"""idea_inventory.py - inventory the base game's national idea sets.

`verify_releasables.py` checks mod idea groups against a fixed rule of
"2 traditions, 1 ambition, 7 ideas". That rule was a guess until this tool
measured it. It mines every group in the base game's `common/ideas/` and
reports what the engine actually ships, so the rule can be defended, cited
and tightened when the base game changes.

What it reports:

  * a census of all idea groups per file, classified by how they are granted
  * the modal shape: how many `start`, `bonus` and individual ideas
  * how heavy a single idea is allowed to be (modifiers per idea)
  * how often a group repeats one effect across its own traditions, ambition
    and ideas (the "silently doubled bonus" bug)
  * trigger styles and how many groups are tag-locked
  * every empty idea body, i.e. an idea the player sees with no effect

Usage:
    python3 idea_inventory.py [--game PATH] [--json] [--catalogue] [--group NAME]

`--catalogue` lists every group (the full inventory); `--group NAME` dumps one
group in full. `--json` emits the whole census for machine consumers, which
is how the verifier consumes it.

Exit code 0 always: this is a measurement tool, not a gate.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

DEFAULT_GAME = Path("/home/rick/Paradox/Games/Europa Universalis IV")

# A `name = number` line. Same shape the verifier uses.
MODIFIER_NAME_RE = re.compile(
    r"^\s*([a-z][a-z0-9_]*)\s*=\s*(-?[0-9.]+)\s*$", re.MULTILINE
)
TOP_LEVEL_RE = re.compile(r"^([A-Za-z_0-9]+) = \{", re.MULTILINE)

# Sub-blocks that hold scoring, not effects: `factor` repeats legitimately
# inside them, so they must be excluded before looking for doubled effects.
SCORING_KEYS = {"ai_will_do", "ai_will_do_tech", "trigger", "if", "else", "limit"}


def _balanced(text: str, open_idx: int) -> str | None:
    """Inner text of the {...} whose opening brace sits at `open_idx`."""
    depth = 0
    for j in range(open_idx, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : j]
    return None


def _extract_block(text: str, name: str) -> str | None:
    """Body of a top-level `name = { ... }` block, or None."""
    m = re.search(rf"^[ \t]*{re.escape(name)} = \{{", text, re.MULTILINE)
    if m is None:
        return None
    return _balanced(text, m.end() - 1)


def _sub_blocks(body: str) -> dict[str, str]:
    """Direct children of a block body, as name -> inner text."""
    out: dict[str, str] = {}
    for m in re.finditer(r"^[ \t]+([A-Za-z_0-9]+) = \{", body, re.MULTILINE):
        # a child may not be the first thing on its line, so only take
        # children that start at the left margin of the body
        line_start = body.rfind("\n", 0, m.start()) + 1
        if body[line_start : m.start()].strip():
            continue
        inner = _balanced(body, m.end() - 1)
        if inner is not None:
            out.setdefault(m.group(1), inner)
    return out


def _mods(text: str) -> list[str]:
    return [m.group(1) for m in MODIFIER_NAME_RE.finditer(text or "")]


def _content_lines(text: str) -> list[str]:
    """Non-blank, non-comment lines. An idea with only these is still real:
    most vanilla ideas apply non-numeric effects, so testing for a numeric
    modifier alone would call 152 healthy ideas 'empty'."""
    return [
        l.strip()
        for l in (text or "").splitlines()
        if l.strip() and not l.strip().startswith("#")
    ]


def classify(g_file: str, g_name: str, tag_lock: str | None) -> str:
    """What kind of set this is. `country` is the one a mod copies."""
    if g_name.startswith("compatibility"):
        return "compat stub"
    if g_file == "zzz_default_idea.txt":
        return "default"
    if g_file == "00_basic_ideas.txt":
        return "basic"
    if g_file == "zz_group_ideas.txt":
        return "group"
    if tag_lock or g_file == "00_country_ideas.txt":
        return "country"
    return "other"


def parse_groups(game: Path) -> list[dict]:
    """Every idea group in common/ideas, as dicts."""
    groups: list[dict] = []
    ideas_dir = game / "common" / "ideas"
    for f in sorted(ideas_dir.glob("*.txt")):
        text = f.read_bytes().decode("utf-8", errors="replace")
        for m in TOP_LEVEL_RE.finditer(text):
            name = m.group(1)
            body = _extract_block(text, name)
            if body is None:
                continue
            subs = _sub_blocks(body)
            ideas = [k for k in subs if k not in SCORING_KEYS and k not in {"start", "bonus"}]
            owners: list[tuple[str, str]] = [
                ("start", subs.get("start", "")),
                ("bonus", subs.get("bonus", "")),
            ] + [(k, subs[k]) for k in ideas]

            # repeated effects, ignoring the scoring sub-blocks
            where: dict[str, list[str]] = {}
            for owner, text_ in owners:
                for mod in _mods(text_):
                    where.setdefault(mod, []).append(owner)

            trigger = subs.get("trigger", "")
            tag = re.search(r"\btag\s*=\s*([A-Z]{3})\b", trigger)
            groups.append(
                {
                    "file": f.name,
                    "name": name,
                    "kind": classify(f.name, name, tag.group(1) if tag else None),
                    "start": len(_mods(subs.get("start", ""))),
                    "bonus": len(_mods(subs.get("bonus", ""))),
                    "ideas": ideas,
                    "idea_count": len(ideas),
                    "free": bool(re.search(r"^\s*free\s*=\s*yes\s*$", body, re.MULTILINE)),
                    "tag_lock": tag.group(1) if tag else None,
                    "trigger_lines": len([l for l in trigger.splitlines() if l.strip()]),
                    "empty_ideas": [k for k in ideas if not _content_lines(subs[k])],
                    "repeated": {k: v for k, v in where.items() if len(v) > 1},
                    "modifiers_per_idea": [len(_mods(subs[k])) for k in ideas],
                    "effects": sorted(where),
                }
            )
    return groups


def _coverage_cap(counts: Counter, share: float = 0.95) -> int:
    """Smallest N covering `share` of the observations."""
    total = sum(counts.values()) or 1
    run = 0
    for n in sorted(counts):
        run += counts[n]
        if run / total >= share:
            return n
    return max(counts) if counts else 0


def summarise(groups: list[dict]) -> dict:
    """The norms the verifier should test against.

    The headline numbers come from `country` sets only (the 446 tag-locked
    national idea sets in 00_country_ideas.txt). Government, advisor and
    group sets have their own shapes and would skew every average.
    """
    country = [g for g in groups if g["kind"] == "country"]
    live = [g for g in country if g["idea_count"]]
    per_idea = Counter(n for g in country for n in g["modifiers_per_idea"])
    return {
        "group_count": len(groups),
        "by_file": dict(Counter(g["file"] for g in groups).most_common()),
        "by_kind": dict(Counter(g["kind"] for g in groups).most_common()),
        "country_count": len(country),
        "tag_locked": sum(1 for g in groups if g["tag_lock"]),
        "free": sum(1 for g in groups if g["free"]),
        "start": dict(sorted(Counter(g["start"] for g in country).items())),
        "bonus": dict(sorted(Counter(g["bonus"] for g in country).items())),
        "idea_count": dict(sorted(Counter(g["idea_count"] for g in country).items())),
        "modal_start": Counter(g["start"] for g in country).most_common(1)[0][0],
        "modal_bonus": Counter(g["bonus"] for g in country).most_common(1)[0][0],
        "modal_idea_count": Counter(g["idea_count"] for g in live).most_common(1)[0][0],
        "modifiers_per_idea": dict(sorted(per_idea.items())),
        "idea_weight_cap": _coverage_cap(per_idea),
        "empty_ideas": sum(len(g["empty_ideas"]) for g in groups),
        "groups_with_repeated_effects": sum(1 for g in groups if g["repeated"]),
    }


def report(groups: list[dict], s: dict) -> None:
    print(f"Base-game idea inventory: {s['group_count']} groups")
    for f, c in s["by_file"].items():
        print(f"    {f:28} {c:4}")
    print("  by kind: " + ", ".join(f"{k} {v}" for k, v in s["by_kind"].items()))
    print()
    print(f"Reference set for this mod: the {s['country_count']} country idea sets")
    print()
    print("How they are granted")
    print(f"    tag-locked (tag = XNN)   {s['tag_locked']:4} / {s['group_count']}")
    print(f"    free = yes               {s['free']:4} / {s['group_count']}")
    print()
    print("Shape of a country idea set (the numbers the mod follows)")
    print(f"    traditions (start): {s['start']}")
    print(f"    ambition   (bonus): {s['bonus']}")
    print(f"    ideas:              {s['idea_count']}")
    print(f"    -> vanilla modal: {s['modal_start']} traditions, "
          f"{s['modal_bonus']} ambition, {s['modal_idea_count']} ideas")
    print()
    print("Weight of a single idea (numeric modifiers per idea, country sets)")
    tot = sum(s["modifiers_per_idea"].values())
    peak = max(s["modifiers_per_idea"].values())
    for n, c in s["modifiers_per_idea"].items():
        bar = "#" * max(1, round(40 * c / peak))
        print(f"    {n:3}  {c:5}  {100*c/tot:5.1f}%  {bar}")
    print(f"    -> 1-{s['idea_weight_cap']} modifiers per idea covers 95% of the base game")
    print()
    print("Rare in vanilla, so a mod doing it is almost certainly a bug")
    print(f"    groups repeating an effect internally : {s['groups_with_repeated_effects']}"
          f" / {s['group_count']}")
    print(f"    empty idea bodies (no effect at all)  : {s['empty_ideas']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", type=Path, default=DEFAULT_GAME)
    ap.add_argument("--json", action="store_true", help="emit the census as JSON")
    ap.add_argument("--catalogue", action="store_true", help="list every group")
    ap.add_argument("--group", help="dump one group in full")
    args = ap.parse_args(argv)

    if not (args.game / "common" / "ideas").is_dir():
        print(f"error: no common/ideas under {args.game}", file=sys.stderr)
        return 2

    groups = parse_groups(args.game)
    s = summarise(groups)

    if args.group:
        for g in groups:
            if g["name"] == args.group:
                print(json.dumps(g, indent=2))
                return 0
        print(f"error: no group named {args.group}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"summary": s, "groups": groups}, indent=2))
        return 0

    report(groups, s)
    if args.catalogue:
        print()
        print("Catalogue")
        print(f"    {'group':34} {'str':>3} {'amb':>3} {'ideas':>5}  {'free':4} {'tag':4}  file")
        for g in groups:
            print(f"    {g['name']:34} {g['start']:3} {g['bonus']:3} {g['idea_count']:5}  "
                  f"{'yes' if g['free'] else '-':4} {(g['tag_lock'] or '-'):4}  {g['file']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
