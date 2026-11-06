#!/usr/bin/env python3
"""National ideas: the base game's tag- and culture-specific idea groups replaced by ones written for the period.

The sets live in `tools/data/ideas/*.ideas` (hand-written game design, no CK3 text). The build writes

* `common/ideas/00_country_ideas.txt`: the tag sets, first match wins (this replaces the base game's file of that name,
  with its 440 tag groups);
* `common/ideas/zz_group_ideas.txt`: the base game's government- and status-based groups kept verbatim (client states,
  trading cities, colonial nations, cossacks, hordes, daimyo, Siberian tribes, pirates, Christian theocracies), then our
  major-culture sets, then our culture-group sets (this replaces the base game's file of that name);
* `localisation/kar_ideas_l_english.yml`: every group, tradition, ambition and idea name and description.

File format (`#` starts a comment line):

    [slug]
    trigger = tag ASU,LEO ; culture french ; group frankish ; not tag XXX
    name = Asturian
    start = land_morale 0.10, defensiveness 0.10
    bonus = prestige 1                     # or `gov 1`: legitimacy, devotion, horde_unity, meritocracy 1 and
                                           # republican_tradition 0.5 (the one that fits the government applies)
    idea = Name | Description | key value, key value        # exactly seven

A trigger is the OR of its `tag`, `culture` and `group` clauses (`culture` is `primary_culture`, `group` is
`culture_group`), ANDed with each `not` clause. Modifier keys are those the base game's ideas use, minus force limits and
whatever belongs to a later age; values stay within the range the base game's ideas use for that key."""

import collections
import os
import re
import sys

from steps.layout import GAME, MOD
from steps.output import write_loc, write_out

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data", "ideas")

#: government-bound stats: the ones that do nothing for a government are ignored by the game, so a `gov v` macro lists all
GOV = (("legitimacy", 1.0), ("devotion", 1.0), ("horde_unity", 1.0), ("meritocracy", 1.0), ("republican_tradition", 0.5))

#: kept from the base game's zz_group_ideas.txt, in its order: they trigger on a reform or status, never on a tag or culture
KEEP_GROUPS = ("client_ideas", "trading_city_ideas", "colonial_ideas", "cossack_ideas", "horde_ideas", "daimyo_ideas",
               "siberian_ideas", "pirate_ideas", "theocracy_ideas")

#: what is never used in an idea here: troop numbers must come from development alone (user, 5 Nov 2026), and the new world,
#: trade companies, gunpowder, institutions and the early modern state are a later age
FORBIDDEN = re.compile(r"forcelimit|colon|trade_company|privateer|embargo|artillery|fire|institution|absolutism|"
                       r"army_professionalism|years_of_nationalism|cav_to_inf|innovativeness|mercantilism|treasure|"
                       r"parliament|estate|revolution|great_project|center_of_trade|expand_administration|"
                       r"state_governing|reform_progress|government_power|yearly_(?!corruption)|monthly_|privilege|loyalty_modifier|"
                       r"num_of|free_|possible_|may_|tariffs|power_projection|imperial_|tribal_development|"
                       r"naval_tradition_from|global_naval|blockade|siege_blockade|landing|transport")

KEY_RE = re.compile(r"^[a-z][a-z_0-9]*$")


def vanilla_ranges():
    """{modifier: (min, max)} of the numeric values the base game's idea files give it."""
    seen = collections.defaultdict(list)
    for fn in ("00_country_ideas.txt", "zz_group_ideas.txt", "00_basic_ideas.txt"):
        text = re.sub(r"#.*", "", open(os.path.join(GAME, "common", "ideas", fn), encoding="cp1252", errors="replace").read())
        for m in re.finditer(r"(?m)^\s*([a-z_0-9]+)\s*=\s*(-?[0-9.]+)\s*$", text):
            seen[m.group(1)].append(float(m.group(2)))
    return {k: (min(v), max(v)) for k, v in seen.items()}


def _mods(text, where, problems):
    out = []
    for part in [p.strip() for p in text.split(",") if p.strip()]:
        bits = part.split()
        if len(bits) != 2:
            problems.append(f"{where}: cannot read modifier {part!r}")
            continue
        key, val = bits
        try:
            num = float(val)
        except ValueError:
            problems.append(f"{where}: {val!r} is no number")
            continue
        if key == "gov":
            out += [(k, round(num * f, 4)) for k, f in GOV]
        else:
            out.append((key, num))
    return out


def parse(path_or_text=None):
    """({slug: set}, [problems]) over every data file; each set keeps its file order in `order`."""
    problems, sets, order = [], {}, []
    files = sorted(f for f in os.listdir(DATA) if f.endswith(".ideas")) if os.path.isdir(DATA) else []
    for fn in files:
        cur = None
        for n, raw in enumerate(open(os.path.join(DATA, fn), encoding="utf-8").read().splitlines(), 1):
            line = raw.strip()
            where = f"{fn}:{n}"
            if not line or line.startswith("#"):
                continue
            m = re.match(r"^\[([a-z][a-z_0-9]*)\]$", line)
            if m:
                cur = {"slug": m.group(1), "file": fn, "trigger": [], "ideas": [], "name": None, "start": [], "bonus": []}
                if cur["slug"] in sets:
                    problems.append(f"{where}: set {cur['slug']} is defined twice")
                sets[cur["slug"]] = cur
                order.append(cur["slug"])
                continue
            if cur is None or "=" not in line and "|" not in line:
                problems.append(f"{where}: unreadable line {line!r}")
                continue
            key, _, rest = line.partition("=")
            key, rest = key.strip(), rest.strip()
            if key == "trigger":
                for clause in rest.split(";"):
                    bits = clause.split()
                    if not bits:
                        continue
                    neg = bits[0] == "not"
                    if neg:
                        bits = bits[1:]
                    if len(bits) != 2 or bits[0] not in ("tag", "culture", "group"):
                        problems.append(f"{where}: cannot read trigger clause {clause.strip()!r}")
                        continue
                    cur["trigger"].append((neg, bits[0], [v.strip() for v in bits[1].split(",") if v.strip()]))
            elif key == "name":
                cur["name"] = rest
            elif key in ("start", "bonus"):
                cur[key] = _mods(rest, where, problems)
            elif key == "idea":
                parts = [p.strip() for p in rest.split("|")]
                if len(parts) != 3:
                    problems.append(f"{where}: an idea is `Name | Description | modifiers`")
                    continue
                cur["ideas"].append({"name": parts[0], "desc": parts[1], "mods": _mods(parts[2], where, problems)})
            else:
                problems.append(f"{where}: unknown key {key!r}")
    for s in sets.values():
        s["order"] = order.index(s["slug"])
    return sets, problems


def kind(s):
    """tag, culture or group: how specific the set is (the order the sets are tried in)."""
    kinds = {c for neg, c, _ in s["trigger"] if not neg}
    return "tag" if "tag" in kinds else ("culture" if "culture" in kinds else "group")


def check_sets(sets):
    """Everything that must hold for a set to be written; returns the problems."""
    from tagdb import BY_TAG, FORMABLE_TAGS, culture_groups

    ranges = vanilla_ranges()
    groups = culture_groups()
    cultures = {c for v in groups.values() for c in v}
    problems = []
    for s in sets.values():
        w = s["slug"]
        if not s["name"]:
            problems.append(f"{w}: no name")
        if not [t for t in s["trigger"] if not t[0]]:
            problems.append(f"{w}: no positive trigger clause")
        if len(s["ideas"]) != 7:
            problems.append(f"{w}: {len(s['ideas'])} ideas, not 7")
        govs = {g for g, _f in GOV}
        start_n = len([k for k, _ in s["start"] if k not in govs]) + (1 if any(k in govs for k, _ in s["start"]) else 0)
        if start_n != 2:
            problems.append(f"{w}: tradition (start) must carry two modifiers, has {start_n}")
        if not s["bonus"]:
            problems.append(f"{w}: no ambition (bonus)")
        for neg, what, values in s["trigger"]:
            for v in values:
                known = (set(BY_TAG) | FORMABLE_TAGS | VANILLA_ONLY_TAGS()) if what == "tag" else (cultures if what == "culture" else set(groups))
                if v not in known:
                    problems.append(f"{w}: {what} {v} does not exist here")
        blocks = [("start", s["start"]), ("bonus", s["bonus"])] + [(f"idea {i + 1}", i_["mods"]) for i, i_ in enumerate(s["ideas"])]
        for label, mods in blocks:
            collapsed = len([k for k, _ in mods if k not in {g for g, _f in GOV}]) + (1 if any(k in {g for g, _f in GOV} for k, _ in mods) else 0)
            if label.startswith("idea") and not 1 <= collapsed <= 2:
                problems.append(f"{w} {label}: {collapsed} modifiers (1 or 2)")
            seen = set()
            for key, val in mods:
                if key in seen:
                    problems.append(f"{w} {label}: {key} twice")
                seen.add(key)
                gov = key in {k for k, _ in GOV}
                if not gov and (FORBIDDEN.search(key) or key not in ranges or not KEY_RE.match(key)):
                    problems.append(f"{w} {label}: {key} is not an allowed modifier")
                    continue
                lo, hi = ranges.get(key, (None, None))
                if lo is not None and not gov and not (min(lo, hi) - 1e-9 <= val <= max(lo, hi) + 1e-9):
                    problems.append(f"{w} {label}: {key} {val:g} is outside the base game's {lo:g}..{hi:g}")
    return problems


def VANILLA_ONLY_TAGS():
    """Tags of the base game that the mod does not use but a set may name (formation targets from the base game)."""
    found = set()
    d = os.path.join(GAME, "common", "country_tags")
    for fn in os.listdir(d):
        if fn.endswith(".txt"):
            found.update(re.findall(r"(?m)^([A-Z][A-Z0-9]{2})\s*=", open(os.path.join(d, fn), encoding="cp1252", errors="replace").read()))
    return found


def _fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-") else "0"


def _trigger(s):
    pos = [(c, v) for neg, c, vs in s["trigger"] if not neg for v in vs]
    neg = [(c, v) for ng, c, vs in s["trigger"] if ng for v in vs]
    word = {"tag": "tag", "culture": "primary_culture", "group": "culture_group"}
    lines = []
    if len(pos) == 1:
        lines.append(f"\t\t{word[pos[0][0]]} = {pos[0][1]}")
    else:
        lines.append("\t\tOR = {")
        lines += [f"\t\t\t{word[c]} = {v}" for c, v in pos]
        lines.append("\t\t}")
    for c, v in neg:
        lines.append(f"\t\tNOT = {{ {word[c]} = {v} }}")
    return "\n".join(lines)


def group_text(s):
    key = f"kar_{s['slug']}_ideas"
    mods = lambda ms: "\n".join(f"\t\t{k} = {_fmt(v)}" for k, v in ms)  # noqa: E731
    out = [f"{key} = {{", "\tstart = {", mods(s["start"]), "\t}", "", "\tbonus = {", mods(s["bonus"]), "\t}", "",
           "\ttrigger = {", _trigger(s), "\t}", "\tfree = yes", ""]
    for i, idea in enumerate(s["ideas"], 1):
        out += [f"\tkar_{s['slug']}_{i} = {{", mods(idea["mods"]).replace("\t\t", "\t\t"), "\t}"]
    out.append("}")
    return "\n".join(out) + "\n"


def loc_pairs(sets):
    pairs = []
    for s in sets.values():
        key = f"kar_{s['slug']}_ideas"
        pairs += [(key, f"{s['name']} Ideas"), (f"{key}_start", f"{s['name']} Traditions"), (f"{key}_bonus", f"{s['name']} Ambition")]
        for i, idea in enumerate(s["ideas"], 1):
            pairs += [(f"kar_{s['slug']}_{i}", idea["name"]), (f"kar_{s['slug']}_{i}_desc", idea["desc"])]
    return pairs


def _vanilla_blocks(text, names):
    out = {}
    for name in names:
        m = re.search(rf"(?m)^{name}\s*=\s*\{{", text)
        if not m:
            raise SystemExit(f"base-game idea group {name} not found")
        depth, i = 0, m.end() - 1
        while i < len(text):
            depth += (text[i] == "{") - (text[i] == "}")
            if depth == 0:
                break
            i += 1
        out[name] = text[m.start():i + 1]
    return out


def step_ideas():
    sets, problems = parse()
    problems += check_sets(sets)
    if problems:
        raise SystemExit("national ideas data:\n  " + "\n  ".join(problems[:30]))
    ordered = sorted(sets.values(), key=lambda s: ({"tag": 0, "culture": 1, "group": 2}[kind(s)], s["order"]))
    tags = [s for s in ordered if kind(s) == "tag"]
    rest = [s for s in ordered if kind(s) != "tag"]
    head = "# Generated by tools/steps/ideas.py from tools/data/ideas/*.ideas; do not edit.\n\n"
    write_out(os.path.join(MOD, "common", "ideas", "00_country_ideas.txt"), head + "\n".join(group_text(s) for s in tags))
    vanilla = open(os.path.join(GAME, "common", "ideas", "zz_group_ideas.txt"), encoding="cp1252", errors="replace").read()
    kept = _vanilla_blocks(vanilla, KEEP_GROUPS)
    write_out(os.path.join(MOD, "common", "ideas", "zz_group_ideas.txt"),
              head + "# Kept from the base game: groups that trigger on a reform or a status.\n\n"
              + "\n\n".join(kept[n] for n in KEEP_GROUPS) + "\n\n# Ours: major cultures, then culture groups.\n\n"
              + "\n".join(group_text(s) for s in rest))
    write_loc(os.path.join(MOD, "localisation", "kar_ideas_l_english.yml"), loc_pairs(sets))
    by = collections.Counter(kind(s) for s in ordered)
    print(f"national ideas: {len(ordered)} sets ({by['tag']} tag, {by['culture']} culture, {by['group']} group), "
          f"{len(KEEP_GROUPS)} base-game groups kept")
