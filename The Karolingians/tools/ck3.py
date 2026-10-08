#!/usr/bin/env python3

import os, re
from functools import lru_cache
from pathlib import Path

from enc import encname
from tagdb import BY_TAG, CTRY_DATE, RULER_TITLES, TITLES

GAME_CK3 = "/mnt/data/SteamLibrary/steamapps/common/Crusader Kings III/game"

DATE = "867.1.1"

HOUSE_NAME_OVERRIDE = {
    "house_abbasid": "dynn_Abbasid",
}


def _date_key(s: str) -> tuple:
    p = [int(x) for x in s.split(".")]
    return tuple(p + [0] * (3 - len(p)))


def _norm(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _blocks(text: str):
    for m in re.finditer(r"^([a-zA-Z_0-9]+)\s*=\s*\{", text, re.M):
        i = m.end() - 1
        d = 0
        while i < len(text):
            if text[i] == "{":
                d += 1
            elif text[i] == "}":
                d -= 1
                if d == 0:
                    break
            i += 1
        yield m.group(1), text[m.end() : i]


def _inner_blocks(body: str):
    for m in re.finditer(r"^[ \t]*([a-zA-Z_0-9.]+)\s*=\s*\{", body, re.M):
        i = m.end() - 1
        d = 0
        while i < len(body):
            if body[i] == "{":
                d += 1
            elif body[i] == "}":
                d -= 1
                if d == 0:
                    break
            i += 1
        yield m.group(1), body[m.end() : i]


@lru_cache(maxsize=1)
def load_titles():
    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "titles").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for tid, body in _blocks(text):
            out.setdefault(tid, []).extend(_inner_blocks(body))
    return out


def holder_at(title, titles):
    return holder_at_exact(title, titles)[0]


def holder_at_exact(title, titles):
    blocks = titles.get(title)
    if not blocks:
        return None, None
    best = None
    at_date = None
    for head, body in blocks:
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)", head)
        if not m:
            continue
        d = f"{m[1]}.{m[2]}.{m[3]}"
        if _date_key(d) > _date_key(DATE):
            continue
        h = re.search(r"holder\s*=\s*(\d+)", body)
        if not h:
            continue
        if _date_key(d) == _date_key(DATE):
            at_date = h.group(1)
        best = (h.group(1), d)
    if at_date is not None:
        return at_date, None
    return best if best else (None, None)


@lru_cache(maxsize=1)
def load_chars():
    out = {}
    for f in sorted((Path(GAME_CK3) / "history" / "characters").glob("*.txt")):
        text = _norm(f.read_text(errors="replace")).lstrip("\ufeff")
        for cid, body in _blocks(text):
            out.setdefault(cid, body)
    return out


@lru_cache(maxsize=1)
def load_dynasties():
    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasties").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"(dynn_\w+)"', body)
            if n:
                out[key] = n.group(1)
    return out


@lru_cache(maxsize=1)
def load_title_colors():
    """{titlename: (r, g, b)} from landed_titles: the title's CK3 map colour.

    CK3 titles carry `color = { r g b }` or `color = hsv{ h s v }`; hsv floats
    are converted back to rgb. Title keys may contain dashes and digits
    (e.g. e_caspian-pontic_steppe), and titles nest, so this walks every
    block whose key looks like a title."""
    from colorsys import hsv_to_rgb

    title = re.compile(r"^[ecbksd]_[a-z0-9_\-]+$")
    block = re.compile(r"^[ \t]*([a-zA-Z0-9_\-.:]+)\s*=\s*\{", re.M)
    color = re.compile(
        r"^[ \t]*color\s*=\s*(hsv\s*)?\{[ \t]*([0-9.]+)[ \t]+([0-9.]+)"
        r"[ \t]+([0-9.]+)[ \t]*\}",
        re.M,
    )
    out: dict = {}

    def walk(body):
        for m in block.finditer(body):
            k = m.group(1)
            if not title.match(k):
                continue
            i = body.index("{", m.start())
            d = 0
            j = i
            while j < len(body):
                if body[j] == "{":
                    d += 1
                elif body[j] == "}":
                    d -= 1
                    if d == 0:
                        break
                j += 1
            sub = body[i + 1 : j]
            cm = color.search(sub)
            if cm and k not in out:
                h, s, v = (float(x) for x in cm.groups()[1:])
                if cm.group(1):
                    r, g, b = (round(x * 255) for x in hsv_to_rgb(h, s, v))
                else:
                    r, g, b = (round(x) for x in (h, s, v))
                out[k] = (r, g, b)
            walk(sub)

    for f in sorted((Path(GAME_CK3) / "common" / "landed_titles").glob("*.txt")):
        walk(_norm(f.read_text(errors="replace")).lstrip("\ufeff"))
    return out


@lru_cache(maxsize=1)
def load_houses():
    out = {}
    for f in sorted((Path(GAME_CK3) / "common" / "dynasty_houses").glob("*.txt")):
        for key, body in _blocks(_norm(f.read_text(errors="replace"))):
            n = re.search(r'name\s*=\s*"?\s*(dynn_\w+)\s*"?', body)
            d = re.search(r"^\s*dynasty\s*=\s*(\w+)", body, re.M)
            name_key = n.group(1) if n else None
            out[key] = (
                HOUSE_NAME_OVERRIDE.get(key, name_key),
                d.group(1) if d else None,
            )
    return out


_LOC_FILES = None

_LOC_RE = re.compile(r'^[ \t]*([\w.\-]+)\s*:\d*\s*"(.*?)"[ \t\r\n]*$', re.M)


def loc(key):
    global _LOC_FILES
    if _LOC_FILES is None:
        _LOC_FILES = {}
        for pat in ("localization/english", "localisation/english"):
            root = Path(GAME_CK3) / pat
            if not root.is_dir():
                continue
            for f in sorted(root.rglob("*.yml")):
                try:
                    t = _norm(f.read_text(errors="replace"))
                except OSError:
                    continue
                for k, v in _LOC_RE.findall(t):

                    _LOC_FILES.setdefault(k, v)
    return _LOC_FILES.get(key)


def resolve_dynasty(body, dyns, houses):
    m = re.search(r"^\s*dynasty\s*=\s*(\w+)", body, re.M)
    if m:
        return loc(dyns.get(m.group(1), "")) or m.group(1)
    h = re.search(r"^\s*dynasty_house\s*=\s*(\w+)", body, re.M)
    if h:
        house = h.group(1)
        name_key, nested = houses.get(house, (None, None))
        name_key = HOUSE_NAME_OVERRIDE.get(house, name_key)
        if name_key:
            return loc(name_key) or name_key
        if nested:
            return loc(dyns.get(nested, "")) or nested
    return None


def resolve(tag, titles, chars, dyns, houses):
    title = TITLES[tag]

    ruler_title = RULER_TITLES.get(tag, title)
    cid, carried = holder_at_exact(ruler_title, titles)
    if cid is None:
        where = (
            f"CK3 has no 867 holder for {tag}'s title {title}"
            if ruler_title == title
            else f"CK3 has no 867 holder for {tag}'s ruler title {ruler_title} "
            f"(bound to {title})"
        )
        return {"error": where}
    body = chars.get(cid)
    if body is None:
        return {"error": f"CK3 has no character {cid} for {tag}"}

    nm = re.search(r'^\s*name\s*=\s*(?:"([^"]*)"|([^\s#"]+))', body, re.M)
    if not nm:
        return {"error": f"character {cid} has no name line"}
    raw = nm.group(1) or nm.group(2)

    name = loc(raw) or raw
    dy = resolve_dynasty(body, dyns, houses)
    return {
        "char": cid,
        "name": name,
        "dynasty": dy,
        "title": title,
        "ruler_title": ruler_title,
        "carried": carried,
        "no_dynasty": not dy,
    }


def land_holders():
    from eu4 import effective, MOD

    out = {}
    for f in sorted((MOD / "history" / "provinces").glob("*.txt")):
        pid = int(f.name.split("-")[0].strip())
        text = f.read_text(encoding="utf-8", errors="surrogateescape")
        owner, _ctrl, _core = effective(text)
        if owner:
            out[owner] = out.get(owner, 0) + 1
    return out


def monarch_block(path):
    text = path.read_text(encoding="cp1252", errors="surrogateescape")
    m = re.search(
        rf"^{re.escape(CTRY_DATE)} = \{{\s*\n\tmonarch = \{{(.*?)^\t\}}",
        text,
        re.M | re.S,
    )
    return text, (m.group(1) if m else None)


def current(body):
    if body is None:
        return (None, None)
    n = re.search(r'name = "([^"]+)"', body)
    d = re.search(r'dynasty = "([^"]+)"', body)
    return (n.group(1) if n else None, d.group(1) if d else None)


def heir_dynasty(text):
    blk = re.search(rf"^{re.escape(CTRY_DATE)} = \{{\n(.*?)^\}}", text, re.M | re.S)
    if not blk:
        return None
    heir = re.search(r"heir = \{(.*?)\n\t\}", blk.group(1), re.S)
    if not heir:
        return None
    d = re.search(r'dynasty = "([^"]+)"', heir.group(1))
    return d.group(1) if d else None


def step_ck3(argv):
    from eu4 import COUNTRY_OUT, VANILLA_CDIR

    fix = "--fix" in argv
    titles, chars = load_titles(), load_chars()
    dyns, houses = load_dynasties(), load_houses()

    bad = []
    unwritten = []

    holders = land_holders()
    vanilla = {
        fn.split(" ")[0] for fn in os.listdir(VANILLA_CDIR) if fn.endswith(".txt")
    }
    kept_vanilla = sorted(t for t in holders if t not in TITLES and t in vanilla)
    unclassified = sorted(t for t in holders if t not in TITLES and t not in vanilla)
    print(f"== {len(holders)} tags own land at the mod start date ==")
    print(f"   CK3-derived (name/dynasty checked): {len(TITLES)}")
    print(f"   vanilla, untouched, ruler kept    : {len(kept_vanilla)}")
    for t in unclassified:
        bad.append(
            f"{t} owns {holders[t]} provinces at the start date but has no "
            f"CK3 title and no vanilla country file"
        )
    if unclassified:
        print(f"   UNCLASSIFIED: {', '.join(unclassified)}")

    for tag in sorted(TITLES):
        got = resolve(tag, titles, chars, dyns, houses)
        path = COUNTRY_OUT / f"{tag}.txt"
        if "error" in got:
            bad.append(f"{tag}: {got['error']}")
            continue
        if not path.exists():

            print(f"  NOTE {tag} {got['title']} / char {got['char']}")
            print(f"        no {path.name}: keeps the vanilla file, nothing to sync")
            if got.get("no_dynasty"):
                print(
                    f"        CK3 867: name={got['name']!r} and NO dynasty - "
                    f"CK3 records neither dynasty nor dynasty_house for this "
                    f"character. Nothing is invented for it: if this tag ever "
                    f"gets a country file, map it to a title whose 867 holder "
                    f"has a dynasty."
                )
            else:
                print(
                    f"        CK3 867: name={got['name']!r} "
                    f"dynasty={got['dynasty']!r}"
                )
            unwritten.append(tag)
            continue
        text, body = monarch_block(path)
        cn, cd = current(body)
        if got.get("no_dynasty"):

            if cd is not None:
                bad.append(
                    f"{tag}: CK3 character {got['char']} ({got['name']}) has "
                    f"neither dynasty nor dynasty_house, but {path.name} "
                    f"declares dynasty={cd!r}. That dynasty is invented - "
                    f"drop it, or map the tag to a CK3 title whose 867 "
                    f"holder has a real one."
                )
                print(f"  FAIL {tag} {got['title']} / char {got['char']}")
                print(f"        file: name={cn!r} dynasty={cd!r}  <- INVENTED")
                print(f"        CK3 : name={got['name']!r} and NO dynasty")
            else:
                print(f"  OK   {tag} {got['title']} / char {got['char']}")
                print(f"        file: name={cn!r} dynasty={cd!r}")
                print(
                    f"        CK3 : name={got['name']!r} and NO dynasty - the file "
                    f"declares none either, which is the correct handling: CK3 "
                    f"records neither dynasty nor dynasty_house, so nothing is "
                    f"invented to cover the gap."
                )
            continue
        hd = heir_dynasty(text)
        heir_bad = (
            hd is not None
            and hd != encname(got["dynasty"])
            and not BY_TAG[tag].no_heir_sync
        )
        ok = (
            cn == encname(got["name"])
            and cd == encname(got["dynasty"])
            and not heir_bad
        )
        mark = "OK " if ok else "DRIFT"
        src = (
            f"<- {got['title']}"
            + (
                f" (ruler from {got['ruler_title']})"
                if got.get("ruler_title", got["title"]) != got["title"]
                else ""
            )
            + (f" (holder carried from {got['carried']})" if got.get("carried") else "")
        )
        print(f"  {mark} {tag} {src} / char {got['char']}")
        print(f"        file: name={cn!r} dynasty={cd!r}")
        print(f"        CK3 : name={got['name']!r} dynasty={got['dynasty']!r}")
        if hd is not None:
            print(
                f"        heir dynasty={hd!r}"
                + ("  <- should match the ruler's" if heir_bad else "")
            )
        if not ok:
            if fix:

                blk = re.search(
                    rf"^{re.escape(CTRY_DATE)} = \{{\n(.*?)^\}}", text, re.M | re.S
                )
                new = blk.group(1)
                if cn is not None:
                    new = re.sub(
                        r'name = "[^"]+"',
                        f'name = "{encname(got["name"])}"',
                        new,
                        count=1,
                    )
                if cd is not None:
                    new = re.sub(
                        r'dynasty = "[^"]+"',
                        f'dynasty = "{encname(got["dynasty"])}"',
                        new,
                        count=1,
                    )
                if heir_bad:
                    heir = re.search(r"heir = \{.*?\n\t\}", new, re.S)
                    nb = re.sub(
                        r'dynasty = "[^"]+"',
                        f'dynasty = "{encname(got["dynasty"])}"',
                        heir.group(0),
                        count=1,
                    )
                    new = new[: heir.start()] + nb + new[heir.end() :]
                text = text[: blk.start(1)] + new + text[blk.end(1) :]
                path.write_text(text, encoding="cp1252", errors="pdx")
                print(
                    f"        fixed -> {encname(got['name'])} / "
                    f"{encname(got['dynasty'])}"
                )
            else:
                if cn != encname(got["name"]) or cd != encname(got["dynasty"]):
                    bad.append(
                        f"{tag}: file has {cn!r}/{cd!r}, CK3 has "
                        f"{encname(got['name'])!r}/{encname(got['dynasty'])!r}"
                    )
                if heir_bad:
                    bad.append(
                        f"{tag}: heir dynasty is {hd!r} but the ruler's is "
                        f"{encname(got['dynasty'])!r}"
                    )

    if bad:
        print("\nFAIL:")
        for b in bad:
            print("  " + b)
        return 1
    checked = len(TITLES) - len(unwritten)
    print(
        f"\nOK: all {len(holders)} start-date land-holders are accounted for; "
        f"{checked} of {len(TITLES)} CK3-mapped rulers match CK3's 867 bookmark"
        + (
            f", {len(unwritten)} unwritten ({', '.join(sorted(unwritten))}) "
            f"keep vanilla's file"
            if unwritten
            else ""
        )
        + (" (rewritten)" if fix else "")
    )
    return 0


_CK3_CACHE: dict = {}


def ck3_ruler(tag):
    if tag not in _CK3_CACHE:
        if tag not in TITLES:
            _CK3_CACHE[tag] = None
            return None
        got = resolve(
            tag,
            load_titles(),
            load_chars(),
            load_dynasties(),
            load_houses(),
        )

        _CK3_CACHE[tag] = None if got.get("error") or not got.get("dynasty") else got
    return _CK3_CACHE[tag]


def ck3_sync(tag, text):
    got = ck3_ruler(tag)
    if got is None:
        return text
    blk = re.search(rf"^{re.escape(CTRY_DATE)} = \{{\n(.*?)^\}}", text, re.M | re.S)
    if not blk:
        return text
    new = re.sub(
        r'name = "[^"]+"', f'name = "{encname(got["name"])}"', blk.group(1), count=1
    )
    new = re.sub(r'dynasty = "[^"]+"', f'dynasty = "{encname(got["dynasty"])}"', new)
    return text[: blk.start(1)] + new + text[blk.end(1) :]


def _eu4_skill(ck3_value):
    if ck3_value is None:
        return 2, None
    return max(1, min(6, round(int(ck3_value) / 3))), int(ck3_value)


def _ck3_dates_and_skills(cid, chars):
    body = chars.get(cid)
    if body is None:
        return None
    birth = death = None

    for date, block in re.findall(r"(\d+\.\d+\.\d+)\s*=\s*\{(.*?)\n\t\}", body, re.S):
        if re.search(r"^\s*birth\s*=", block, re.M):
            birth = date
        if re.search(r"^\s*death\s*=", block, re.M):
            death = date

    def skill(key):
        m = re.search(r"^\s*" + key + r"\s*=\s*(\d+)", body, re.M)
        return m.group(1) if m else None

    adm, _ = _eu4_skill(skill("stewardship"))
    dip, _ = _eu4_skill(skill("diplomacy"))
    mil, _ = _eu4_skill(skill("martial"))
    return birth, death, adm, dip, mil


def _ck3_name(cid, chars, loc):
    m = re.search(r'^\s*name\s*=\s*(?:"([^"]*)"|([^\s#"]+))', chars[cid], re.M)
    if not m:
        return None
    return loc(m.group(1) or m.group(2)) or (m.group(1) or m.group(2))


def ck3_block(tag):
    titles, chars = load_titles(), load_chars()
    dyns, houses = load_dynasties(), load_houses()
    got = resolve(tag, titles, chars, dyns, houses)
    if "error" in got:
        raise SystemExit(f"{tag}: {got['error']}")
    cid = got["char"]
    facts = _ck3_dates_and_skills(cid, chars)
    if facts is None:
        raise SystemExit(f"{tag}: CK3 character {cid} has no readable entry")
    birth, death, adm, dip, mil = facts
    if not birth or not death:
        raise SystemExit(f"{tag}: CK3 character {cid} has no birth or death date")
    name = _ck3_name(cid, chars, loc)
    dynasty = got["dynasty"]

    def person(cid_, claim=None):
        nm = _ck3_name(cid_, chars, loc)
        b, d, a, dp, ml = _ck3_dates_and_skills(cid_, chars)
        dy = resolve_dynasty(chars[cid_], dyns, houses)
        out = [f'\t\tname = "{encname(nm)}"']
        if claim is not None:
            out.append(f'\t\tmonarch_name = "{encname(nm)}"')
        if dy:
            out.append(f'\t\tdynasty = "{encname(dy)}"')
        for label, d_ in (("birth_date", b), ("death_date", d)):
            if not d_:
                raise SystemExit(f"{tag}: CK3 character {cid_} has no {label}")
            y, m, dd = (int(x) for x in d_.split("."))
            out.append(f"\t\t{label} = {y}.{m}.{dd}")
        if claim is not None:
            out.append(f"\t\tclaim = {claim}")
        out += [f"\t\tadm = {a}", f"\t\tdip = {dp}", f"\t\tmil = {ml}"]
        return "\n".join(out)

    lines = [f"{CTRY_DATE} = {{", "\tmonarch = {", person(cid), "\t}"]

    kids = [
        k for k, b in chars.items() if re.search(rf"^\s*father\s*=\s*{cid}\b", b, re.M)
    ]
    kids.sort(key=lambda k: _ck3_dates_and_skills(k, chars)[0] or "9999.9.9")
    if kids:
        lines += ["\their = {", person(kids[0], claim=90), "\t}"]
    lines += ["}", ""]
    return "\n".join(lines)
