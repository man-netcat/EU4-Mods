#!/usr/bin/env python3
"""common/cultures/00_cultures.txt, built from the base game's file and CK3.

Nothing of either game is stored here. The build takes EU4's own cultures file
and applies a small plan (names of things to drop, move or add) while every
name list comes from CK3:

  1. drop the groups and cultures the 867 world has no use for (the Americas,
     post-867 peoples, the Greek and Egyptian "lost cultures");
  2. move cultures between groups (a group that loses its last culture gives
     its group-level name lists to the group its cultures went to);
  3. add the cultures EU4 lacks (LIFTS): the entry is CK3's own culture, with
     the name list that culture names (`name_list = ...`), its dynasties,
     male and female names;
  4. swap the names of a vanilla culture for another CK3 culture's (REPURPOSE).

The localisation of the added cultures is CK3's own text. The file is written
whenever it differs, before anything reads it (tagdb reads it on import).

    python3 tools/cultures.py          # rewrite the file and its localisation
    python3 tools/cultures.py --check  # exit 1 if either is stale
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import CK3_GAME, EU4_GAME  # noqa: E402

MOD = os.path.join(HERE, "..")
OUT = os.path.join(MOD, "common", "cultures", "00_cultures.txt")
LOC = os.path.join(MOD, "localisation", "karolingian_cultures_l_english.yml")
LOC_REPLACE = os.path.join(MOD, "localisation", "replace", "karolingian_cultures_l_english.yml")
VANILLA = os.path.join(str(EU4_GAME), "common", "cultures", "00_cultures.txt")
CK3_LISTS = os.path.join(str(CK3_GAME), "common", "culture", "name_lists")
CK3_CULTURES = os.path.join(str(CK3_GAME), "common", "culture", "cultures")

NAMES = ("dynasty_names", "male_names", "female_names")
NOT_CULTURES = NAMES + ("country", "province")

# ---- the plan ----------------------------------------------------------------

# the New World and the Slavic group whose cultures went elsewhere
REMOVE_GROUPS = (
    "andean_group", "apachean", "araucanian", "aridoamerican", "caddoan", "carribean",
    "central_algonquian", "central_american", "chibchan",
    "eastern_algonquian", "eskaleut", "iroquoian", "je", "je_tupi", "maranon", "mataco",
    "maya", "muskogean", "na_dene", "otomanguean", "penutian", "plains_algonquian",
    "siouan", "sonoran",
)
# peoples that come after 867 and the "lost cultures" of antiquity
REMOVE_CULTURES = (
    "lower_saxon", "flemish", "frisian", "english", "american", "maltese", "mexican",
    "platinean", "portugese", "burgundian", "wallonian", "quebecois", "slovene",
    "hungarian", "maori", "astrakhani", "kazani", "mishary", "nogaybak", "atlantean",
    "spartan", "athenian", "old_egyptian", "jan_mayenese", "phoenician", "babylonian",
    "etrurian", "parthian", "scythian",
)
# culture -> group it joins
MOVES = {
    "pommeranian": "west_slavic", "prussian": "baltic", "hessian": "frankish",
    "franconian": "frankish", "dutch": "frankish", "finnish": "finno_ugric",
    "sapmi": "finno_ugric", "karelian": "finno_ugric", "welsh": "brythonic",
    "cornish": "brythonic", "breton": "brythonic",
    "estonian": "finno_ugric", "goths": "germanic",
    # peoples whose CK3 heritage is not their vanilla group's
    "hebrew": "turko_semitic", "aramaic": "turko_semitic", "bashkir": "altaic",
    "buryat": "altaic", "gondi": "dravidian",
    "roman": "latin", "anglosaxon": "british", "livonian": "baltic",
}
# new group -> (graphical culture, the group it is listed before)
NEW_GROUPS = {
    "brythonic": ("westerngfx", "british"),
    "frankish": ("westerngfx", "french"),
}
# EU4 culture -> (group, CK3 culture whose name list and loc it takes, primary tag).
# The group is ours; everything else about the culture is CK3's.
LIFTS = {
    "andalusian": ("iberian", "andalusian", None),
    "avar": ("altaic", "avar", "VSG"),
    "baranis": ("maghrebi", "baranis", None),
    "bjarmian": ("finno_ugric", "samoyed", None),
    "butr": ("maghrebi", "butr", None),
    "carantanian": ("west_slavic", "carantanian", None),
    "cisalpine": ("latin", "cisalpine", None),
    "cumbrian": ("brythonic", "cumbrian", None),
    "frankish": ("frankish", "frankish", "FRA"),
    "guanche": ("maghrebi", "guanches", "CNI"),
    "italian": ("latin", "italian", None),
    "kerait": ("altaic", "kerait", None),
    "khitan": ("altaic", "khitan", "KTN"),
    "khwarezmian": ("iranian", "khwarezmian", "AFR"),
    "komi": ("finno_ugric", "komi", None),
    "levantine": ("turko_semitic", "levantine", None),
    "maghrebi": ("maghrebi", "maghrebi", "SIC"),
    "magyar": ("finno_ugric", "hungarian", "MGY"),
    "mari": ("finno_ugric", "mari", None),
    "merya": ("finno_ugric", "merya", None),
    "meshchera": ("finno_ugric", "meshchera", None),
    "mordvin": ("finno_ugric", "mordvin", None),
    "naiman": ("altaic", "naiman", None),
    "pecheneg": ("altaic", "pecheneg", None),
    "pictish": ("brythonic", "pictish", None),
    "polabian": ("west_slavic", "polabian", "LUT"),
    "slovien": ("west_slavic", "slovien", "CLI"),
    "amis": ("pacific", "amis", None),
    "ryukyuan": ("japanese_g", "ryukyuan", None),
    # vanilla cultures whose block is replaced outright
    "roman": ("latin", "roman", None),
    "russian": ("east_slavic", "russian", None),
}
# vanilla culture -> CK3 culture whose name list replaces its names (group, graphics
# and primary tag stay: EU4's Saigoku and Togoku stand in for CK3's Yamato and Emishi)
REPURPOSE = {"japanese": "japanese", "togoku": "emishi"}
# vanilla cultures shown under CK3's name for the same people -> CK3 culture key
RENAME_FROM_CK3 = {
    "leonese": "asturleonese", "castillian": "castilian", "occitain": "occitan",
    "highland_scottish": "gaelic", "togoku": "emishi", "japanese": "japanese",
}
# a group is shown under CK3's name for it
GROUP_NAME_FROM_CK3 = {"frankish": "frankish_group", "brythonic": "brythonic_group",
                       "byzantine": "byzantine_group"}


# CK3 heritage -> the EU4 groups a culture of that heritage may sit in (validate fails otherwise).
# EU4's groups are looser than CK3's heritages (Turks and Mongols share altaic, Arabs and Hebrews
# turko_semitic, Franks and Rhinelanders frankish); this lists what each heritage may share with.
HERITAGE_GROUPS = {
    "heritage_west_germanic": ("british", "germanic", "frankish"),
    "heritage_central_germanic": ("germanic", "frankish"),
    "heritage_north_germanic": ("scandinavian",),
    "heritage_gothic": ("germanic",),
    "heritage_frankish": ("frankish", "french"),
    "heritage_latin": ("latin",),
    "heritage_iberian": ("iberian",),
    "heritage_brythonic": ("brythonic",),
    "heritage_goidelic": ("gaelic",),
    "heritage_baltic": ("baltic",),
    "heritage_balto_finnic": ("finno_ugric",),
    "heritage_volga_finnic": ("finno_ugric",),
    "heritage_ugro_permian": ("finno_ugric",),
    "heritage_magyar": ("finno_ugric",),
    "heritage_west_slavic": ("west_slavic",),
    "heritage_south_slavic": ("south_slavic",),
    "heritage_east_slavic": ("east_slavic",),
    "heritage_vlach": ("carpathian",),
    "heritage_byzantine": ("byzantine",),
    "heritage_arabic": ("turko_semitic", "maghrebi"),
    "heritage_israelite": ("turko_semitic",),
    "heritage_syriac": ("turko_semitic",),
    "heritage_berber": ("maghrebi",),
    "heritage_iranian": ("iranian", "caucasian"),
    "heritage_turkic": ("altaic",),
    "heritage_mongolic": ("altaic",),
    "heritage_tungusic": ("evenks",),
    "heritage_dravidian": ("dravidian",),
    "heritage_indo_aryan": ("eastern_aryan", "hindusthani", "western_aryan"),
}


# ---- text plumbing ----------------------------------------------------------

def _read(path):
    return open(path, encoding="cp1252", errors="replace").read().replace("\r\n", "\n")


def _code(line):
    return line.split("#", 1)[0]


def split_items(lines):
    """A block body -> [(name, kind, [raw lines])]. Comments and blank lines ride
    with the item that follows them. kind: 'block' (name = { ... }) or 'line'."""
    out, pend, depth, cur = [], [], 0, None
    for ln in lines:
        c = _code(ln)
        if depth == 0 and cur is None:
            m = re.match(r"^\s*([A-Za-z0-9_]+)\s*=\s*(\{?)", c)
            if m:
                depth = c.count("{") - c.count("}")
                cur = [m.group(1), "block" if m.group(2) else "line", pend + [ln]]
                pend = []
                if depth <= 0:
                    out.append(tuple(cur))
                    cur, depth = None, 0
                continue
            pend.append(ln)
            continue
        cur[2].append(ln)
        depth += c.count("{") - c.count("}")
        if depth <= 0:
            out.append(tuple(cur))
            cur, depth = None, 0
    if pend:
        out.append((None, "tail", pend))
    return out


def parse_groups(text):
    """text -> (preamble lines, [(group name, head line, body items, tail lines)])"""
    lines = text.split("\n")
    pre, groups, i = [], [], 0
    while i < len(lines):
        m = re.match(r"^([A-Za-z0-9_]+)\s*=\s*\{", _code(lines[i]))
        if not m:
            pre.append(lines[i])
            i += 1
            continue
        depth, j, body = _code(lines[i]).count("{") - _code(lines[i]).count("}"), i + 1, []
        while depth > 0:
            depth += _code(lines[j]).count("{") - _code(lines[j]).count("}")
            body.append(lines[j])
            j += 1
        closing = body.pop()  # the group's own closing brace
        groups.append([m.group(1), lines[i], split_items(body), closing])
        i = j
    return pre, groups


# ---- CK3 --------------------------------------------------------------------

_ck3_name_list = {}


def ck3_culture_name_list(ck3cult):
    if not _ck3_name_list:
        for fn in sorted(os.listdir(CK3_CULTURES)):
            text = open(os.path.join(CK3_CULTURES, fn), encoding="utf-8-sig",
                        errors="replace").read()
            for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{(.*?)^\}", text, re.S):
                nl = re.search(r"name_list\s*=\s*(\w+)", m.group(2))
                if nl:
                    _ck3_name_list[m.group(1)] = nl.group(1)
    return _ck3_name_list.get(ck3cult)


def _ck3_list_block(list_key):
    for fn in sorted(os.listdir(CK3_LISTS)):
        text = open(os.path.join(CK3_LISTS, fn), encoding="utf-8-sig", errors="replace").read()
        m = re.search(r"(?m)^%s\s*=\s*\{" % re.escape(list_key), text)
        if m:
            j, depth, k = text.index("{", m.start()), 0, text.index("{", m.start())
            while True:
                if text[k] == "{":
                    depth += 1
                elif text[k] == "}":
                    depth -= 1
                    if depth == 0:
                        return text[j + 1:k]
                k += 1
    return None


def _section(block, *names):
    for nm in names:
        i = block.find(nm)
        if i < 0:
            continue
        j = block.find("{", i)
        depth, k = 0, j
        while True:
            if block[k] == "{":
                depth += 1
            elif block[k] == "}":
                depth -= 1
                if depth == 0:
                    break
            k += 1
        return block[j + 1:k]
    return ""


def _tokens(text):
    return re.findall(r'"([^"]+)"|(\S+)', text)


def _clean(tok):
    tok = re.sub(r"\s+", " ", tok.replace("_", " ")).strip()
    try:
        tok.encode("cp1252")
    except UnicodeEncodeError:
        return None
    return tok or None


_heritage = {}


def culture_heritage(eu4key):
    """The CK3 heritage of an EU4 culture: that of the CK3 culture of the same name, else the
    commonest among the CK3 cultures mapped to it. None when CK3 gives it none."""
    import collections

    import culturelift

    if not _heritage:
        for fn in sorted(os.listdir(CK3_CULTURES)):
            text = open(os.path.join(CK3_CULTURES, fn), encoding="utf-8-sig", errors="replace").read()
            for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{(.*?)^\}", text, re.S):
                h = re.search(r"heritage\s*=\s*(\w+)", m.group(2))
                if h:
                    _heritage[m.group(1)] = h.group(1)
    cands = [k for k, v in culturelift.CK3_TO_EU4.items() if v == eu4key and k in _heritage]
    if not cands:
        return None
    if eu4key in cands:
        return _heritage[eu4key]
    return collections.Counter(_heritage[c] for c in cands).most_common(1)[0][0]


def heritage_misfits():
    """[(culture, group, heritage)] for cultures sitting in a group their CK3 heritage does not allow."""
    pre, groups = parse_groups(_read(OUT))
    out = []
    for gname, _head, items, _close in groups:
        for iname, kind, _lines in items:
            if _is_culture(iname, kind):
                h = culture_heritage(iname)
                ok = HERITAGE_GROUPS.get(h)
                if ok and gname not in ok:
                    out.append((iname, gname, h))
    return out


def ck3_names(ck3cult):
    """(dynasties, males, females) of the name list a CK3 culture names."""
    key = ck3_culture_name_list(ck3cult)
    block = _ck3_list_block(key) if key else None
    if not block:
        raise SystemExit(f"cultures: CK3 culture {ck3cult} has no name list")

    def names(*sections, strip=""):
        out = []
        for t in _tokens(_section(block, *sections)):
            tok = t[0] or t[1]
            if strip:
                if not tok.startswith(strip):
                    continue
                tok = tok[len(strip):]
            c = _clean(tok)
            if c:
                out.append(c)
        return list(dict.fromkeys(out))

    dyns = names("cadet_dynasty_names", "dynasty_names", strip="dynn_")
    males, females = names("male_names"), names("female_names")
    if not (dyns and males and females):
        raise SystemExit(f"cultures: short name list for {ck3cult}: "
                         f"{len(dyns)}/{len(males)}/{len(females)}")
    return dyns, males, females


def _q(tok):
    return f'"{tok}"' if re.search(r"[^A-Za-z0-9_'-]", tok) else tok


def _wrap(items):
    lines, cur = [], "\t\t\t"
    for tok in items:
        tok = _q(tok)
        if len(cur) + len(tok) + 1 > 110:
            lines.append(cur.rstrip())
            cur = "\t\t\t"
        cur += tok + " "
    lines.append(cur.rstrip())
    return lines


def _list_lines(key, items):
    return [f"\t\t{key} = {{"] + _wrap(items) + ["\t\t}"]


def culture_lines(key, ck3cult, primary=None, keep=()):
    dyns, males, females = ck3_names(ck3cult)
    out = [f"\t{key} = {{"]
    if primary:
        out.append(f"\t\tprimary = {primary}")
        out.append("")
    out += _list_lines("dynasty_names", dyns) + _list_lines("male_names", males)
    out += _list_lines("female_names", females)
    for ln in keep:
        out.append(ln)
    out.append("\t}")
    return out


def repurposed(raw, ck3cult):
    """A vanilla culture block with its three name lists swapped for CK3's."""
    head, close = raw[0], raw[-1]
    items = split_items(raw[1:-1])
    dyns, males, females = ck3_names(ck3cult)
    new = {"dynasty_names": dyns, "male_names": males, "female_names": females}
    out, done = [head], set()
    for name, _kind, lines in items:
        if name in new:
            out += _list_lines(name, new[name])
            done.add(name)
        else:
            out += lines
    for name, items_ in new.items():
        if name not in done:
            out += _list_lines(name, items_)
    out.append(close)
    return out


# ---- the build --------------------------------------------------------------

def _is_culture(name, kind):
    return kind == "block" and name not in NOT_CULTURES


def build_text():
    pre, groups = parse_groups(_read(VANILLA))
    by_name = {g[0]: g for g in groups}
    taken = {}  # culture -> raw lines, for MOVES and REPURPOSE
    for g in groups:
        for name, kind, lines in g[2]:
            if _is_culture(name, kind):
                taken[name] = lines
    removed = set(REMOVE_CULTURES) | set(LIFTS)
    # a removed group's name lists follow its cultures
    heirs = {}
    for gname in REMOVE_GROUPS:
        dests = [MOVES[c] for c, k, _ in by_name[gname][2]
                 if _is_culture(c, k) and c in MOVES]
        if dests:
            heirs[max(set(dests), key=dests.count)] = gname

    adds = {}  # group -> culture blocks to append
    for c, dest in MOVES.items():
        if c in removed or c not in taken:
            continue
        adds.setdefault(dest, []).append(taken[c])
    for key, (grp, ck3c, primary) in LIFTS.items():
        adds.setdefault(grp, []).append(culture_lines(key, ck3c, primary))

    out = list(pre)

    def emit(g):
        name, head, items, closing = g
        res = [head]
        moved_out = set(MOVES) | removed
        for iname, kind, lines in items:
            if kind == "tail":
                continue
            if _is_culture(iname, kind):
                if iname in moved_out:
                    continue
                if iname in REPURPOSE:
                    lines = repurposed(lines, REPURPOSE[iname])
            res += lines
        if name in heirs:
            for iname, kind, lines in by_name[heirs[name]][2]:
                if kind == "block" and iname in NAMES:
                    res += lines
        for blk in adds.get(name, []):
            res += [""] + blk
        res.append(closing)
        return res

    emitted = set()
    for g in groups:
        if g[0] in REMOVE_GROUPS:
            continue
        for ng, (gfx, before) in NEW_GROUPS.items():
            if before == g[0] and ng not in emitted:
                out += [f"{ng} = {{", f"\tgraphical_culture = {gfx}"]
                for blk in adds.get(ng, []):
                    out += [""] + blk
                out += ["}", ""]
                emitted.add(ng)
        out += emit(g) + [""]
    text = "\n".join(out).rstrip("\n") + "\n"
    return text


_loc_cache = {}


def ck3_loc(keys):
    """CK3's English text for each wanted key (own reader: tagdb imports this
    module while ck3.py is still loading, so ck3.loc is not available here)."""
    want = set(keys) - set(_loc_cache)
    if want:
        rx = re.compile(r'^\s*(%s):\d*\s+"(.*)"' % "|".join(re.escape(k) for k in want))
        root = os.path.join(str(CK3_GAME), "localization", "english")
        for dp, _dn, fns in os.walk(root):
            for fn in sorted(fns):
                if not fn.endswith(".yml"):
                    continue
                for ln in open(os.path.join(dp, fn), encoding="utf-8-sig", errors="replace"):
                    m = rx.match(ln)
                    if m and m.group(1) not in _loc_cache:
                        _loc_cache[m.group(1)] = m.group(2)
        for k in want:
            _loc_cache.setdefault(k, None)
    return {k: _loc_cache[k] for k in keys}


def _loc_pairs():
    """(new loc entries, replace loc entries) as CK3 names them."""
    keys = ([c for _g, c, _p in LIFTS.values()] + list(GROUP_NAME_FROM_CK3.values())
            + list(RENAME_FROM_CK3.values()))
    got = ck3_loc(keys)

    class ck3:  # noqa: N801
        loc = staticmethod(lambda k: got.get(k))

    new, rep = [], []
    for key, (_grp, ck3c, _p) in LIFTS.items():
        txt = ck3.loc(ck3c)
        if txt:
            new.append((key, txt))
    for grp, ck3key in GROUP_NAME_FROM_CK3.items():
        txt = ck3.loc(ck3key)
        if txt:
            new.append((grp, txt))
    for key, ck3c in RENAME_FROM_CK3.items():
        txt = ck3.loc(ck3c)
        if txt:
            rep.append((key, txt))
    return new, rep


def _loc_text(pairs):
    seen, lines = set(), ["l_english:"]
    for k, v in pairs:
        if k not in seen:
            seen.add(k)
            lines.append(f' {k}:0 "{v}"')
    return "\n".join(lines) + "\n"


def targets():
    new, rep = _loc_pairs()
    return [
        (OUT, build_text(), "cp1252"),
        (LOC, _loc_text(new), "utf-8-sig"),
        (LOC_REPLACE, _loc_text(rep), "utf-8-sig"),
    ]


def write(check=False):
    stale = []
    for path, text, enc in targets():
        old = None
        if os.path.exists(path):
            old = open(path, encoding=enc, errors="replace", newline="").read()
        if old != text:
            stale.append(path)
            if not check:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding=enc, errors="replace", newline="") as f:
                    f.write(text)
    return stale


_done = False


def ensure():
    """Write the file once per process, before anything reads it."""
    global _done
    if not _done:
        _done = True
        write()


def known():
    ensure()
    return set(re.findall(r"(?m)^\t([A-Za-z0-9_]+) = \{", _read(OUT))) - set(NOT_CULTURES)


if __name__ == "__main__":
    check = "--check" in sys.argv
    stale = write(check)
    for p in stale:
        print(("stale: " if check else "wrote ") + os.path.relpath(p, MOD))
    sys.exit(1 if (check and stale) else 0)
