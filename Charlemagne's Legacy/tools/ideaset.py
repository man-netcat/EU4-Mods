#!/usr/bin/env python3
"""Work with the national idea sets in tools/data/ideas without opening the data files.

    python3 tools/ideaset.py which TAG [TAG ...]   # the set a tag gets, why, and its ideas
    python3 tools/ideaset.py list [tag|factor|culture|group]   # every set with its trigger
    python3 tools/ideaset.py show SLUG             # one set as the generator will write it
    python3 tools/ideaset.py lint                  # the checks the build runs (exit 1 on a problem)
    python3 tools/ideaset.py new SLUG --tag A,B | --culture a,b | --group g --name Name [--file 15_x.ideas]
                                                   # append an empty block to fill in (placeholders fail lint)
    python3 tools/ideaset.py power [SLUG ...]      # each set's power against its limit (strongest first; the build refuses sets over it)
    python3 tools/ideaset.py ranges KEY [KEY ...]  # the base game's value range for a modifier, and whether it is allowed

Needs EU4_GAME and CK3_GAME like the build."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from steps import ideas as I  # noqa: E402
from tagdb import BY_TAG, culture_groups  # noqa: E402


def _ordered(sets):
    return sorted(sets.values(), key=lambda s: (I.KIND_ORDER[I.kind(s)], s["order"]))


def which(tags):
    sets, _ = I.parse()
    group_of = {c: g for g, v in culture_groups().items() for c in v}
    for tag in tags:
        row = BY_TAG.get(tag)
        if row is None:
            print(f"{tag}: no such tag")
            continue
        grp = group_of.get(row.culture)
        s = next((x for x in _ordered(sets) if I.matches(x, row, group_of)), None)
        if s is None:
            print(f"{tag} ({row.culture}, {grp}): no set of ours: it would fall to the base game's default")
            continue
        print(f"{tag} ({row.culture}, group {grp}): {s['name']} Ideas [{s['slug']}, {I.kind(s)} set, {s['file']}]")
        for i, idea in enumerate(s["ideas"], 1):
            govs = {g for g, _f in I.GOV}
            shown = [f"{k} {v:g}" for k, v in idea["mods"] if k not in govs]
            if any(k in govs for k, _ in idea["mods"]):
                shown.insert(0, "gov " + f"{next(v for k, v in idea['mods'] if k == 'legitimacy'):g}")
            print(f"   {i}. {idea['name']}: " + ", ".join(shown))


def listing(which_kind=None):
    sets, _ = I.parse()
    for s in _ordered(sets):
        if which_kind and I.kind(s) != which_kind:
            continue
        trig = " ; ".join(("not " if neg else "") + f"{what} " + ",".join(vs) for neg, what, vs in s["trigger"])
        print(f"{s['slug']:<28} {I.kind(s):<8} {s['name']:<20} {trig}")


def main(argv):
    if not argv:
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "which" and rest:
        which(rest)
    elif cmd == "list":
        listing(rest[0] if rest else None)
    elif cmd == "show" and rest:
        sets, _ = I.parse()
        print(I.group_text(sets[rest[0]]))
    elif cmd == "lint":
        sets, problems = I.parse()
        problems += I.check_sets(sets)
        print("\n".join(problems) or f"{len(sets)} sets, no problems")
        return 1 if problems else 0
    elif cmd == "power":
        sets, _ = I.parse()
        budget = I.vanilla_budget()
        print(f"base game: median {budget['powers'][len(budget['powers']) // 2]:.2f}, strongest {budget['powers'][-1]:.2f}")
        pick = [sets[w] for w in rest] if rest else sorted(sets.values(), key=lambda s: -I.set_power(s) / I.power_cap(s))[:25]
        for s in pick:
            print(f"{s['slug']:<28} {I.kind(s):<8} {I.set_power(s):6.2f} / {I.power_cap(s):.2f}")
    elif cmd == "ranges" and rest:
        ranges = I.vanilla_ranges()
        for k in rest:
            lo, hi = ranges.get(k, (None, None))
            ok = k in ranges and not I.FORBIDDEN.search(k)
            print(f"{k}: " + (f"base game {lo:g}..{hi:g}" if lo is not None else "not used by the base game's ideas")
                  + ("; allowed" if ok else "; NOT allowed here"))
    elif cmd == "new" and rest:
        slug = rest[0]
        opts = dict(zip(rest[1::2], rest[2::2]))
        clause = next(((w, opts[f"--{w}"]) for w in ("tag", "culture", "group") if f"--{w}" in opts), None)
        if not clause or "--name" not in opts:
            print("new SLUG needs --tag/--culture/--group and --name")
            return 2
        fn = opts.get("--file", "40_new.ideas")
        block = (f"\n[{slug}]\ntrigger = {clause[0]} {clause[1]}\nname = {opts['--name']}\nstart = TODO 0, TODO 0\nbonus = gov 1\n"
                 + "idea = TODO | TODO | TODO 0\n" * 7)
        with open(os.path.join(I.DATA, fn), "a", encoding="utf-8") as fh:
            fh.write(block)
        print(f"appended [{slug}] to tools/data/ideas/{fn}; fill it in, then `ideaset.py lint`")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
