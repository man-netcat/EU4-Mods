"""EU5 tag -> EU4 tag candidates by shared code + same display name."""
import re, glob
from loc2prov import yml, norm
from paths import EU4_GAME, EU5_GAME, MOD


def eu4_tags():
    tags = {}
    for f in (EU4_GAME / "common/country_tags").glob("*.txt"):
        for m in re.finditer(r"^([A-Z0-9]{3})\s*=\s*\"([^\"]+)\"", f.read_text(encoding="latin-1"), re.M):
            tags[m[1]] = m[2]
    return tags


def eu4_names():
    n = {}
    for f in (EU4_GAME / "localisation").glob("*_l_english.yml"):
        n.update({k: v for k, v in yml(f).items() if re.fullmatch(r"[A-Z0-9]{3}", k)})
    return n


def eu5_names():
    n = {}
    for f in (EU5_GAME / "main_menu/localization/english").glob("country_names_l_english.yml"):
        n.update(yml(f))
    return n


def province_owners():
    """EU4 province -> (owner tag, controller tag, {core tags}, pop, tier) by pop-weighted majority of mapped locations."""
    import json
    from collections import Counter, defaultdict
    from eu5setup import ownership
    from popdata import location_pops
    o, c, co = ownership()
    lp = location_pops()
    m = json.load(open(MOD / "tools/data/loc2prov.json"))
    out = {}
    for pid, v in m.items():
        ow, ct, cr = Counter(), Counter(), Counter()
        pop = 0.0
        for l in v["locations"]:
            w = lp.get(l, {"pop": 0})["pop"] or 0.01
            pop += w
            if l in o:
                ow[o[l]] += w
            if l in c:
                ct[c[l]] += w
            for t in co.get(l, ()):
                cr[t] += w
        tot = sum(w for w in [lp.get(l, {"pop": 0})["pop"] or 0.01 for l in v["locations"]])
        out[int(pid)] = dict(owner=ow.most_common(1)[0][0] if ow else None,
                             controller=ct.most_common(1)[0][0] if ct else None,
                             cores={t for t, w in cr.items() if w >= 0.4 * tot},
                             pop=pop, tier=v["tier"])
    return out


# EU5 tag -> EU4 tag where the same state carries a different name or code (hand-verified)
ALIASES = {
    "CHI": "YUA", "GLH": "GLH", "MAM": "MAM", "KOR": "KOR", "NOV": "NOV", "ERE": "ERE", "ORM": "ORM",
    "CHG": "CHG", "PEG": "PEG", "TEU": "TEU", "VOL": "VOL", "KIE": "KIE", "KAR": "KAR", "LBV": "LBV",
    "UBV": "UBV", "PAL": "PAL", "PAP": "PAP", "DAI": "DAI", "FRI": "FRI", "BOU": "BOU", "LOI": "LOI",
    "GRM": "GRM", "CND": "CND", "DUL": "DUL", "TIR": "TIR", "GNV": "GNV", "BRE": "BRE", "CHR": "CHR",
    "AJU": "AJU", "COC": "COC", "TLX": "TLX", "YOK": "YOK", "XIU": "XIU", "KBO": "KBO", "KNI": "KNI",
    "CRT": "CRT", "GEL": "GEL", "SUL": "SUL", "MBA": "MBA", "ZAP": "ZAP", "SRU": "SRU", "ASU": "ASU",
}


def build_table():
    """EU5 tag -> {eu4, new, name}. Only tags that matter (own/control/core a province, or are capitals)."""
    import json
    from collections import Counter
    import eu5info
    po = province_owners()
    n4, e4 = eu4_names(), eu4_tags()
    by_name = {}
    for t in sorted(e4):
        if t in n4:
            by_name.setdefault(norm(n4[t]), t)
    score = Counter()
    for v in po.values():
        for t in {v["owner"], v["controller"], *v["cores"]} - {None}:
            score[t] += 1
        if v["owner"]:
            score[v["owner"]] += 10
    table, taken = {}, {}
    for t, _ in score.most_common():
        nm = eu5info.display(t)
        cand = ALIASES.get(t) or by_name.get(norm(nm))
        if cand and cand not in taken:
            table[t] = dict(eu4=cand, new=False, name=nm)
            taken[cand] = t
        else:
            table[t] = dict(eu4=None, new=True, name=nm)
    used = set(e4) | set(taken)
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for t, r in table.items():
        if not r["new"]:
            continue
        code = t if (len(t) == 3 and t not in used and t.isalpha() and t.isupper()) else None
        if not code:
            base = re.sub(r"[^A-Z]", "", norm(r["name"]).upper() + "XXX")[:3]
            cands = [base] + [base[:2] + c for c in alpha] + [base[0] + a + b for a in alpha for b in alpha]
            code = next(c for c in cands if c not in used)
        r["eu4"] = code
        used.add(code)
    return table, score
