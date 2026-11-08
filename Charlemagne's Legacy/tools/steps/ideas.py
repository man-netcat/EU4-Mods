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
`culture_group`), ANDed with every `religion`, `government`, `rank`, `tech` and `reform` clause (each an OR of its values) and with
the negation of each `not` clause. A set with such a condition is a *factor* set: it is tried after the tag sets and before the
culture sets, so it wins over the culture it narrows. Modifier keys are those the base game's ideas use, minus force limits and
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

#: the trigger clauses that pick realms by name or people (alternatives), and the ones that narrow by what the realm is (all must hold);
#: each condition maps a tags.db row to the values it has
SELECTORS = ("tag", "culture", "group")
CONDITIONS = {
    "religion": lambda r: {str(r.religion)},
    "government": lambda r: {str(r.government)},
    "rank": lambda r: {str(r.rank)},
    "tech": lambda r: {str(r.technology_group)},
    "reform": lambda r: {str(x) for x in (r.reforms or ())},
}
EU4_TRIGGER = {"tag": "tag", "culture": "primary_culture", "group": "culture_group", "religion": "religion",
               "government": "government", "rank": "government_rank", "tech": "technology_group", "reform": "has_reform"}

KEY_RE = re.compile(r"^[a-z][a-z_0-9]*$")


def vanilla_ranges():
    """{modifier: (min, max)} of the numeric values the base game's idea files give it."""
    seen = collections.defaultdict(list)
    for fn in ("00_country_ideas.txt", "zz_group_ideas.txt", "00_basic_ideas.txt"):
        text = re.sub(r"#.*", "", open(os.path.join(GAME, "common", "ideas", fn), encoding="cp1252", errors="replace").read())
        for m in re.finditer(r"(?m)^\s*([a-z_0-9]+)\s*=\s*(-?[0-9.]+)\s*$", text):
            seen[m.group(1)].append(float(m.group(2)))
    return {k: (min(v), max(v)) for k, v in seen.items()}


#: how much of the base game's strongest sets a set may use: a tag set stays under the base game's 98th percentile, a culture
#: or culture-group set (it serves many tags) under the 90th, and no modifier's total over a set passes the highest total any
#: base-game set reaches for it
TAG_QUANTILE, OTHER_QUANTILE = 0.98, 0.90


def power(mods, ranges):
    """What a list of modifiers is worth: each is its value as a share of the largest the base game gives that key, summed.
    The government stats count once (only the one that fits the government applies)."""
    gov_keys = {g for g, _f in GOV}
    share = lambda k, v: abs(v) / (max(abs(ranges[k][0]), abs(ranges[k][1])) or 1)  # noqa: E731
    total = sum(share(k, v) for k, v in mods if k in ranges and k not in gov_keys)
    return total + max([share(k, v) for k, v in mods if k in gov_keys and k in ranges] or [0])


_BUDGET = {}


def vanilla_budget():
    """{"ranges", "powers" (sorted, one per base-game set), "totals" ({key: largest |sum| in one set})} from the base game's own
    national, culture and group idea sets (a block with at least ten numbers is a full set)."""
    if _BUDGET:
        return _BUDGET
    ranges = vanilla_ranges()
    powers, totals = [], collections.defaultdict(float)
    for fn in ("00_country_ideas.txt", "zz_group_ideas.txt"):
        text = re.sub(r"#.*", "", open(os.path.join(GAME, "common", "ideas", fn), encoding="cp1252", errors="replace").read())
        for m in re.finditer(r"(?m)^[A-Za-z0-9_]+\s*=\s*\{", text):
            depth, j = 1, m.end()
            while depth and j < len(text):
                depth += (text[j] == "{") - (text[j] == "}")
                j += 1
            mods = [(k, float(v)) for k, v in re.findall(r"(?m)^\s*([a-z_0-9]+)\s*=\s*(-?[0-9.]+)\s*$", text[m.end():j])]
            if len(mods) < 10:
                continue
            powers.append(power(mods, ranges))
            sums = collections.defaultdict(float)
            for k, v in mods:
                sums[k] += v
            for k, v in sums.items():
                totals[k] = max(totals[k], abs(v))
    _BUDGET.update(ranges=ranges, powers=sorted(powers), totals=dict(totals))
    return _BUDGET


def set_power(s, ranges=None):
    ranges = ranges or vanilla_budget()["ranges"]
    return power(s["start"] + s["bonus"] + [m for i in s["ideas"] for m in i["mods"]], ranges)


def power_cap(s):
    """The most power a set may have (see TAG_QUANTILE)."""
    powers = vanilla_budget()["powers"]
    q = TAG_QUANTILE if kind(s) == "tag" else OTHER_QUANTILE
    return powers[min(len(powers) - 1, int(len(powers) * q))]


def check_power(sets):
    """Problems for sets stronger than the base game's: too much in total, or too much of one modifier."""
    budget = vanilla_budget()
    problems = []
    for s in sets.values():
        w = s["slug"]
        have, cap = set_power(s, budget["ranges"]), power_cap(s)
        if have > cap + 1e-9:
            problems.append(f"{w}: power {have:.2f} is over the {kind(s)} limit {cap:.2f} (the base game's strongest sets reach "
                            f"{budget['powers'][-1]:.2f}); trim the biggest values")
        sums = collections.defaultdict(float)
        for k, v in s["start"] + s["bonus"] + [m for i in s["ideas"] for m in i["mods"]]:
            sums[k] += v
        gov_keys = {g for g, _f in GOV}
        for k, v in sums.items():
            top = budget["totals"].get(k)
            if k not in gov_keys and top is not None and abs(v) > top + 1e-9:
                problems.append(f"{w}: {k} adds up to {v:g} over the whole set, the base game's highest is {top:g}")
    return problems


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
                    if len(bits) != 2 or bits[0] not in SELECTORS + tuple(CONDITIONS):
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
    """tag, factor, culture or group: how specific the set is (the order the sets are tried in)."""
    kinds = {c for neg, c, _ in s["trigger"] if not neg}
    if "tag" in kinds:
        return "tag"
    if kinds & set(CONDITIONS):
        return "factor"
    return "culture" if "culture" in kinds else "group"


KIND_ORDER = {"tag": 0, "factor": 1, "culture": 2, "group": 3}


def matches(s, row, group_of):
    """Does the set's trigger hold for a realm (a tags.db row)? The tag, culture and group clauses are alternatives, the
    religion, government, rank, tech and reform clauses must all hold, a `not` clause must not."""
    def hit(what, values):
        if what == "tag":
            return row.tag in values
        if what == "culture":
            return row.culture in values
        if what == "group":
            return group_of.get(row.culture) in values
        have = CONDITIONS[what](row)
        return any(str(v) in have for v in values)

    pos = [(w, v) for neg, w, v in s["trigger"] if not neg]
    if any(neg and hit(w, v) for neg, w, v in s["trigger"]):
        return False
    selectors = [(w, v) for w, v in pos if w in SELECTORS]
    conds = [(w, v) for w, v in pos if w in CONDITIONS]
    if selectors and not any(hit(w, v) for w, v in selectors):
        return False
    return bool(pos) and all(hit(w, v) for w, v in conds)


def check_sets(sets):
    """Everything that must hold for a set to be written; returns the problems."""
    from tagdb import BY_TAG, FORMABLE_TAGS, culture_groups

    ranges = vanilla_ranges()
    groups = culture_groups()
    cultures = {c for v in groups.values() for c in v}
    problems = []
    by_name = collections.defaultdict(list)
    for s in sets.values():
        by_name[(s["name"] or "").lower()].append(s["slug"])
    for name, slugs in by_name.items():
        if name and len(slugs) > 1:
            problems.append(f"{', '.join(slugs)}: the same display name {name!r}; two idea sets must not read alike in game")
    for s in sets.values():
        w = s["slug"]
        if not s["name"]:
            problems.append(f"{w}: no name")
        if len(s["name"] or "") > 24:
            problems.append(f"{w}: name {s['name']!r} is over 24 characters")
        names = collections.Counter(i["name"].lower() for i in s["ideas"])
        problems += [f"{w}: two ideas are called {n!r}" for n, k in names.items() if k > 1]
        for n, i in enumerate(s["ideas"], 1):
            if not 1 <= len(i["name"]) <= 45:
                problems.append(f"{w} idea {n}: name {i['name']!r} must be 1..45 characters")
            if not 30 <= len(i["desc"]) <= 220 or not i["desc"].endswith((".", "!")):
                problems.append(f"{w} idea {n}: description must be a sentence of 30..220 characters")
            if i["name"].lower() == s["name"].lower():
                problems.append(f"{w} idea {n}: named like its own set")
        if not [t for t in s["trigger"] if not t[0]]:
            problems.append(f"{w}: no positive trigger clause")
        if kind(s) == "factor" and not any(not neg and what in SELECTORS and what != "tag" for neg, what, _ in s["trigger"]) \
                and not any(not neg and what in CONDITIONS for neg, what, _ in s["trigger"]):
            problems.append(f"{w}: a factor set needs a condition")
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
                if what in CONDITIONS:
                    known = {x for r in BY_TAG.values() for x in CONDITIONS[what](r)}
                else:
                    known = (set(BY_TAG) | FORMABLE_TAGS | VANILLA_ONLY_TAGS()) if what == "tag" else (cultures if what == "culture" else set(groups))
                if v not in known:
                    problems.append(f"{w}: {what} {v} does not exist here")
        if kind(s) == "factor" and not any(matches(s, r, {c: g for g, cs in groups.items() for c in cs}) for r in BY_TAG.values()):
            problems.append(f"{w}: no realm matches this factor set")
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
    return problems + check_power(sets)


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
    word = EU4_TRIGGER
    lines = []

    def block(clauses, indent):
        if len(clauses) == 1:
            return [f"{indent}{word[clauses[0][0]]} = {clauses[0][1]}"]
        return [f"{indent}OR = {{"] + [f"{indent}\t{word[c]} = {v}" for c, v in clauses] + [f"{indent}}}"]

    selectors = [(c, v) for c, v in pos if c in SELECTORS]
    if selectors:
        lines += block(selectors, "\t\t")
    for what in CONDITIONS:
        lines += block([(c, v) for c, v in pos if c == what], "\t\t") if any(c == what for c, _ in pos) else []
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
    ordered = sorted(sets.values(), key=lambda s: (KIND_ORDER[kind(s)], s["order"]))
    tags = [s for s in ordered if kind(s) == "tag"]
    rest = [s for s in ordered if kind(s) != "tag"]
    head = "# Generated by tools/steps/ideas.py from tools/data/ideas/*.ideas; do not edit.\n\n"
    write_out(os.path.join(MOD, "common", "ideas", "00_country_ideas.txt"), head + "\n".join(group_text(s) for s in tags))
    vanilla = open(os.path.join(GAME, "common", "ideas", "zz_group_ideas.txt"), encoding="cp1252", errors="replace").read()
    kept = _vanilla_blocks(vanilla, KEEP_GROUPS)
    write_out(os.path.join(MOD, "common", "ideas", "zz_group_ideas.txt"),
              head + "# Kept from the base game: groups that trigger on a reform or a status.\n\n"
              + "\n\n".join(kept[n] for n in KEEP_GROUPS) + "\n\n# Ours: factor sets (religion, government, rank), then major cultures, then culture groups.\n\n"
              + "\n".join(group_text(s) for s in rest))
    write_loc(os.path.join(MOD, "localisation", "kar_ideas_l_english.yml"), loc_pairs(sets))
    by = collections.Counter(kind(s) for s in ordered)
    print(f"national ideas: {len(ordered)} sets ({by['tag']} tag, {by['factor']} factor, {by['culture']} culture, {by['group']} group), "
          f"{len(KEEP_GROUPS)} base-game groups kept")


#: where idea groups and ideas are named by script: `has_idea_group = X`, `full_idea_group = X`, `has_idea = X`
IDEA_REF = re.compile(r"\b(has_idea_group|full_idea_group|has_idea)\s*=\s*\"?([A-Za-z0-9_]+)\"?")


def known_idea_names():
    """Every idea group and idea key the game will know: ours, the kept base-game groups, and the base game's other idea files."""
    names = set()
    d = os.path.join(GAME, "common", "ideas")
    files = [os.path.join(MOD, "common", "ideas", f) for f in os.listdir(os.path.join(MOD, "common", "ideas")) if f.endswith(".txt")]
    mod_names = {os.path.basename(f) for f in files}
    files += [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".txt") and f not in mod_names]
    for path in files:
        text = re.sub(r"#.*", "", open(path, encoding="cp1252", errors="replace").read())
        depth, i = 0, 0
        for m in re.finditer(r"([A-Za-z0-9_]+)\s*=\s*\{|[{}]", text):
            tok = m.group(0)
            if tok == "}":
                depth -= 1
            else:
                if tok != "{" and depth <= 1:
                    names.add(m.group(1))
                depth += 1
    return names


def live_script_files():
    """(relative path, absolute path) of every script file the game will load for the mod: the mod's own, and the base game's that
    the mod neither overrides by name nor drops with a replace_path."""
    from steps.eventrefs import replaced_paths

    dropped = replaced_paths()
    seen = {}
    for root in ("common", "events", "decisions", "missions", "on_actions", "history"):
        for base, is_mod in ((os.path.join(MOD, root), True), (os.path.join(GAME, root), False)):
            for dp, _dirs, fs in os.walk(base):
                for f in fs:
                    if not f.endswith(".txt"):
                        continue
                    full = os.path.join(dp, f)
                    rel = os.path.relpath(full, MOD if is_mod else GAME)
                    if not is_mod and any(rel == d or rel.startswith(d + os.sep) for d in dropped):
                        continue
                    if rel not in seen:
                        seen[rel] = full
    return seen


def dangling_idea_refs():
    """[(relative path, kind, name)] for scripts that name an idea group or idea nobody defines any more."""
    known = known_idea_names()
    out = []
    for rel, full in sorted(live_script_files().items()):
        if rel.startswith(os.path.join("common", "ideas")):
            continue
        text = "\n".join(ln.split("#", 1)[0] for ln in open(full, encoding="cp1252", errors="replace").read().splitlines())
        for m in IDEA_REF.finditer(text):
            if m.group(2) not in known:
                out.append((rel, m.group(1), m.group(2)))
    return out


def _read_script(path):
    """(text, encoding) of a script file, keeping the encoding to write it back the same way."""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"{path}: not utf-8 and not cp1252")


def step_dangling_ideas():
    """The base game's scripts ask whether a realm holds its own idea group (`has_idea_group = FRA_ideas`) and the national ideas
    here replaced those groups. Nobody can hold a group that does not exist, so the question is answered `always = no` in a
    copy of each file that still loads: the same result, without an unknown-idea line in error.log."""
    todo = collections.defaultdict(set)
    for rel, _kind, name in dangling_idea_refs():
        todo[rel].add(name)
    live = live_script_files()
    changed = calls = 0
    for rel, names in sorted(todo.items()):
        text, enc = _read_script(live[rel])
        pattern = re.compile(r"\b(?:has_idea_group|full_idea_group|has_idea)\s*=\s*\"?(" + "|".join(map(re.escape, sorted(names))) + r")\"?(?![A-Za-z0-9_])")
        out, n = pattern.subn("always = no", text)
        write_out(os.path.join(MOD, rel), out, encoding=enc, errors="strict")
        changed += 1
        calls += n
    left = dangling_idea_refs()
    print(f"dangling ideas: {changed} files had {calls} references to removed idea groups answered `always = no`; {len(left)} left")
    if left:
        raise SystemExit(f"still naming removed idea groups: {left[:5]}")


def vanilla_negative_share():
    """{modifier: share of the base game's idea values for it that are negative}, for keys with at least three values."""
    seen = collections.defaultdict(list)
    for fn in ("00_country_ideas.txt", "zz_group_ideas.txt", "00_basic_ideas.txt"):
        text = re.sub(r"#.*", "", open(os.path.join(GAME, "common", "ideas", fn), encoding="cp1252", errors="replace").read())
        for m in re.finditer(r"(?m)^\s*([a-z_0-9]+)\s*=\s*(-?[0-9.]+)\s*$", text):
            seen[m.group(1)].append(float(m.group(2)))
    return {k: sum(1 for x in v if x < 0) / len(v) for k, v in seen.items() if len(v) >= 3}


def wrong_way(sets):
    """[(slug, where, key, value)]: a modifier pointing the opposite way from how the base game always uses it (a malus by accident)."""
    share = vanilla_negative_share()
    out = []
    for s in sets.values():
        blocks = [("tradition", s["start"]), ("ambition", s["bonus"])] + [(f"idea {n}", i["mods"]) for n, i in enumerate(s["ideas"], 1)]
        for where, mods in blocks:
            for k, v in mods:
                neg = share.get(k)
                if neg is not None and v != 0 and ((v > 0 and neg >= 0.9) or (v < 0 and neg <= 0.1)):
                    out.append((s["slug"], where, k, v))
    return out


def top_keys(text, depth=1):
    """Names of the `name = {` blocks that open at the given brace depth (1 = top level) of a script text, comments removed."""
    names, level = [], 0
    for m in re.finditer(r"([A-Za-z0-9_.\-]+)\s*=\s*\{|[{}]", re.sub(r"#.*", "", text)):
        tok = m.group(0)
        if tok == "}":
            level -= 1
        else:
            if tok != "{" and level == depth - 1:
                names.append(m.group(1))
            level += 1
    return names


def engine_names():
    """What a trigger condition may name, read from the game files the mod runs with:
    {religion, government, reform, tech} -> set of names (the mod's own file wins over the base game's of the same name)."""
    def files(sub):
        found = {}
        for base in (os.path.join(GAME, "common", sub), os.path.join(MOD, "common", sub)):
            if os.path.isdir(base):
                for f in os.listdir(base):
                    if f.endswith(".txt"):
                        found[f] = os.path.join(base, f)
        return list(found.values())

    def text(path):
        return open(path, encoding="cp1252", errors="replace").read()

    religions = set()
    for path in files("religions"):
        religions |= set(top_keys(text(path), 2))
    governments = set()
    for path in files("governments"):
        governments |= set(top_keys(text(path), 1))
    reforms = set()
    for path in files("government_reforms"):
        reforms |= set(top_keys(text(path), 1))
    tech = set()
    tfile = os.path.join(MOD, "common", "technology.txt")
    tfile = tfile if os.path.exists(tfile) else os.path.join(GAME, "common", "technology.txt")
    groups_block = re.search(r"groups\s*=\s*\{", re.sub(r"#.*", "", text(tfile)))
    if groups_block:
        body = re.sub(r"#.*", "", text(tfile))[groups_block.start():]
        tech = set(top_keys(body, 2))
    return {"religion": religions, "government": governments, "reform": reforms, "tech": tech}


def written_groups():
    """{group name: (file, text)} for every idea group in the idea files the mod ships, plus the names defined more than once."""
    found, twice = {}, []
    for f in sorted(os.listdir(os.path.join(MOD, "common", "ideas"))):
        if not f.endswith(".txt"):
            continue
        text = open(os.path.join(MOD, "common", "ideas", f), encoding="cp1252", errors="replace").read()
        code = re.sub(r"#.*", "", text)
        for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", code):
            depth, j = 1, m.end()
            while depth and j < len(code):
                depth += (code[j] == "{") - (code[j] == "}")
                j += 1
            if m.group(1) in found:
                twice.append(m.group(1))
            found[m.group(1)] = (f, code[m.end():j - 1], depth == 0)
    return found, twice
