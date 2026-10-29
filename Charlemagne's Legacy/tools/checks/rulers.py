#!/usr/bin/env python3
"""867 rulers and dynasties compared with CK3's."""

import os
import re
import sys
from checks.report import note, warn
from checks.context import BY_FORMABLE, BY_TAG, CONQUERED_BY_THE_ARABS, COUNTRY_OUT, CTRY_DATE, HERE, MOD, MUSLIM_RELIGIONS_867, PDIR, TAGS, country_path, encname, karling_realms
from steps.layout import VANILLA_CDIR
from tagdb import TITLES


def check_867_rulers() -> None:
    """867 rulers."""
    print("\n== 867 rulers ==")

    sys.path.insert(0, str(HERE))
    try:
        import ck3 as _b

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
            for fn in os.listdir(VANILLA_CDIR)
            if fn.endswith(".txt")
        }

        _ck3 = {t for t in _holders if t in TITLES}
        _rest = {t for t in _holders if t not in TITLES}
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

        for t in sorted(TITLES):
            want = _b.resolve(t, _titles, _chars, _dyn, _houses)
            if "error" in want:
                note(False, f"{t} CK3 lookup failed: {want['error']}")
                continue
            cp = country_path(t)
            if not os.path.exists(cp):

                print(
                    f"  SKIP {t} has no mod country file; keeps vanilla's ruler "
                    f"(CK3 {t} would be {want['display']} / {want['dynasty']})"
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
                got_n == encname(want["display"]) and got_d == encname(want["dynasty"]),
                f"{t} ruler name/dynasty matches CK3 867 "
                f"({encname(want['display'])} / {encname(want['dynasty'])})",
            )
            import ck3
            want_female = ck3._is_female(want["char"], _chars)
            got_female = re.search(r"^\s*female\s*=\s*yes", blk.group(1), re.M) is not None
            note(
                want_female == got_female,
                f"{t} ruler gender matches CK3 867 "
                f"({'female' if want_female else 'male'})",
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
        if age < 15 and not regent:
            # CK3 has child rulers (a ward of 11 holding a county); EU4 opens a regency council for a minor
            warn(f"{t} is ruled by {nm.group(1)}, aged {age} in 867: the game gives the realm a regency")
        else:
            note(True, f"{t} ruled by {nm.group(1)}, {age} in 867" + (" (regent)" if regent else ""))
        print(
            f"        {t} {nm.group(1):14} born {y} "
            f"{'-> age %d at the start date' % age}{', flagged regent' if regent else ''}"
        )


def karling_dynasty_lifted_from_ck3() -> None:
    """Karling dynasty, lifted from CK3."""
    print("\n== Karling dynasty, lifted from CK3 ==")
    dynasty, ktags = karling_realms()
    for t in ktags:
        p = country_path(t)
        body = open(p, encoding="cp1252", errors="surrogateescape").read()
        blk = re.search(rf"^{re.escape(CTRY_DATE)} = \{{.*?^\}}", body, re.M | re.S)
        ds = re.findall(r'dynasty = "([^"]+)"', blk.group(0)) if blk else []
        note(
            bool(ds) and ds[0] == dynasty,
            f"{t} 867 ruler carries the {dynasty} dynasty",
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
    note(
        BY_FORMABLE["HLR"].dynasty == dynasty,
        "the HLR formable records the same dynasty",
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

    stale_religion = []
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
        if culture == "greek" and pid not in CONQUERED_BY_THE_ARABS:
            for rel in re.findall(r"^\s*religion\s*=\s*(\w+)", text, re.M):
                if rel in MUSLIM_RELIGIONS_867:
                    stale_religion.append(f"{pid} {fn} ({rel})")
    note(
        not stale_religion,
        "every Greek province outside the Arab conquest is orthodox"
        + ("" if not stale_religion else f": {', '.join(stale_religion)}"),
    )


def run() -> None:
    check_867_rulers()
    karling_dynasty_lifted_from_ck3()
