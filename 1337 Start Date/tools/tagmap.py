"""EU5 tag -> EU4 tag candidates by shared code + same display name."""
import re, glob
from loc2prov import yml, norm
from paths import EU4_GAME, EU5_GAME, MOD


def eu4_tags():
    tags = {}
    for f in sorted((EU4_GAME / "common/country_tags").glob("*.txt")):
        for m in re.finditer(r"^([A-Z0-9]{3})\s*=\s*\"([^\"]+)\"", f.read_text(encoding="latin-1"), re.M):
            tags[m[1]] = m[2]
    return tags


def eu4_names():
    n = {}
    for f in sorted((EU4_GAME / "localisation").glob("*_l_english.yml")):
        n.update({k: v for k, v in yml(f).items() if re.fullmatch(r"[A-Z0-9]{3}", k)})
    return n


def eu5_names():
    n = {}
    for f in (EU5_GAME / "main_menu/localization/english").glob("country_names_l_english.yml"):
        n.update(yml(f))
    return n


def partition_shared_pools(out, m, o, c, lp):
    """Several EU4 provinces can be matched to the same pool of EU5 locations (a whole EU5 area for lack of a
    finer name match). Giving each of them the pool's majority owner erases every other state in it
    (Navarre inside Castile's Navarra/Rioja). Instead the provinces of one pool are shared out among its
    owners in proportion to their pop, largest remainder first; an owner is put on the province whose name
    best matches one of its locations (otherwise in province order). Control follows the owner's locations."""
    from collections import Counter, defaultdict
    import eu5info
    groups = defaultdict(list)
    for pid, v in m.items():
        if v["tier"] in ("node", "area-node", "area-fallback"):
            groups[tuple(sorted(v["locations"]))].append(int(pid))
    prov_names = eu4_province_names()
    disp = eu5info.loc()
    for locs, pids in groups.items():
        if len(pids) < 2:
            continue
        weight = Counter()
        for l in locs:
            weight[o.get(l)] += lp.get(l, {"pop": 0})["pop"] or 0.01
        total = sum(weight.values())
        k = len(pids)
        quota = {t: w / total * k for t, w in weight.items()}
        seats = {t: int(q) for t, q in quota.items()}
        for t in sorted(quota, key=lambda t: (quota[t] - seats[t], weight[t], str(t)), reverse=True)[:k - sum(seats.values())]:
            seats[t] += 1
        order = sorted(seats, key=lambda t: (-weight[t], str(t)))
        pids = sorted(pids)

        def hit(pid, t):
            names = {norm(n) for n in prov_names.get(pid, ())}
            tn = norm(eu5info.display(t)) if t else ""
            if len(tn) >= 5 and any(n[:5] == tn[:5] for n in names):
                return True  # the state shares its name with the province (Navarre / Navarra)
            return any(norm(disp.get(l, l)) in names for l in locs if o.get(l) == t)

        remaining = Counter({t: n for t, n in seats.items() if n})
        assigned = {}
        for t in order:
            for pid in pids:
                if remaining[t] > 0 and pid not in assigned and hit(pid, t):
                    assigned[pid] = t
                    remaining[t] -= 1
        for pid in pids:
            if pid not in assigned:
                t = max((t for t in order if remaining[t] > 0), key=lambda t: remaining[t], default=None)
                if t is None:
                    break
                assigned[pid] = t
                remaining[t] -= 1
        for pid, t in assigned.items():
            own_locs = [l for l in locs if o.get(l) == t]
            ctrl = Counter(c.get(l) for l in own_locs if l in c)
            out[pid]["owner"] = t
            out[pid]["controller"] = ctrl.most_common(1)[0][0] if ctrl else t
            if t is not None:
                out[pid]["cores"] = out[pid]["cores"] | {t}


def eu4_province_names():
    from loc2prov import eu4_provinces
    return eu4_provinces()


def province_owners(fold=True):
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
    partition_shared_pools(out, m, o, c, lp)
    return fold_small_subjects(out) if fold else out


SUBJECT_TYPES = ("vassal", "fiefdom", "dominion", "appanage", "samanta", "tusi", "familial_governor",
                 "hanseatic_member", "tributary")
FOLDED = {}  # EU5 tag -> the overlord it was folded into (filled by fold_small_subjects)
FOLD_MAX = 2  # a non-vanilla subject holding at most this many EU4 provinces is not worth a tag


def overlords():
    """EU5 subject tag -> its overlord, from 12_diplomacy (tributaries included, chains resolved later)."""
    from paths import EU5_SETUP
    from pdx import parse, get
    dm = get(parse((EU5_SETUP / "12_diplomacy.txt").read_text(encoding="utf-8-sig")), "diplomacy_manager")
    out = {}
    for k, b in dm:
        if not isinstance(b, list):
            continue
        t = get(b, "subject_type") if k == "dependency" else get(b, "type")
        if t in SUBJECT_TYPES:
            out[get(b, "second")] = get(b, "first")
    return out


def vanilla_matched(tags):
    """The EU5 tags among `tags` that name-match a base-game EU4 tag (those keep their own tag)."""
    import eu5info
    n4, e4 = eu4_names(), eu4_tags()
    by_name = {norm(n4[t]) for t in e4 if t in n4}
    return {t for t in tags if ALIASES.get(t) or norm(eu5info.display(t)) in by_name}


def fold_small_subjects(po):
    """EU4 keeps a tag for a state worth playing or fighting, not for every EU5 county. A subject that is
    not a base-game tag and holds <= FOLD_MAX provinces is folded into its overlord (top of the chain that
    is itself kept): its provinces, control and cores pass up and it gets no tag."""
    from collections import Counter
    held = Counter(v["owner"] for v in po.values() if v["owner"])
    over = overlords()
    keep = vanilla_matched(held)

    def small(t):
        return t in over and held[t] <= FOLD_MAX and t not in keep

    def top(t):
        seen = set()
        while small(t) and t not in seen:
            seen.add(t)
            t = over[t]
        return t

    fold = {t: top(t) for t in list(over) if small(t) and top(t) != t}
    FOLDED.update(fold)
    for v in po.values():
        for key in ("owner", "controller"):
            v[key] = fold.get(v[key], v[key])
        v["cores"] = {fold.get(t, t) for t in v["cores"]}
    return po


# EU5 tag -> EU4 tag where the same state carries a different name or code (hand-verified)
ALIASES = {
    "CHI": "YUA", "GLH": "GLH", "MAM": "MAM", "KOR": "KOR", "NOV": "NOV", "ERE": "ERE", "ORM": "ORM",
    "CHG": "CHG", "PEG": "PEG", "TEU": "TEU", "VOL": "VOL", "KIE": "KIE", "KAR": "KAR", "LBV": "LBV",
    "UBV": "UBV", "PAL": "PAL", "PAP": "PAP", "DAI": "DAI", "FRI": "FRI", "BOU": "BOU", "LOI": "LOI",
    "GRM": "GRM", "CND": "CND", "DUL": "DUL", "TIR": "TIR", "GNV": "GNV", "BRE": "BRE", "CHR": "CHR",
    "AJU": "AJU", "COC": "COC", "TLX": "TLX", "YOK": "YOK", "XIU": "XIU", "KBO": "KBO", "KNI": "KNI",
    "ALS": "ALS", "CLM": "CLM", "JLW": "JLV", "KLT": "KLT", "MEN": "MEN", "MUA": "MPH", "NAV": "NAV",
    "ONN": "ONO", "MDY": "MAS",
    # same polity under another name in the base game (Viennois = Dauphine, Kangleipak = Manipur, Mecca = Hejaz ...)
    "ARK": "ARK", "AYD": "AYD", "BGK": "BGL", "CUT": "SDY", "DAU": "DAU", "DGH": "KAS", "FDL": "FAD", "GOW": "MKS",
    "GYO": "CAY", "HTR": "SHL", "JRW": "ALH", "KKA": "MOH", "MEC": "HED", "MIH": "SIS", "MLB": "MLB", "MLL": "MJO",
    "ONY": "ONE",
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
