#!/usr/bin/env python3
"""Resolve the effective province state at the mod's start date.

tools/probe.py builds cache/provdata.json by reading only the top-level
assignments of each vanilla province file. That is the state *before* any dated
block fires, which is nowhere near the 1444.11.11 start this mod runs on: the
mod ships no common/defines.lua, so it inherits vanilla's 1444.11.11.

231 vanilla provinces have an owner or core change dated inside (867, 1444], so
the two snapshots disagree badly. Erzincan (2305) is the clearest example: the
top level says owner = TIM with add_core = TIM, but a 1402.1.1 block hands it to
the Aq Qoyunlu and does remove_core = TIM. At 1444 it is Aq Qoyunlu.

Every "all of <tag>" in gen_provinces.py is derived from this cache, so deriving
it from the wrong snapshot silently produces the wrong realms. This tool applies
the dated blocks in order and writes the effective owner/controller/cores back
into the cache alongside the original values, so the two can be compared rather
than one quietly overwriting the other.
"""
import json
import pathlib
import re
import sys

CACHE = pathlib.Path(__file__).resolve().parent / "cache"
VANILLA = pathlib.Path(
    "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV/history/provinces"
)

# The mod has no defines.lua, so this is vanilla's start date.
START = (1444, 11, 11)

DATE_BLOCK = re.compile(r"^[\t ]*([\d]+)\.([\d]+)\.([\d]+)[\t ]*=[\t ]*[{]", re.M)


def _blocks(text):
    """Yield (date, body) for every dated block, in file order."""
    for m in DATE_BLOCK.finditer(text):
        i = m.end() - 1
        depth = 0
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        yield (int(m.group(1)), int(m.group(2)), int(m.group(3))), text[m.end():i]


def _apply(state, body):
    """Apply the owner/core assignments inside one block body, in textual order."""
    for m in re.finditer(
        r"\b(owner|controller|add_core|remove_core)[\t ]*=[\t ]*([A-Za-z0-9_]+)", body
    ):
        key, val = m.group(1), m.group(2)
        if key == "owner":
            state["owner"] = val
        elif key == "controller":
            state["controller"] = val
        elif key == "add_core":
            if val not in state["cores"]:
                state["cores"].append(val)
        elif key == "remove_core":
            state["cores"] = [c for c in state["cores"] if c != val]


def main():
    cache = CACHE / "provdata.json"
    data = json.loads(cache.read_text())
    changed_owner = []
    changed_cores = []
    missing = []

    for pid, prov in sorted(data["provs"].items(), key=lambda kv: int(kv[0])):
        path = VANILLA / prov["file"]
        if not path.exists():
            missing.append(pid)
            continue
        text = path.read_text(errors="replace")

        # Start from the top-level state that probe.py already recorded, then
        # replay every block dated at or before the start date in order.
        state = {
            "owner": prov.get("owner"),
            "controller": prov.get("controller"),
            "cores": list(prov.get("cores") or []),
        }
        for date, body in sorted(_blocks(text)):
            if date <= START:
                _apply(state, body)

        prov["owner_1444"] = state["owner"]
        prov["controller_1444"] = state["controller"]
        prov["cores_1444"] = sorted(state["cores"])

        if state["owner"] != prov.get("owner"):
            changed_owner.append(
                (pid, prov["name"], prov.get("owner"), state["owner"])
            )
        if sorted(state["cores"]) != sorted(prov.get("cores") or []):
            changed_cores.append((pid, prov["name"], prov.get("cores"), prov["cores_1444"]))

    cache.write_text(json.dumps(data, indent=1, sort_keys=True))

    print(f"resolved {len(data['provs'])} provinces at {START[0]}.{START[1]}.{START[2]}")
    print(f"  owner differs from top level : {len(changed_owner)}")
    print(f"  cores differ from top level  : {len(changed_cores)}")
    if missing:
        print(f"  WARNING missing vanilla files: {len(missing)} -> {missing[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())