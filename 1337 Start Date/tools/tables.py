"""EU5 culture/religion -> EU4 culture/religion tables (hand overrides, then name match, then vote)."""
import json, re
from collections import Counter, defaultdict
from popdata import location_pops, vanilla_cr
from paths import MOD

RELIGION_HAND = {
    "catholic": "catholic", "orthodox": "orthodox", "sunni": "sunni", "shia": "shiite", "ibadi": "ibadi",
    "hindu": "hinduism", "sanjiao": "confucianism", "mahayana": "mahayana", "theravada": "buddhism",
    "tibetan_buddhism": "vajrayana", "shinto": "shinto", "miaphysite": "coptic", "nestorianism": "sunni",
    "tengri": "tengri_pagan_reformed", "dreamtime_religion": "dreamtime", "inti": "inti",
    "mesoamerican": "nahuatl", "nahuatl": "nahuatl", "mayan": "mesoamerican_religion",
    "druzism": "shiite", "jewish": "jewish", "zoroastrian": "zoroastrian", "sikh": "sikhism",
    # TODO(new religion): Baltic/Finnic paganism has no vanilla EU4 religion
    "romuva": "animism", "muinaisusko": "animism", "sapmi_shamanism": "shamanism",
    "norse": "norse_pagan_reformed", "norse_pagan": "norse_pagan_reformed", "bantu_religion": "animism",
}


def eu5_culture_groups():
    import glob
    from pdx import parse, get, getall
    from paths import EU5_GAME
    out = {}
    for f in glob.glob(str(EU5_GAME / "in_game/common/cultures/*.txt")):
        for name, b in parse(open(f, encoding="utf-8-sig").read()):
            if isinstance(b, list):
                g = get(b, "culture_groups")
                if isinstance(g, list):
                    out[name] = [v for k, v in g if k is None]
    return out


def build():
    m = json.load(open(MOD / "tools/data/loc2prov.json"))
    lp = location_pops()
    van = vanilla_cr()
    cv, rv = defaultdict(Counter), defaultdict(Counter)
    eu5_cul, eu5_rel = Counter(), Counter()
    for l in lp.values():
        eu5_cul.update(l["cul"])
        eu5_rel.update(l["rel"])
    for pid, v in m.items():
        if v["tier"] == "area-fallback":
            continue
        cul, rel = Counter(), Counter()
        for l in v["locations"]:
            if l in lp:
                cul += lp[l]["cul"]
                rel += lp[l]["rel"]
        if cul:
            vc, vr = van[int(pid)]
            cv[cul.most_common(1)[0][0]][vc] += 1
            rv[rel.most_common(1)[0][0]][vr] += 1
    eu4_rel = set(RELIGION_HAND.values()) | {r for c in rv.values() for r in c if r}
    rmap = {}
    for r in eu5_rel:
        if r in RELIGION_HAND:
            rmap[r] = RELIGION_HAND[r]
        elif r in rv:
            # exclude world religions for pagan-looking names: take most common pagan-ish answer
            ranked = [x for x, _ in rv[r].most_common() if x]
            pag = [x for x in ranked if x in ("animism", "shamanism", "totemism", "tengri_pagan_reformed", "nahuatl",
                                               "mesoamerican_religion", "inti", "dreamtime")]
            rmap[r] = pag[0] if pag and r.endswith(("religion", "paganism", "shamanism", "totemism")) else (ranked[0] if ranked else "animism")
        else:
            rmap[r] = "animism"
    groups = eu5_culture_groups()
    gv = defaultdict(Counter)
    for c, cnt in cv.items():
        for g in groups.get(c, []):
            gv[g].update(cnt)
    cmap = {c: (max(cv[c].items(), key=lambda kv: (kv[0] is not None, kv[1]))[0] if cv[c] else None) for c in eu5_cul}
    for c in cmap:
        if not cmap[c]:
            for g in groups.get(c, []):
                if gv[g]:
                    cmap[c] = max((kv for kv in gv[g].items() if kv[0]), key=lambda kv: kv[1])[0]
                    break
    return cmap, rmap, eu5_cul, eu5_rel


if __name__ == "__main__":
    cmap, rmap, ec, er = build()
    json.dump({"culture": cmap, "religion": rmap}, open(MOD / "tools/data/cr_map.json", "w"), indent=1)
    unres = [c for c, v in cmap.items() if not v]
    print(len(cmap), "cultures,", len(unres), "unresolved (no matched province):", sum(ec[c] for c in unres), "of", sum(ec.values()), "pop")
    print(sorted(unres, key=lambda c: -ec[c])[:50])
