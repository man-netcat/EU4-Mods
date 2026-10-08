import json, os, os, re, sys, importlib.util

BASE = os.path.dirname(os.path.abspath(__file__))
GAME_HIST_PROV = "/home/rick/Paradox/Games/Europa Universalis IV/history/provinces"
GAME_HIST_CNT = "/home/rick/Paradox/Games/Europa Universalis IV/history/countries"

with open(f"{BASE}/america.json") as f:
    AM = json.load(f)
PROVS = {str(k): v for k, v in AM["provs"].items()}
AMER_IDS = set(str(x) for x in AM["amer_ids"])

spec = importlib.util.spec_from_file_location("design", f"{BASE}/design.py")
design = importlib.util.module_from_spec(spec)
sys.modules["design"] = design
spec.loader.exec_module(design)

with open(f"{BASE}/tribes.json") as f:
    TRIBES = json.load(f)
TRIBE_PROVS = {str(t["prov"]) for t in TRIBES.values()}

# tags the mod controls at 1444: base realms + tribes + formables
mod_tags = {r["tag"] for r in design.REALMS}
mod_tags |= set(TRIBES.keys())
mod_tags |= {f["tag"] for f in design.FORMABLES}
mod_tags |= {f["tag"] for f in design.FORMABLE_REGIONS}


def top_blocks(text):
    blocks = []
    i = 0
    while True:
        m = re.search(r"([\w.:-]+)\s*=\s*\{", text[i:])
        if not m:
            break
        key = m.group(1)
        start = i + m.end() - 1
        j = start + 1
        depth = 1
        while depth:
            ch = text[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            j += 1
        blocks.append((key, text[start + 1:j - 1]))
        i = j
    return blocks


def vanilla_owner(pid):
    cand = []
    for f in os.listdir(GAME_HIST_PROV):
        if re.match(rf"^{pid}\s", f) or f.startswith(pid + " -"):
            cand.append(f)
    if not cand:
        return None
    text = open(f"{GAME_HIST_PROV}/{cand[0]}", encoding="latin-1").read()
    # vanilla puts the 1444 state in the undated section before the first
    # dated block; a 1444.11.11 block (rare) overrides it
    blocks = top_blocks(text)
    if blocks:
        text = text[: text.find(blocks[0][0]) - 1]
    m = re.search(r"owner\s*=\s*\"?(\w+)\"?", text)
    if m:
        return m.group(1)
    for key, inner in blocks:
        if key == "1444.11.11":
            m = re.search(r"owner\s*=\s*\"?(\w+)\"?", inner)
            if m:
                return m.group(1)
    return None

restored = {}
unowned = []
for pid in sorted(AMER_IDS):
    own = vanilla_owner(pid)
    if own is None:
        unowned.append(pid)
        continue
    if own in mod_tags:
        continue
    restored.setdefault(own, []).append(int(pid))

for t in sorted(restored):
    restored[t] = sorted(restored[t])
nprov = sum(len(v) for v in restored.values())
print(f"tags: {len(restored)}  provs: {nprov}")
print(f"vanilla-owned 1444 provs with no owner in vanilla: {len(unowned)}")
print(f"unowned: {unowned[:20]}{'...' if len(unowned) > 20 else ''}")
print()
for t in sorted(restored):
    print(f"  {t}: {restored[t]}")