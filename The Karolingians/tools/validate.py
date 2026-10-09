#!/usr/bin/env python3

import json, os, re, sys
from collections import Counter
from build import parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
MOD = str(HERE.parent)
PDIR = os.path.join(MOD, "history", "provinces")
COUNTRY_OUT = os.path.join(MOD, "history", "countries")
from build import ALL_TAGS  # noqa: E402

from build import TAGS as _REALMS  # noqa: E402

from enc import encname  # noqa: E402

TAGS = sorted(t.tag for t in _REALMS if t.ck3_title)

sys.path.insert(0, str(HERE))
from build import (
    PROVINCES,
    ALL_TAGS,
    CAPITAL,
    empire_core,
    karling_realms,
)

# this mod's 867 culture/religion expectations, checked against the files
# the build writes
CULTURE_GONE_867 = {"turkish": "greek", "pontic_greek": "greek"}
CONQUERED_BY_THE_ARABS = {327, 332, 2303, 4298, 4310}
MUSLIM_RELIGIONS_867 = ("sunni", "shiite")
from build import effective  # noqa: E402

CAPS = CAPITAL

from build import RANK, KEPT_REALMS  # noqa: E402

from build import BY_TAG  # noqa: E402

from tagdb import CTRY_DATE, DIPLOMACY  # noqa: E402

fail = []


def _s(m):
    return m.encode("ascii", "replace").decode("ascii")


def note(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + _s(msg))
    if not ok:
        fail.append(msg)


def warn(msg):
    print("  WARN " + _s(msg))




def run() -> int:
    fail.clear()
    print("== mod skeleton ==")
    for p in [
        "/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/The Karolingians.mod",
        f"{MOD}/descriptor.mod",
        f"{MOD}/localisation/replace/countries_l_english.yml",
    ]:
        note(os.path.exists(p), f"exists {os.path.relpath(p, MOD)}")

    print("\n== country definitions ==")
    GH = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV/history/countries"
    base = {fn.split(" ")[0] for fn in os.listdir(GH) if fn.endswith(".txt")}
    note("LUS" not in base, "no invented LUS tag is in use (base game Lusatia is SOR)")
    mine = set()
    MC = os.path.join(MOD, "common", "countries")
    if os.path.isdir(MC):
        for fn in os.listdir(MC):
            if fn.endswith(".txt"):
                p = os.path.join(MC, fn)
                t = open(p, encoding="utf-8", errors="replace").read()
                note(
                    t.count("{") == t.count("}"),
                    f"braces balanced in common/countries/{fn}",
                )
                mine.add(fn.split(" ")[0])
    CT = os.path.join(MOD, "common", "country_tags")
    if os.path.isdir(CT):
        for fn in os.listdir(CT):
            if not fn.endswith(".txt"):
                continue
            text = open(os.path.join(CT, fn), encoding="utf-8", errors="replace").read()
            for m in re.finditer(r'^([A-Z]{3})\s*=\s*"countries/([^"]+)"', text, re.M):
                tag, cfile = m.group(1), m.group(2)
                note(
                    os.path.exists(os.path.join(MC, cfile)),
                    f"{tag} registry entry {fn} -> countries/{cfile} resolves",
                )
                mine.add(tag)
    for t in TAGS:
        where = (
            "base game"
            if t in base
            else ("mod common/countries" if t in mine else "NOWHERE")
        )
        note(t in base or t in mine, f"{t} country definition resolvable ({where})")

    from ck3 import load_title_colors
    from eu4 import load_vanilla_countries

    vcountries = load_vanilla_countries()
    ck3_colors = load_title_colors()
    for t in _REALMS:
        if not t.ck3_title:
            continue
        vbase = vcountries.get(t.tag)
        if vbase is None:
            p = os.path.join(MC, t.country_file or f"{t.name}.txt")
        else:
            p = os.path.join(MC, vbase[0])
        want = ck3_colors.get(t.ck3_title)
        body = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^color = \{?\s*(\d+)\s+(\d+)\s+(\d+)", body)
        got = tuple(int(x) for x in m.groups()) if m else None
        if want is None:
            note(
                got == t.color,
                f"{t.tag} colour stays {t.color} (CK3 has no {t.ck3_title} colour)",
            )
        else:
            note(
                got == want,
                f"{t.tag} colour {got} lifted from CK3 {t.ck3_title} {want}",
            )
    for t in TAGS:
        if t not in base and t not in mine:
            continue
        g = [fn for fn in os.listdir(GH) if fn.startswith(t + " - ")]
        if g:
            body = open(
                os.path.join(GH, g[0]), encoding="utf-8", errors="replace"
            ).read()
            note(
                re.search(r"^\s*capital\s*=\s*(\d+)", body, re.M) is not None,
                f"{t} vanilla history declares a capital",
            )

    print("\n== brace balance ==")
    n = 0
    bad = []
    for d in (PDIR, COUNTRY_OUT):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".txt"):
                continue
            n += 1
            t = re.sub(
                r"#.*",
                "",
                open(
                    os.path.join(d, fn), encoding="utf-8", errors="surrogateescape"
                ).read(),
            )
            if t.count("{") != t.count("}"):
                bad.append(f"{fn} {t.count('{')}/{t.count('}')}")
    note(not bad, f"balanced braces in all {n} files")
    for b in bad[:10]:
        print("        " + b)

    print("\n== country files ==")


    def country_path(t: str) -> str:
        for fn in os.listdir(COUNTRY_OUT):
            if fn.startswith(f"{t} - ") and fn.endswith(".txt"):
                return os.path.join(COUNTRY_OUT, fn)
        return os.path.join(COUNTRY_OUT, f"{t}.txt")


    for t in TAGS:
        txt = open(
            country_path(t),
            encoding="utf-8",
            errors="surrogateescape",
        ).read()
        note(f"capital = {CAPS[t]}" in txt, f"{t} capital = {CAPS[t]}")
        note("monarch = {" in txt, f"{t} has an 867 monarch")

    print("\n== every kept realm has a deliberate rank ==")
    unwritten = []
    for t in sorted(KEPT_REALMS):
        path = country_path(t)
        if not os.path.exists(path):
            unwritten.append(t)
            continue
        txt = open(path, encoding="utf-8", errors="surrogateescape").read()
        want = RANK[t]

        top = re.search(r"^government_rank\s*=\s*(\d+)", txt, re.M)
        got = int(top.group(1)) if top else None
        note(
            got == want,
            f"{t} government_rank = {want}"
            + ("" if got is None else f" (top-level, found {got})")
            + (" - ABSENT, so EU4 defaults it to a duchy" if top is None else ""),
        )

    note(
        not unwritten,
        f"every kept realm has a country file ({len(KEPT_REALMS)} realms)",
    )
    for t in unwritten:
        print(f"        {t}: holds land, has a rank, but no country file")

    print("\n== province ownership ==")
    files = {}
    for fn in sorted(os.listdir(PDIR)):
        files[int(re.match(r"^(\d+)", fn).group(1))] = os.path.join(PDIR, fn)
    note(
        len(files) == len(os.listdir(PDIR)),
        f"no duplicate province files ({len(files)} unique)",
    )

    own, badown, multicore = Counter(), [], []
    cores_new = {}
    for pid, path in files.items():
        s, c0, ca = parse(path)
        o = s.get("owner")
        ctrl = s.get("controller")
        if o is None and ctrl is None:

            if int(pid) not in PROVINCES:
                pass  # a vanilla sea tile (no owner by design)
            else:
                text = open(path, encoding="utf-8", errors="surrogateescape").read()
                o, ctrl, _ = effective(text)
                if o is None:
                    badown.append(f"{pid} has no owner at the start date")
                    continue
        own[o] += 1

        if o is None and ctrl is None:
            pass
        elif ctrl != o:
            badown.append(f"{pid} controller={ctrl} owner={o}")
        for c in c0:
            cores_new.setdefault(c, []).append(pid)
        hit = [t for t in TAGS if t in c0]

        if len(hit) > 1 and o not in TAGS:
            multicore.append(f"{pid}: {hit} (owner {o})")

    note(not badown, f"every province has owner == controller ({len(badown)} problems)")
    for b in badown[:8]:
        print("        " + b)
    note(not multicore, f"no province cored by 2+ new tags ({len(multicore)})")
    for m in multicore[:8]:
        print("        " + m)

    print("\n== realm sizes ==")
    for t in TAGS:
        note(own[t] > 0, f"{t} owns {own[t]} provinces")
    note(own["HLR"] == 0, f"HLR owns 0 provinces (has {own['HLR']})")
    print(f"        new total = {sum(own[t] for t in TAGS)}")

    print("\n== capitals inside own realm ==")
    for t in TAGS:
        s, _, _ = parse(files[CAPS[t]])
        note(
            s.get("owner") == t,
            f"{t} capital {CAPS[t]} ({s.get('capital')}) owned by {s.get('owner')}",
        )

    print("\n== new core on every owned province ==")
    for t in TAGS:
        owned = [pid for pid, p in files.items() if parse(p)[0].get("owner") == t]
        missing = [pid for pid in owned if t not in parse(files[pid])[1]]
        note(
            not missing, f"{t}: core on all {len(owned)} owned ({len(missing)} missing)"
        )

    print()
    print('== no dead cores ==')
    alive = set(ALL_TAGS) | {'HLR'}
    dead = []
    for pid, path in files.items():
        for c in parse(path)[1]:
            if c not in alive:
                dead.append(f'{pid}: core for {c}')
    note(not dead, f'every core belongs to a living tag ({len(dead)} dead)')
    for d in dead[:10]:
        print('        ' + d)

    print("\n== untouched neighbours intact ==")

    reassigned = {pid for pid, p in files.items() if parse(p)[0].get("owner") in TAGS}
    for t in [
        "NAP",
        "SIC",
        "SARD",
        "DAN",
        "SWE",
        "NOR",
        "ENG",
        "CAS",
        "POR",
        "MKL",
        "POM",
    ]:
        owned = [pid for pid in reassigned if parse(files[pid])[0].get("owner") == t]
        note(not owned, f"{t} owns none of the {len(reassigned)} reassigned provinces")

    print("\n== hre decision matches the empire's land ==")

    expected = set(empire_core())
    trig = open(
        os.path.join(MOD, "common", "scripted_triggers", "KarolingianFormations.txt"),
        encoding="utf-8",
        errors="replace",
    ).read()
    blk = re.search(
        r"kar_form_hre_provinces_trigger = \{(.*?)\n\}",
        trig,
        re.S,
    )
    body = blk.group(1) if blk else ""
    cdata = json.load(open(str(CACHE / "provdata.json")))
    required = {int(x) for x in re.findall(r"province_id = (\d+)", body)}
    for a in re.findall(r"^\s*area = (\w+)", body, re.M):
        required |= {int(x) for x in cdata["areas"].get(a, ())}
    note(
        required == expected,
        f"trigger covers exactly the {len(expected)} imperial provinces",
    )
    if required != expected:
        print(f"        only in trigger : {sorted(required - expected)}")
        print(f"        only in the core : {sorted(expected - required)}")
    note(
        not (required - expected),
        "no province outside the 867 empire is required to restore it",
    )
    hredec = open(
        os.path.join(MOD, "decisions", "KarolingianHRE.txt"),
        encoding="utf-8",
        errors="replace",
    ).read()
    val = re.search(r"num_of_owned_provinces_with = \{.*?value = (\d+)", hredec, re.S)
    note(
        bool(val) and int(val.group(1)) == len(expected),
        f"decision demands owning {len(expected)} provinces (value)",
    )
    note(
        "dynasty = " in hredec,
        "potential gates on the Karling dynasty",
    )
    hreloc = open(
        os.path.join(MOD, "localisation", "karolingian_hre_l_english.yml"),
        encoding="utf-8",
        errors="replace",
    ).read()
    note(
        "kar_form_hre_title:0" in hreloc,
        "decision name keyed kar_form_hre_title (EU4 reads <key>_title)",
    )

    print("\n== starting vassals ==")
    dip = os.path.join(MOD, "history", "diplomacy", "karolingian_vassals.txt")
    raw_dip = open(dip, encoding="cp1252", errors="replace").read()
    found = list(
        zip(
            re.findall(r"first\s*=\s*([A-Z]{3})", raw_dip),
            re.findall(r"second\s*=\s*([A-Z]{3})", raw_dip),
        )
    )
    expected_dip = [(d.liege, d.subject) for d in DIPLOMACY]
    note(found == expected_dip, "diplomacy file lists exactly the starting vassals")
    if found != expected_dip:
        print(f"        in file    : {found}")
        print(f"        in tagdb   : {expected_dip}")

    print()
    print("== vanilla tag reuse is deliberate ==")
    VANILLA_REUSE = frozenset(
        "ADU ARB ARM ASU BAV BOH BRI BUL BYZ CRO CRT DAL EGY EST FRA "
        "GER GMA HSA ITA KIE KRA KUR LIT LOT LVA MON NAV NOV PAP PLT PRU RUG SAR "
        "SIL SOR SRV STE VEN VOL WOL".split()
    )
    vtags = set()
    vd = os.path.join(GAME, "common", "country_tags")
    for fn in os.listdir(vd):
        if not fn.endswith(".txt"):
            continue
        vtags.update(
            re.findall(
                r'^([A-Z]{3})\s*=\s*"countries/',
                open(os.path.join(vd, fn), encoding="cp1252", errors="replace").read(),
                re.M,
            )
        )
    clash = [t for t in ALL_TAGS if t in vtags and t not in VANILLA_REUSE]
    note(not clash, f"no accidental vanilla tag reuse ({', '.join(clash) or 'none'})")

    print("\n== custom tags registered ==")

    cdata = json.load(open(str(CACHE / "provdata.json")))
    for t in _REALMS:
        if t.tag in vcountries:
            continue
        flag = os.path.join(MOD, "gfx", "flags", f"{t.tag}.tga")
        if not os.path.exists(flag):
            warn(f"{t.tag} has no flag yet")
        if not t.forms:
            continue
        basin = {int(pid) for a in t.form_areas for pid in cdata["areas"].get(a, ())}
        trig = open(
            os.path.join(
                MOD, "common", "scripted_triggers", "KarolingianFormations.txt"
            ),
            encoding="utf-8",
            errors="replace",
        ).read()
        blk = re.search(
            re.escape(t.decision) + r"_provinces_trigger = \{(.*?)\n\}",
            trig,
            re.S,
        )
        body = blk.group(1) if blk else ""
        required = {int(x) for x in re.findall(r"province_id = (\d+)", body)}
        for a in re.findall(r"^\s*area = (\w+)", body, re.M):
            required |= {int(x) for x in cdata["areas"].get(a, ())}
        note(
            required == basin,
            f"{t.decision} requires exactly the {len(basin)} Carpathian Basin "
            f"provinces",
        )
        if required != basin:
            print(f"        only in decision : {sorted(required - basin)}")
            print(f"        only in the land : {sorted(basin - required)}")
        dec = open(
            os.path.join(MOD, "decisions", f"Form{t.forms}.txt"),
            encoding="utf-8",
            errors="replace",
        ).read()
        note(
            f"change_tag = {t.forms}" in dec,
            f"{t.decision} changes the tag to {t.forms}",
        )
        for key in t.suppress:
            pat = re.escape(key) + r"\s*=\s*\{\s*potential\s*=\s*\{\s*always\s*=\s*no"
            note(
                bool(re.search(pat, dec)),
                f"vanilla {key} decision suppressed with always = no",
            )
        loc = open(
            os.path.join(MOD, "localisation", "magyars_l_english.yml"),
            encoding="utf-8",
            errors="replace",
        ).read()
        said = re.search(r"hold all (\d+) provinces", loc)
        note(bool(said), f"{t.decision} description quotes a province count")
        if said:
            note(
                int(said.group(1)) == len(basin),
                f"description says {said.group(1)}, basin has {len(basin)}",
            )

    print("\n== every realm holds its own capital ==")

    prov_owner = {}
    for pid, path in files.items():
        prov_owner[pid] = parse(path)[0].get("owner")

    _bp = json.load(open(str(CACHE / "provdata.json")))["provs"]

    def holds(tag):
        held = {pid for pid, o in prov_owner.items() if o == tag}
        for pid, pr in _bp.items():
            pid = int(pid)
            if (
                pr.get("owner_1444", pr.get("owner")) == tag
                and prov_owner.get(pid, tag) == tag
            ):
                held.add(pid)
        return held

    def vanilla_capital(tag):
        for fn in os.listdir(GH):
            if fn.startswith(tag + " - ") and fn.endswith(".txt"):
                m = re.search(
                    r"^\s*capital\s*=\s*(\d+)",
                    open(
                        os.path.join(GH, fn), encoding="utf-8", errors="replace"
                    ).read(),
                    re.M,
                )
                return int(m.group(1)) if m else None
        return None

    for t in ALL_TAGS:
        cap = CAPS.get(t) or vanilla_capital(t)
        held = holds(t)
        if cap is None:
            note(not held, f"{t} owns nothing and declares no capital")
            continue
        src = "mod" if t in CAPS else "vanilla"
        note(
            cap in held,
            f"{t} holds its {src} capital {cap} "
            f"({len(held)} province{'s' if len(held) != 1 else ''})",
        )

    print("\n== Tag.capital agrees with the country file ==")
    for t in ALL_TAGS:
        spec = BY_TAG.get(t)
        if spec is None or spec.capital is None:
            continue
        cp = country_path(t)
        if not os.path.exists(cp):
            continue
        got = re.search(
            r"^\s*capital\s*=\s*(\d+)",
            open(cp, encoding="utf-8", errors="replace").read(),
            re.M,
        )
        note(
            got is not None and int(got.group(1)) == spec.capital,
            f"{t} Tag.capital {spec.capital} matches its file"
            + (
                f" ({got.group(1)})"
                if got and int(got.group(1)) != spec.capital
                else ""
            ),
        )

    print("\n== 867 rulers ==")

    sys.path.insert(0, str(HERE))
    try:
        import build as _b

        _dyn = _b.load_dynasties()
        _chars = _b.load_chars()
        _houses = _b.load_houses()
        _titles = _b.load_titles()
    except (ImportError, OSError) as exc:
        _b = None
        print(f"  SKIP CK3 name/dynasty cross-check ({type(exc).__name__}: {exc})")
        print("        build.py needs a CK3 install to read CK3's rulers.")

    if _b is not None:
        _holders = _b.land_holders()
        _vanilla = {
            fn.split(" ")[0]
            for fn in os.listdir(_b.VANILLA_CDIR)
            if fn.endswith(".txt")
        }

        _ck3 = {t for t in _holders if t in _b.TITLES}
        _rest = {t for t in _holders if t not in _b.TITLES}
        _unclassified = sorted(t for t in _rest if t not in _vanilla)

        _sneaky = sorted(t for t in _rest if (s := BY_TAG.get(t)) is not None)
        for t in _unclassified:
            note(
                False,
                f"{t} owns {_holders[t]} provinces at the start date but has "
                f"no CK3 title and no vanilla country file",
            )
        for t in _sneaky:
            note(
                False,
                f"{t} owns {_holders[t]} provinces and this mod writes it a "
                f"ranked country file, but it is not CK3-derived; classify it "
                f"rather than letting 'vanilla and untouched' cover for it",
            )

        print(
            f"        {len(_ck3)} CK3-derived + {len(_rest)} vanilla and "
            f"untouched = {len(_holders)} holders"
        )

        for t in sorted(_b.TITLES):
            want = _b.resolve(t, _titles, _chars, _dyn, _houses)
            if "error" in want:
                note(False, f"{t} CK3 lookup failed: {want['error']}")
                continue
            cp = country_path(t)
            if not os.path.exists(cp):

                print(
                    f"  SKIP {t} has no mod country file; keeps vanilla's ruler "
                    f"(CK3 {t} would be {want['name']} / {want['dynasty']})"
                )
                continue
            body = open(cp, encoding="cp1252", errors="surrogateescape").read()
            blk = re.search(
                rf"^{re.escape(CTRY_DATE)} = \{{\s*\n\tmonarch = \{{(.*?)^\t\}}",
                body,
                re.M | re.S,
            )
            if not blk:
                note(False, f"{t} has an 867 monarch")
                continue
            got_n, got_d = _b.current(blk.group(1))
            note(
                got_n == encname(want["name"]) and got_d == encname(want["dynasty"]),
                f"{t} ruler name/dynasty matches CK3 867 "
                f"({encname(want['name'])} / {encname(want['dynasty'])})",
            )
        print("        run `python3 tools/build.py --fix` to resync")

    START_DT = (867, 1, 1)
    for t in TAGS:
        p = country_path(t)
        if not os.path.exists(p):
            note(False, f"{t} has a history file")
            continue
        body = open(p, encoding="cp1252", errors="surrogateescape").read()
        blk = re.search(
            rf"^{re.escape(CTRY_DATE)} = \{{\s*\n\tmonarch = \{{(.*?)^\t\}}",
            body,
            re.M | re.S,
        )
        if not blk:
            note(False, f"{t} has an 867 monarch")
            continue
        m = blk.group(1)
        nm = re.search(r'name = "([^"]+)"', m)
        bd = re.search(r"birth_date = (\d+)\.(\d+)\.(\d+)", m)
        if not (nm and bd):
            note(False, f"{t} monarch has a name and birth_date")
            continue
        y, mo, d = (int(x) for x in bd.groups())

        age = START_DT[0] - y - ((START_DT[1], START_DT[2]) < (mo, d))
        regent = "regent = yes" in m
        note(
            age >= 15 or regent,
            f"{t} ruled by {nm.group(1)}, {age} in 867"
            + (" (regent)" if regent else ""),
        )
        print(
            f"        {t} {nm.group(1):14} born {y} "
            f"{'-> age %d at the start date' % age}{', flagged regent' if regent else ''}"
        )

    LOC = os.path.join(MOD, "localisation")
    print("\n== localisation files load ==")
    for root, _dirs, files in os.walk(LOC):
        for fn in sorted(files):
            if not fn.endswith("_l_english.yml"):
                continue
            raw = open(os.path.join(root, fn), "rb").read(3)
            rel = os.path.relpath(os.path.join(root, fn), MOD)
            note(raw == b"\xef\xbb\xbf", f"{rel} starts with a UTF-8 BOM")

    print("\n== no unrenderable z-carons ==")
    bad_glyph = []
    for root, _dirs, files in os.walk(LOC):
        for fn in sorted(files):
            if not fn.endswith("_l_english.yml"):
                continue
            for ln in open(os.path.join(root, fn), encoding="utf-8-sig").read().splitlines():
                if '"' not in ln:
                    continue
                val = ln.split('"')[1]
                if "ž" in val or "Ž" in val:
                    bad_glyph.append(f"{fn}: {val.strip()!r} (renders as ? in game)")
    note(not bad_glyph, f"no ž glyphs ({len(bad_glyph)} bad)")
    for b in bad_glyph[:8]:
        print("        " + b)

    print("\n== Karling dynasty, lifted from CK3 ==")
    dynasty, ktags = karling_realms()
    for t in ktags:
        p = country_path(t)
        body = open(p, encoding="cp1252", errors="surrogateescape").read()
        blk = re.search(rf"^{re.escape(CTRY_DATE)} = \{{.*?^\}}", body, re.M | re.S)
        ds = re.findall(r'dynasty = "([^"]+)"', blk.group(0)) if blk else []
        note(
            bool(ds) and set(ds) == {dynasty},
            f"{t} 867 ruler and heir carry the {dynasty} dynasty",
        )
    dec = open(
        os.path.join(MOD, "decisions", "KarolingianHRE.txt"),
        encoding="utf-8",
        errors="replace",
    ).read()
    gates = re.findall(r'dynasty = "([^"]+)"', dec)
    note(
        gates == [dynasty],
        f"the decision gates on dynasty {dynasty} (only a Karling can restore the "
        f"empire; if the Karlings die out, no one can)",
    )

    for fn in sorted(os.listdir(COUNTRY_OUT)):
        if fn == "HLR - Holy Roman Empire.txt":
            continue  # deliberately neutralized (formed in-game, no OTL history)
        if fn.endswith(".txt") and os.path.getsize(os.path.join(COUNTRY_OUT, fn)) < 200:
            note(
                False,
                f"{fn} is suspiciously small "
                f"({os.path.getsize(os.path.join(COUNTRY_OUT, fn))} bytes) "
                f"- generator probably crashed mid-write",
            )

    gone = set(CULTURE_GONE_867)
    stale_culture, stale_religion = [], []
    for fn in sorted(os.listdir(PDIR)):
        if not fn.endswith(".txt"):
            continue

        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        pid = int(m.group(1))
        text = open(
            os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
        ).read()
        m = re.search(r"^\s*culture\s*=\s*(\w+)", text, re.M)
        culture = m.group(1) if m else None
        if culture in gone:
            stale_culture.append(f"{pid} {fn} ({culture})")
        if culture == "greek" and pid not in CONQUERED_BY_THE_ARABS:
            for rel in re.findall(r"^\s*religion\s*=\s*(\w+)", text, re.M):
                if rel in MUSLIM_RELIGIONS_867:
                    stale_religion.append(f"{pid} {fn} ({rel})")
    note(
        not stale_culture,
        "no mod-written province keeps a culture that postdates 867"
        + ("" if not stale_culture else f": {', '.join(stale_culture)}"),
    )
    note(
        not stale_religion,
        "every Greek province outside the Arab conquest is orthodox"
        + ("" if not stale_religion else f": {', '.join(stale_religion)}"),
    )

    print("\n" + ("ALL CHECKS PASSED" if not fail else f"{len(fail)} FAILURES"))

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(run())
