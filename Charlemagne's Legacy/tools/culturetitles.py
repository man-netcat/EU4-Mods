#!/usr/bin/env python3
"""Lift CK3 government title names for tags.db tags.

Usage: python3 tools/culturetitles.py [TAG...] [--govs LIST] [--religion X]
       [--replace BLOCK] [--emit-only]

How CK3 does it (all data-driven): every rule in
game/common/flavorization/00_title_holders.txt is a named block whose
name doubles as the localisation key in
game/localization/english/culture/culture_titles_l_english.yml. Per
_flavourization.info the engine scans the rules highest-priority-first
and returns the FIRST eligible one; eligibility tests title binding,
government, heritage pillar, name list, religion, gender, tier and
flags. "Khwarezmshahdom" is the loc value of duchy_khorezm rules bound
to d_khorezm - an invented string nowhere.

Coverage (every tags.db tag MUST have a ck3_title; the ruler_title
lane is deprecated): the run reads each tag's explicit tier (rank),
ck3_title, CK3 culture -> our key via culturelift.CK3_TO_EU4, and the
ruler's CK3 faith resolved through the rite -> faith -> religion chain
(holder_faith, falling back to the FAITH_TO_RELIGION inversion of
tags.religion). Tags an already-written block covers (a trigger naming
the tag, the culture key, or our culture's group; the default_* /
muslim / hre_county defaults never count) are left alone - deliberate
hand flavor wins. The rest join per-culture blocks `<key>_titles`
(trigger primary_culture = key, or a tag OR-list when the key is not
one of our registered cultures): identical pick-sets within a culture
share one block; a tag whose CK3 title carries rule specials gets its
own `<key>_<TAG>_titles` block (trigger tag = CODE) with suffixed loc
keys, emitted BEFORE the shared block (first-match-wins). Heirs print
SHAHZADE at ranks 2+ for islam realms (ARB/AFR precedent) and HEIR
otherwise; consorts use the ruler form (CK3 has no consort terms).

Ranks: 1 county / 2 duchy / 3 kingdom / 4 empire / 5 hegemony; both
realm and ruler rows carry the same CK3 tier. Feudal+clan governments
by default (--govs adds administrative_government for Roman heirs).
$alias$ indirections resolve; [SelectLocalization pseudo-loc values
count as absent; contract-flagged rules (castellan and friends) can
never carry over and are skipped.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
CK3 = "/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game"
MOD = os.path.join(HERE, "..")
ZZ = os.path.join(MOD, "common", "government_names",
                  "zz_kar_government_names.txt")
TITLE_LOC = os.path.join(MOD, "localisation", "replace",
                         "title_names_l_english.yml")
OUR_CULTURES = os.path.join(MOD, "common", "cultures", "00_cultures.txt")

CK3_TITLES_DIR = os.path.join(CK3, "common", "flavorization")
CULT_LOC = os.path.join(CK3, "localization", "english", "culture",
                        "culture_titles_l_english.yml")
CK3_CULTURES_DIR = os.path.join(CK3, "common", "culture", "cultures")
CK3_LANDED_DIR = os.path.join(CK3, "common", "landed_titles")
CK3_FAITH_TYPES = os.path.join(CK3, "common", "religion", "faith_types",
                               "00_faith_types.txt")
CK3_RITE_TYPES = os.path.join(CK3, "common", "religion", "rite_types",
                              "00_rite_types.txt")

GENERIC_BLOCKS = {"default_monarchy", "default_republic",
                  "default_theocracy", "default_tribal", "hre_county",
                  "muslim_monarchy"}

# EU4 rank -> CK3 tier, plus vanilla fallback keys when no CK3 rule
# is eligible
RANKS = [
    (1, "county", "COUNTY", "COUNT", "COUNTESS"),
    (2, "duchy", "DUCHY", "DUKE", "DUCHESS"),
    (3, "kingdom", "KINGDOM", "KING", "QUEEN"),
    (4, "empire", "EMPIRE", "EMPEROR", "EMPRESS"),
    (5, "hegemony", "HEGEMONY", "EMPEROR", "EMPRESS"),
]
DEFAULT_GOVS = ""  # --govs optional add (administrative_government for Roman heirs)

MUSLIM_EU4 = {"sunni", "ibadi", "shiite"}


def gov_set(t, extra):
    """The CK3 governments a tag's realm can be read as. EU4 government +
    EU4 religion: tribal is tribal; theocracy covers CK3's theocratic ids;
    muslim monarchies are clan (feudal gates stay in the sibling rules);
    the rest are feudal. --govs adds more (Roman heirs)."""
    g = (t.government or "monarchy").lower()
    if g == "tribal":
        return {"tribal_government"} | extra
    if g == "theocracy":
        return {"theocracy_government",
                "ecclesiastical_government"} | extra
    if g == "republic":
        return {"republic_government"} | extra
    if (t.religion or "") in MUSLIM_EU4:
        return {"clan_government", "feudal_government"} | extra
    return {"feudal_government"} | extra

WHERE = {"county": "COUNT", "duchy": "DUKE", "kingdom": "KING",
         "empire": "EMPEROR", "hegemony": "EMPEROR"}
LOC_RE = re.compile(
    r'^ *([A-Za-z0-9_.\-]+):\s*(\d*)[ \t]*"((?:[^"\\]|\\.)*)"', re.M)
TIER_OF_PREFIX = {"b": "barony", "c": "county", "d": "duchy", "k": "kingdom",
                  "e": "empire", "h": "hegemony"}


class Rule:
    def __init__(self, name, body, order, tier_of_title):
        self.name = name
        self.order = order
        self.type = scalar(body, "type")
        self.gender = scalar(body, "gender")
        self.tier = scalar(body, "tier") or "none"
        self.special = scalar(body, "special")
        self.priority = int(scalar(body, "priority") or 0)
        self.governments = lst(body, "governments")
        self.heritages = lst(body, "heritages")
        self.religions = lst(body, "religions")
        self.faiths = lst(body, "faiths")
        self.name_lists = lst(body, "name_lists")
        self.flag = scalar(body, "flag")
        self.contract_flags = lst(body, "subject_contract_obligation_flags")
        self.titled = lst(body, "titles")
        self.de_jure_liege = lst(body, "de_jure_liege")
        if self.tier != "none":
            self.effective_tiers = {self.tier}
        elif self.titled:
            self.effective_tiers = {tier_of_title.get(t)
                                    for t in self.titled} - {None}
        else:
            self.effective_tiers = {"none"}


def scalar(body, field):
    m = re.search(r"(?m)^\t" + field + r"\s*=\s*([A-Za-z0-9_\-]+)", body)
    return m.group(1) if m else None


def lst(body, field):
    m = re.search(r"(?m)^\t" + field + r"\s*=\s*\{([^\n}]*?)\s*\}", body)
    return [s for s in m.group(1).split()] if m else []


def landed_tiers():
    """landed_titles entry prefixes: title id -> tier."""
    out = {}
    for fn in sorted(os.listdir(CK3_LANDED_DIR)):
        if not fn.endswith(".txt"):
            continue
        text = open(os.path.join(CK3_LANDED_DIR, fn),
                    encoding="utf-8-sig").read()
        for m in re.finditer(r"(?m)^\s*([bhcekd])_([A-Za-z0-9_\-]+)\s*=\s*\{",
                             text):
            out[f"{m.group(1)}_{m.group(2)}"] = TIER_OF_PREFIX[m.group(1)]
    return out


def parse_rules(tier_of_title):
    rules = {}
    order = 0
    for fn in sorted(os.listdir(CK3_TITLES_DIR)):
        if not fn.endswith(".txt") or fn.startswith("_"):
            continue
        text = open(os.path.join(CK3_TITLES_DIR, fn),
                    encoding="utf-8-sig").read().replace("\r\n", "\n")
        for m in re.finditer(r"(?m)^([A-Za-z0-9_\-]+)\s*=\s*\{", text):
            depth = 0
            for i in range(m.end(), len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    if depth == 0:
                        rules[m.group(1)] = Rule(m.group(1),
                                                 text[m.end():i], order,
                                                 tier_of_title)
                        order += 1
                        break
                    depth -= 1
    return rules


def ck3_loc_map():
    out = {}
    text = open(CULT_LOC, encoding="utf-8-sig").read().replace("\r\n", "\n")
    for key, vers, val in LOC_RE.findall(text):
        v = int(vers) if vers else 0
        if key not in out or v >= out[key][0]:
            out[key] = (v, val)
    return {k: v[1] for k, v in out.items()}


def resolve(locmap, key):
    val = locmap.get(key)
    if val is None:
        return None
    for _ in range(8):
        m = re.fullmatch(r"\$([A-Za-z0-9_\-]+)\$", val.strip())
        if not m:
            break
        val = locmap.get(m.group(1))
        if val is None:
            return None
    return None if "[SelectLocalization" in val else val


def culture_info(culture):
    """CK3 culture id -> (heritage pillar, name list)."""
    for fn in sorted(os.listdir(CK3_CULTURES_DIR)):
        if not fn.endswith(".txt"):
            continue
        text = open(os.path.join(CK3_CULTURES_DIR, fn),
                    encoding="utf-8-sig").read().replace("\r\n", "\n")
        m = re.search(r"(?m)^%s\s*=\s*\{" % (culture,), text)
        if m:
            deep = text[m.start():]
            hm = re.search(r"(?m)^\s{1,2}heritage\s*=\s*([a-z_0-9]+)", deep)
            nl = re.search(r"(?m)^\s{1,2}name_list\s*=\s*([a-z_0-9]+)", deep)
            return (hm.group(1) if hm else None,
                    nl.group(1) if nl else None)
    return None, None


def resolve_culture(culture, title):
    """tags.db culture column -> (CK3 culture id, our EU4 trigger key).

    addtag stores the 867 holder's CK3 culture after lifting it, so rows
    may hold either a CK3 id (khwarezmian) or the lifted EU4 key
    (al_misr_arabic). The lift map normalises direction; collisions
    (baranis/butr -> berber, coptic/egyptian -> al_misr_arabic, ...)
    resolve to the 867 title holder's own CK3 culture.
    """
    from culturelift import CK3_TO_EU4, holder_culture
    if culture_info(culture)[0]:
        return culture, CK3_TO_EU4.get(culture, culture)
    cands = sorted(k for k, v in CK3_TO_EU4.items() if v == culture)
    if len(cands) > 1:
        hc = holder_culture(title)[1]
        if hc in cands:
            return hc, culture
        return None, None
    if len(cands) == 1:
        return cands[0], culture
    return None, None


def religion_of(faith):
    """faith-like id (rite or faith) -> CK3 religion id, or None."""
    text = open(CK3_FAITH_TYPES, encoding="utf-8-sig").read()
    m = re.search(r"(?m)^%s\s*=\s*\{" % (faith,), text)
    if m:
        m2 = re.search(r"(?m)^\s*religion\s*=\s*([a-z_0-9]+)",
                       text[m.start():m.start() + 3000])
        if m2:
            return m2.group(1)
    text = open(CK3_RITE_TYPES, encoding="utf-8-sig").read()
    m = re.search(r"(?m)^%s\s*=\s*\{" % (faith,), text)
    if m:
        m2 = re.search(r"(?m)^\s*faith\s*=\s*([a-z_0-9]+)",
                       text[m.start():m.start() + 3000])
        if m2:
            return religion_of(m2.group(1))
    return None


def religion_of_eu4(eu4rel):
    """EU4 religion -> CK3 religion, via FAITH_TO_RELIGION inversion."""
    from culturelift import FAITH_TO_RELIGION
    for faith in sorted(f for f, eu in FAITH_TO_RELIGION.items()
                        if eu == eu4rel):
        r = religion_of(faith)
        if r:
            return r
    return None


def pick(rules, tier, rtype, gender, title, heritage, name_list, religion,
         govs, locmap):
    """CK3 semantics: rules sorted by priority then file order, first
    eligible wins. A rule with a narrower gate we cannot verify
    (contract flags, faiths, name lists) is never a guess."""
    for r in sorted(rules.values(), key=lambda r: (-r.priority, -r.order)):
        if r.type != rtype:
            continue
        if r.special not in (None, "holder"):
            continue
        if tier not in r.effective_tiers:
            continue
        if gender and r.gender != gender:
            continue
        if r.governments and not (set(r.governments) & govs):
            continue
        if r.heritages and heritage not in r.heritages:
            continue
        if r.name_lists and (not name_list or name_list not in r.name_lists):
            continue
        if r.religions and religion not in r.religions:
            continue
        if r.flag or r.contract_flags or r.faiths:
            continue
        if r.de_jure_liege:
            continue  # de-jure liege gates cannot be verified in EU4 scope
        if (r.titled and not title) or (r.titled and title
                                        and title not in r.titled):
            continue
        val = resolve(locmap, r.name)
        if val is None:
            continue
        return (r, val)
    return None


def read_txt(path):
    return open(path, encoding="cp1252").read()


def zz_blocks():
    """name -> body text of every block in our zz government_names file."""
    text = read_txt(ZZ).replace("\r\n", "\n")
    out = {}
    for m in re.finditer(r"(?m)^([A-Za-z0-9_]+)\s*=\s*\{", text):
        depth = 0
        for i in range(m.end() - 1, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out[m.group(1)] = text[m.end():i]
                    break
    return out


def trigger_of(body):
    """The body's trigger section text ("" when absent)."""
    m = re.search(r"(?m)^\s*trigger\s*=\s*\{", body)
    if not m:
        return ""
    depth = 0
    for i in range(m.end() - 1, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                return body[m.end():i]
    return ""


def coverage_index(blocks):
    """(tags, cultures, groups) covered by existing non-default blocks."""
    tagmap, cultmap, groupmap = {}, {}, {}
    for name, body in blocks.items():
        if name in GENERIC_BLOCKS or name.endswith("_titles"):
            continue
        trig = trigger_of(body)
        for t in re.findall(r"(?m)^\s*tag\s*=\s*([A-Z0-9]{3})", trig):
            tagmap.setdefault(t, name)
        for c in re.findall(r"primary_culture\s*=\s*([a-z_0-9]+)", trig):
            cultmap.setdefault(c, name)
        for g in re.findall(r"culture_group\s*=\s*([a-z_0-9]+)", trig):
            groupmap.setdefault(g, name)
    return tagmap, cultmap, groupmap


def our_cultures():
    """Our 00_cultures.txt: culture key -> culture group."""
    text = open(OUR_CULTURES, encoding="cp1252").read().replace("\r\n", "\n")
    out = {}
    group = None
    for ln in text.split("\n"):
        top = re.match(r"^([a-z_0-9]+)\s*=\s*\{", ln)
        if top:
            group = top.group(1)
            continue
        m = re.match(r"^\t([a-z_0-9]+)\s*=\s*\{", ln)
        if m and group:
            out[m.group(1)] = group
    return out


def all_tags(subset):
    import db
    import models
    s = db.session()
    rows = s.query(models.Tag).all()
    s.close()
    if subset:
        wanted = {t.upper() for t in subset}
        missing = wanted - {r.tag for r in rows}
        if missing:
            sys.exit(f"not in tags.db: {sorted(missing)}")
        rows = [r for r in rows if r.tag in wanted]
    return rows


def identity(picks):
    """Stable fingerprint of a ladder: the CK3 rule name per slot."""
    return tuple(
        tuple((picks[r][i][0].name if picks[r][i] else None)
              for i in range(3))
        for r in range(1, 6))


def body_of(key, suffixed, tags, picks, islam, reg):
    """Block body + fresh loc keys (outcome: dict KEY -> value).
    suffixed = tag code for a tag-specific block, None for the shared
    culture block."""
    up = key.upper()
    if suffixed:
        up = f"{up}_{suffixed}"
    keys = {}
    lines = ["\trank = {"]
    for rank, tier, fb, fbm, fbf in RANKS:
        slot = picks[rank][0]
        if slot:
            k = f"{up}_{tier.upper()}"
            rows = f"\t\t{rank} = {k}  # {slot[0].name}"
            keys[k] = slot[1]
        else:
            k = fb  # vanilla key, already localised
            rows = f"\t\t{rank} = {k}"
        lines.append(rows)
    lines.append("\t}")
    lines.append("")
    for kind, index in (("ruler_male", 1), ("ruler_female", 2)):
        lines.append(f"\t{kind} = {{")
        for rank, tier, fb, fbm, fbf in RANKS:
            res = picks[rank][index]
            if res:
                k = f"{up}_{WHERE[tier]}_MALE" if kind == "ruler_male" \
                    else f"{up}_{WHERE[tier]}_FEMALE"
                lines.append(f"\t\t{rank} = {k}  # {res[0].name}")
                keys[k] = res[1]
            else:
                lines.append(f"\t\t{rank} = "
                             f"{fbm if kind == 'ruler_male' else fbf}")
        lines.append("\t}")
        lines.append("")
    lines.append("\tconsort_male = {")
    for rank, tier, fb, fbm, fbf in RANKS:
        res = picks[rank][1]
        if res:
            k = f"{up}_{WHERE[tier]}_MALE"
            lines.append(f"\t\t{rank} = {k}  # consort uses the ruler form")
            keys.setdefault(k, res[1])
        else:
            lines.append(f"\t\t{rank} = PRINCE_CONSORT")
    lines.append("\t}")
    lines.append("")
    lines.append("\tconsort_female = {")
    for rank, tier, fb, fbm, fbf in RANKS:
        res = picks[rank][2]
        if res:
            k = f"{up}_{WHERE[tier]}_FEMALE"
            lines.append(f"\t\t{rank} = {k}  # {res[0].name}")
            keys.setdefault(k, res[1])
        else:
            lines.append(f"\t\t{rank} = CONSORT")
    lines.append("\t}")
    lines.append("")
    lines.append("\their_male = {")
    lines.append("\t\t1 = HEIR")
    for rank in range(2, 6):
        lines.append(f"\t\t{rank} = {'SHAHZADE' if islam else 'HEIR'}")
    lines.append("\t}")
    lines.append("")
    lines.append("\their_female = {")
    lines.append("\t\t1 = HEIR_fem")
    for rank in range(2, 6):
        lines.append(f"\t\t{rank} = {'SHAHZADE' if islam else 'HEIR_fem'}")
    lines.append("\t}")
    lines.append("")
    lines.append("\ttrigger = {")
    lines.append("\t\tgovernment = monarchy")
    if suffixed:
        lines.append(f"\t\ttag = {suffixed}")
    elif reg:
        lines.append(f"\t\tprimary_culture = {key}")
    else:
        lines.append("\t\tOR = {")
        for t in tags:
            lines.append(f"\t\t\ttag = {t}")
        lines.append("\t\t}")
    lines.append("\t}")
    return "\n".join(lines), keys


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tags", nargs="*",
                    help="tags.db codes to process (default: all)")
    ap.add_argument("--govs", default=DEFAULT_GOVS,
                    help="extra CK3 governments merged into every tag's "
                         "inferred set (administrative for Roman heirs)")
    ap.add_argument("--religion",
                    help="override the CK3 religion gate for every tag; "
                         "NONE drops it")
    ap.add_argument("--replace", help="remove this old zz block first")
    ap.add_argument("--emit-only", action="store_true",
                    help="print the plan, write nothing")
    a = ap.parse_args(argv)

    from culturelift import holder_faith, CK3_TO_EU4

    blocks = zz_blocks()
    tagcov, cultcov, groupcov = coverage_index(blocks)
    ours = our_cultures()
    tier_of_title = landed_tiers()
    rules = parse_rules(tier_of_title)
    locmap = ck3_loc_map()
    govs_extra = set(a.govs.split())
    loc_file = read_utf8(TITLE_LOC)
    existing_loc = set(re.findall(r"(?m)^ ([A-Za-z0-9_]+):", loc_file))

    broken = []
    covered_keys = set()
    plan = []
    for t in all_tags(a.tags):
        if not t.ck3_title:
            broken.append((t.tag, "no ck3_title - selfcheck should catch it"))
            continue
        if t.ck3_title not in tier_of_title:
            broken.append((t.tag, f"unknown CK3 title {t.ck3_title}"))
            continue
        ck3cult, key = resolve_culture(t.culture, t.ck3_title)
        if key is None:
            broken.append((t.tag,
                           f"culture {t.culture}: no CK3 id resolves it "
                           f"(map has no source for this key)"))
            continue
        if key != t.culture:
            key = CK3_TO_EU4.get(ck3cult, key)
        reg = key in ours
        backing = (tagcov.get(t.tag)
                   or (cultcov.get(key) if reg else None)
                   or (groupcov.get(ours[key]) if reg else None))
        if backing:
            print(f"  {t.tag:<5} covered        by {backing}")
            covered_keys.add(key)
            continue
        heritage, name_list = culture_info(ck3cult)
        if not heritage:
            broken.append((t.tag, f"{ck3cult}: no heritage pillar"))
            continue
        govs = gov_set(t, govs_extra)
        religion = a.religion
        if a.religion == "NONE":
            religion = None
        if religion is None:
            try:
                faith = holder_faith(t.ck3_title)[1]
                religion = religion_of(faith) or religion_of_eu4(t.religion)
            except Exception:
                religion = None
        islam = religion == "islam_religion"
        picks = {}
        for rank, tier, fb, fbm, fbf in RANKS:
            picks[rank] = (
                pick(rules, tier, "title", None, t.ck3_title, heritage,
                     name_list, religion, govs, locmap),
                pick(rules, tier, "character", "male", t.ck3_title,
                     heritage, name_list, religion, govs, locmap),
                pick(rules, tier, "character", "female", t.ck3_title,
                     heritage, name_list, religion, govs, locmap),
                tier)
        plan.append({"key": key, "tag": t.tag, "rank": t.rank,
                     "title": t.ck3_title,
                     "religion": religion or None, "islam": islam,
                     "reg": reg, "picks": picks})

    inserts = []
    groups = {}
    order_keys = []
    for p in plan:
        groups.setdefault(p["key"], []).append(p)
        if p["key"] not in order_keys:
            order_keys.append(p["key"])
    clash = covered_keys & set(groups)
    for key in clash:
        print(f"  ! {key}: planned ladder would shadow an existing hand "
              f"block for a covered tag of the same culture - dropping "
              f"the ladder, hand flavor wins")
        order_keys.remove(key)

    for key in order_keys:
        members = groups[key]
        byid = {}
        for p in members:
            byid.setdefault(identity(p["picks"]), []).append(p)
        base_id = max(byid, key=lambda i: len(byid[i]))
        specials = [p for i, ps in byid.items() for p in ps
                    if i != base_id]
        common = byid[base_id]

        for p in sorted(specials, key=lambda p: p["tag"]):
            name = f"{key}_{p['tag'].lower()}_titles"
            if name in blocks:
                print(f"  {p['tag']:<5} own block exists {name}")
                continue
            head = (f"# lifted from CK3 flavorization for {p['tag']}: "
                    f"{p['title']} carries rule specials the shared "
                    f"{key}_titles block cannot express; Islam heir = "
                    f"{p['islam']}")
            body, keys = body_of(key, p["tag"], [p["tag"]], p["picks"],
                                 p["islam"], p["reg"])
            inserts.append((name, head, body, keys, p))
            print(f"  {p['tag']:<5} own block     {name}")
        if common:
            name = f"{key}_titles"
            if name in blocks:
                print(f"  {key:<18} block exists   {name} "
                      f"({len(common)} tags)")
                continue
            ladders = ", ".join(f"{p['tag']}(r{p['rank']})" for p in common)
            head = (f"# CK3 ladders for {ladders}"
                    + (f" - islam realms (Shahzade)"
                       if all(p["islam"] for p in common) else ""))
            body, keys = body_of(key, None, [p["tag"] for p in common],
                                 common[0]["picks"], common[0]["islam"]
                                 and len({p["islam"] for p in common}) == 1,
                                 common[0]["reg"])
            inserts.append((name, head, body, keys, common[0]))
            print(f"  {key:<18} culture block {name} ({ladders})")

    fresh = {}
    from enc import encname
    for _, _, _, keys, _ in inserts:
        for k, v in keys.items():
            if k not in existing_loc:
                fresh[k] = encname(v)
                existing_loc.add(k)

    print(f"\nplan: {len({p['key'] for p in plan})} culture ladders -> "
          f"{len(inserts)} blocks, {len(fresh)} new loc keys; "
          f"broken: {len(broken)}")
    for tag, why in broken:
        print(f"  ! {tag}: {why}")

    if a.emit_only:
        for name, head, body, keys, p in inserts:
            print(f"\n--- {name} ---\n{head}\n\n{body}\n")
        print("--- loc ---")
        for k, v in fresh.items():
            print(f' {k}:0 "{v}"')
        return 0

    if not inserts:
        print("nothing to insert")
        return 0

    zz = read_txt(ZZ).replace("\r\n", "\n")
    if a.replace:
        m = re.search(r"(?m)^%s\s*=\s*\{" % (re.escape(a.replace),), zz)
        if not m:
            sys.exit(f"--replace {a.replace}: block not found in zz file")
        depth = 0
        end = None
        for i in range(m.end() - 1, len(zz)):
            if zz[i] == "{":
                depth += 1
            elif zz[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end is None:
            sys.exit(f"--replace {a.replace}: unterminated block")
        while end < len(zz) and zz[end] == "\n":
            end += 1
        zz = zz[:m.start()] + "\n" + zz[end:]
        print(f"  removed old block {a.replace}")
    marker = "muslim_monarchy = {"
    if zz.count(marker) != 1:
        sys.exit("anchor 'muslim_monarchy = {' not unique in zz file")
    insert = "\n\n".join(f"{name} = {{\n{head}\n{body}\n}}\n"
                         for name, head, body, _, _ in inserts)
    zz = zz.replace(marker, insert + "\n\n" + marker, 1)
    open(ZZ, "w", encoding="cp1252", newline="").write(
        zz.replace("\n", "\r\n"))
    print(f"  zz: {len(inserts)} blocks inserted before muslim_monarchy")

    if fresh:
        loc_file = read_utf8(TITLE_LOC)
        text = (loc_file.rstrip("\n") + "\n\n") + "\n".join(
            f' {k}:0 "{v}"' for k, v in fresh.items()) + "\n"
        open(TITLE_LOC, "w", encoding="utf-8-sig",
             newline="").write(text)
        print(f"  title loc: {len(fresh)} keys appended")
    if broken:
        print("  NOTE: broken tags above left uncovered - fix and re-run")
    return 0


def read_utf8(path):
    return open(path, encoding="utf-8-sig").read()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
