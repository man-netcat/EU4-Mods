#!/usr/bin/env python3
"""Validate The Karolingians against vanilla."""
import json, os, re, sys
from collections import Counter
from build import parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

GAME = "/mnt/data/SteamLibrary/steamapps/common/Europa Universalis IV"
MOD = str(HERE.parent)
VDIR = os.path.join(GAME, "history", "provinces")
PDIR = os.path.join(MOD, "history", "provinces")
COUNTRY_OUT = os.path.join(MOD, "history", "countries")
from build import ALL_TAGS  # noqa: E402
# The realms this mod writes a country file for. Derived from
# gen_countries' own per-tag ruler data rather than kept as a second
# list here: the capital/rank/core checks below only mean anything for a
# tag the mod actually authors, and a hand-kept copy of that set is a
# duplicate waiting to drift.
from build import RULERS as _RULERS  # noqa: E402
TAGS = sorted(_RULERS)
# Vanilla tags handed provinces but never generated here. Imported rather than
# re-listed: a private copy of this list silently went stale twice, letting CRT
# and then HUN escape the ownership and empire-frontier checks.
sys.path.insert(0, str(HERE))
from build import (BALATON_RESERVED, TAG_RENAMES,  # noqa: E402
                   ALL_TAGS, CAPITAL, empire_core,
                   CULTURE_GONE_867, CONQUERED_BY_THE_ARABS,
                   MUSLIM_RELIGIONS_867)
from build import effective  # noqa: E402
# Was a second hand-copied copy of gen_provinces.CAPITAL, which is the same class of
# bug as the deleted cache/alloc.json: two files holding one fact, with nothing
# checking they agreed. Now imported from the generator that writes the files.
CAPS = CAPITAL
# The five Carolingian kingdoms are peers; Lusatia is a minor principality.
# Was a hand-copied rank table, and it had already drifted from the files it was
# meant to describe: it claimed FRA was rank 2 while FRA is vanilla's rank 3, and
# it covered only the six generated realms, so the eight realms that have no rank
# at all passed unnoticed. gen_countries.RANK is now the one table, each entry
# argued from its own 867 standing.
from build import RANK, KEPT_REALMS, DEFERRED_REALMS  # noqa: E402
fail = []


def _s(m):
    return m.encode("ascii","replace").decode("ascii")


def note(ok, msg):
    print(("  OK   " if ok else "  FAIL ") + _s(msg))
    if not ok:
        fail.append(msg)


def vfile(pid):
    for f in os.listdir(VDIR):
        m = re.match(r"^(\d+)", f)
        if m and int(m.group(1)) == pid:
            return os.path.join(VDIR, f)
    return None



def run() -> int:
    """Run every check. Returns 0 only when the mod is consistent."""
    fail.clear()
    print("== mod skeleton ==")
    for p in ["/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/The Karolingians.mod",
              f"{MOD}/descriptor.mod",
              f"{MOD}/localisation/replace/countries_l_english.yml",
              f"{MOD}/localisation/replace/emperor_map_l_english.yml",
              f"{MOD}/localisation/replace/areas_regions_l_english.yml"]:
        note(os.path.exists(p), f"exists {os.path.relpath(p, MOD)}")

    # The engine only ever creates a tag it can resolve. A tag it cannot resolve
    # never exists, so every province naming it as owner resolves to no owner and
    # renders as uncolonised land - which is what a made-up "LUS" tag did here. The
    # base game already ships a Lusatia, under the tag SOR, so the mod reuses it.
    # This block fails loudly if a tag is ever invented again. Vanilla tags are
    # identified by the "TAG - Name.txt" filenames in history/countries;
    # common/countries files carry no tag key at all.
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
                note(t.count("{") == t.count("}"), f"braces balanced in common/countries/{fn}")
                mine.add(fn.split(" ")[0])
    for t in TAGS:
        where = "base game" if t in base else ("mod common/countries" if t in mine else "NOWHERE")
        note(t in base or t in mine, f"{t} country definition resolvable ({where})")
    for t in TAGS:
        if t not in base and t not in mine:
            continue
        g = [fn for fn in os.listdir(GH) if fn.startswith(t + " - ")]
        if g:
            body = open(os.path.join(GH, g[0]), encoding="utf-8", errors="replace").read()
            note(re.search(r"^\s*capital\s*=\s*(\d+)", body, re.M) is not None,
                 f"{t} vanilla history declares a capital")

    print("\n== brace balance ==")
    n = 0
    bad = []
    for d in (PDIR, COUNTRY_OUT):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".txt"):
                continue
            n += 1
            t = re.sub(r"#.*", "", open(os.path.join(d, fn), encoding="utf-8",
                                        errors="surrogateescape").read())
            if t.count("{") != t.count("}"):
                bad.append(f"{fn} {t.count('{')}/{t.count('}')}")
    note(not bad, f"balanced braces in all {n} files")
    for b in bad[:10]:
        print("        " + b)

    print("\n== country files ==")
    for t in TAGS:
        txt = open(os.path.join(COUNTRY_OUT, f"{t}.txt"), encoding="utf-8",
                   errors="surrogateescape").read()
        note(f"capital = {CAPS[t]}" in txt, f"{t} capital = {CAPS[t]}")
        note("monarch = {" in txt, f"{t} has a 1444 monarch")

    # Every kept realm, not just the generated ones. A realm with land and no
    # government_rank of its own silently inherits EU4's default of 1, which is how
    # realms as large as the Tulunids came to sit level with Silesia - an omission
    # that reads exactly like a decision in the finished game.
    print("\n== every kept realm has a deliberate rank ==")
    unwritten = []
    for t in sorted(KEPT_REALMS):
        path = os.path.join(COUNTRY_OUT, f"{t}.txt")
        if not os.path.exists(path):
            unwritten.append(t)
            continue
        txt = open(path, encoding="utf-8", errors="surrogateescape").read()
        want = RANK[t]
        # Match the TOP-LEVEL key only, and read the number rather than searching for
        # its text. A substring test passes on two things that are not a rank at all:
        # a commented-out line, and the same key indented inside a dated block.
        # Both were live here - Bulgaria had `government_rank = 2` swallowed by the
        # end of a comment on line 4, and France's only occurrence was inside its
        # 1792 revolution block - so West Francia was a duchy and the First
        # Bulgarian Empire was one too, and the build called both correct.
        top = re.search(r"^government_rank\s*=\s*(\d+)", txt, re.M)
        got = int(top.group(1)) if top else None
        note(got == want, f"{t} government_rank = {want}"
                          + ("" if got is None else f" (top-level, found {got})")
                          + (" - ABSENT, so EU4 defaults it to a duchy" if top is None else ""))
    # A realm with land, a name and a rank but no country file is unplayable. The
    # gate fails for any such realm that is not an explicitly declared deferral, so a
    # NEW gap still stops the build; a declared one is reported every time instead of
    # turning the build permanently red for a reason people learn to ignore.
    undeclared = [t for t in unwritten if t not in DEFERRED_REALMS]
    note(not undeclared,
         f"every kept realm has a country file, or a declared reason it has none "
         f"({len(KEPT_REALMS)} realms, {len(DEFERRED_REALMS)} deferred)")
    for t in undeclared:
        print(f"        {t}: holds land, has a rank, but no country file")
    for t in sorted(set(unwritten) & set(DEFERRED_REALMS)):
        print(f"        DEFERRED {t}: {DEFERRED_REALMS[t]}")

    print("\n== province ownership ==")
    files = {}
    for fn in sorted(os.listdir(PDIR)):
        files[int(re.match(r"^(\d+)", fn).group(1))] = os.path.join(PDIR, fn)
    note(len(files) == len(os.listdir(PDIR)), f"no duplicate province files ({len(files)} unique)")

    own, hre, badown, multicore = Counter(), [], [], []
    cores_new = {}
    for pid, path in files.items():
        s, c0, ca, h = parse(path)
        o = s.get("owner")
        ctrl = s.get("controller")
        if o is None and ctrl is None:
            # The undated header declares no owner at all. That is only acceptable
            # for the deliberately unowned Balaton parking provinces; everywhere
            # else it means the province is populated by a dated block, so fall back
            # to replaying the file to the start date rather than calling it
            # ownerless. Vanilla's 367 Azores and 368 Madeira are exactly this:
            # uninhabited in the header, settled by a 1427.11.29 block that gives
            # them to POR, and they are only in scope now because the ADU transfer
            # takes Portugal's islands. check_start.effective() is the same replay
            # check_start.py uses, so the two tools cannot disagree about a start.
            if int(pid) in BALATON_RESERVED:
                pass
            else:
                text = open(path, encoding="utf-8",
                            errors="surrogateescape").read()
                o, ctrl, _, _ = effective(text)
                if o is None:
                    badown.append(f"{pid} has no owner at the start date")
                    continue
        own[o] += 1
        # A deliberately unowned province (see gen_provinces.unown - the Balaton
        # parking lot) has neither owner nor controller, which is consistent. Only a
        # half-set pair is a defect.
        if o is None and ctrl is None:
            pass
        elif ctrl != o:
            badown.append(f"{pid} controller={ctrl} owner={o}")
        if h:
            hre.append(pid)
        for c in c0:
            cores_new.setdefault(c, []).append(pid)
        hit = [t for t in TAGS if t in c0]
        # A vanilla core often survives a historical handover (e.g. 203 Lyonnais and
        # 204 Dauphine are FRA-cored in vanilla but Lotharingian in 867). That is
        # legitimate, so only flag double-coring that is not backed by ownership.
        if len(hit) > 1 and o not in TAGS:
            multicore.append(f"{pid}: {hit} (owner {o})")

    note(not badown, f"every province has owner == controller ({len(badown)} problems)")
    for b in badown[:8]:
        print("        " + b)
    note(not hre, f"no 'hre = yes' anywhere ({len(hre)} left)")
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
        s, _, _, _ = parse(files[CAPS[t]])
        note(s.get("owner") == t, f"{t} capital {CAPS[t]} ({s.get('capital')}) owned by {s.get('owner')}")

    print("\n== new core on every owned province ==")
    for t in TAGS:
        owned = [pid for pid, p in files.items() if parse(p)[0].get("owner") == t]
        missing = [pid for pid in owned if t not in parse(files[pid])[1]]
        note(not missing, f"{t}: core on all {len(owned)} owned ({len(missing)} missing)")

    print("\n== vanilla cores preserved ==")
    # Vanilla cores are compared through TAG_RENAMES, because the generated files
    # deliberately rewrite them: MAM's cores become EGY's when the Mamluks are folded
    # into Egypt. Comparing the raw strings instead reports all 37 of those as lost
    # regressions and hides any REAL core loss in the noise. A renamed core still
    # counts as retained - the province kept its core, only under a new tag.
    lost = []
    for pid, path in files.items():
        v = vfile(pid)
        if not v:
            continue
        vc = {TAG_RENAMES.get(c, c) for c in parse(v)[1]}
        mc = set(parse(path)[1])
        if not vc <= mc:
            lost.append(f"{pid} lost {sorted(vc - mc)}")
    note(not lost, f"all vanilla initial cores retained ({len(lost)} regressions)")
    for l in lost[:10]:
        print("        " + l)

    print("\n== absorbed tags ==")
    # A tag survives if it still holds a vanilla INITIAL core outside the 5 realms.
    # Tags whose entire land sits inside a kingdom cannot be released; that is an
    # accepted consequence of reassigning European provinces, not a defect.
    vcore = {}
    for pid in os.listdir(VDIR):
        m = re.match(r"^(\d+)", pid)
        if m:
            vcore[int(m.group(1))] = parse(os.path.join(VDIR, pid))[1]
    taken = {pid for pid, path in files.items()
             if parse(path)[0].get("owner") in TAGS}
    survivors, absorbed = [], []
    for tag in sorted({c for cs in vcore.values() for c in cs}):
        held = [p for p, cs in vcore.items() if tag in cs]
        left = [p for p in held if p not in taken]
        if left:
            survivors.append(f"{tag}({len(left)})")
        elif held:
            absorbed.append(tag)
    note(True, f"{len(survivors)} tags keep cores outside the realms -> releasable")
    print(f"        {', '.join(survivors)}")
    note(True, f"{len(absorbed)} tags fully absorbed -> intentionally gone")
    print(f"        {', '.join(absorbed)}")

    print("\n== untouched neighbours intact ==")
    # Only the reassigned provinces matter here. The other overridden files exist
    # solely to strip hre=yes and legitimately keep their vanilla owner.
    reassigned = {pid for pid, p in files.items()
                  if parse(p)[0].get("owner") in TAGS}
    for t in ["BOH", "HUN", "POL", "PAP", "NAP", "SIC", "SARD", "DAN", "SWE", "NOR",
              "ENG", "CAS", "POR", "MKL", "POM", "BRA"]:
        owned = [pid for pid in reassigned if parse(files[pid])[0].get("owner") == t]
        note(not owned, f"{t} owns none of the {len(reassigned)} reassigned provinces")

    # The prose in the decision description quotes a province count by hand, and it
    # has already been wrong twice (210, then 221, then 225). Tie all three together:
    # the allocation, the generated decision, and the number written for the player.
    print("\n== hre decision matches the empire's land ==")
    # empire_core(), the same call the decision generator makes. This used to compare the
    # decision against the holdings of five privileged tags, which meant it could not
    # detect the decision disagreeing with the empire's actual extent - it defined the
    # extent as whatever those five held.
    expected = set(empire_core())
    dec = open(os.path.join(MOD, "decisions", "KarolingianHRE.txt"),
               encoding="utf-8", errors="replace").read()
    required = {int(x) for x in re.findall(
        r"NOT = \{\s*(\d+)\s*=\s*\{\s*country_or_non_sovereign_subject_holds\s*=\s*ROOT",
        dec)}
    note(required == expected,
         f"decision requires exactly the {len(expected)} imperial provinces")
    if required != expected:
        print(f"        only in decision : {sorted(required - expected)}")
        print(f"        only in the core : {sorted(expected - required)}")
    note(not (required - expected),
         "no province outside the 867 empire is required to restore it")
    hreloc = open(os.path.join(MOD, "localisation", "karolingian_hre_l_english.yml"),
                  encoding="utf-8", errors="replace").read()
    said = re.search(r"hold all (\d+) provinces", hreloc)
    note(bool(said), "decision description quotes a province count")
    if said:
        note(int(said.group(1)) == len(expected),
             f"description says {said.group(1)}, partition has {len(expected)}")

    # A tag that owns land but not its own capital is legal in EU4, yet it is
    # always a sign that a capital was overlooked - Silesia lost Ratibor to Great
    # Moravia and was left holding three provinces with no seat until its history
    # was patched. Resolve every realm's seat, including vanilla recipients, and
    # require that they actually hold it.
    print("\n== every realm holds its own capital ==")
    # Vanilla tags this mod gives an 867 ruler to. BOH, GMA and SIL are generated by
    # gen_countries.py; BUL, CRT, DAL, ARB and EGY were added later as hand-written
    # files, so they have to be listed here too or the age/regency check skips them.
    RULER_TAGS = ["BOH", "GMA", "SIL", "BUL", "CRT", "DAL", "ARB", "EGY", "ADU", "ASU",
                  "BYZ"]
    # Tags whose ruler name and dynasty must match CK3's 867 bookmark. Kept as its
    # own list rather than deriving it from ck3ruler.TITLES at import time,
    # because validate.py must keep working if CK3 is not installed on the machine
    # running it, whereas ck3ruler.py legitimately requires CK3 to exist.
    #
    # This is a cross-tool check, not a duplicate: ck3ruler.py is what writes these
    # strings, and this is what stops a later hand-edit from drifting away from CK3
    # without anyone noticing. Run ck3ruler.py --fix to resync after changing either.
    #
    # CRT is not here: CK3 has no Crete at all. BOH, GMA and SIL are not here either:
    # they are mod-invented Slavic rulers, not CK3-sourced. See ck3ruler.py.
    CK3_RULER_TAGS = ["ARB", "ADU", "ASU", "BYZ", "BUL", "DAL", "EGY"]


    # Vanilla tags this mod only patched the capital of.
    CAPITAL_FIXES = {"SIL": 264, "HUN": 283}
    prov_owner = {}
    for pid, path in files.items():
        prov_owner[pid] = parse(path)[0].get("owner")
    # Vanilla owners AT THE 1444.11.11 START_DT, so a tag we merely gifted a province to
    # still counts the land it kept. A vanilla province drops out of the count the
    # moment we write it with somebody else as owner. This must be owner_1444 and not
    # the top-level `owner`: the top level predates every dated block, and 158
    # provinces change hands inside (867, 1444].
    _bp = json.load(open(str(CACHE / "provdata.json")))["provs"]


    def holds(tag):
        held = {pid for pid, o in prov_owner.items() if o == tag}
        for pid, pr in _bp.items():
            pid = int(pid)
            if pr.get("owner_1444", pr.get("owner")) == tag and prov_owner.get(pid, tag) == tag:
                held.add(pid)
        return held


    def vanilla_capital(tag):
        for fn in os.listdir(GH):
            if fn.startswith(tag + " - ") and fn.endswith(".txt"):
                m = re.search(r"^\s*capital\s*=\s*(\d+)",
                              open(os.path.join(GH, fn), encoding="utf-8",
                                   errors="replace").read(), re.M)
                return int(m.group(1)) if m else None
        return None


    for t in dict.fromkeys(ALL_TAGS + RULER_TAGS):
        cap = CAPS.get(t) or CAPITAL_FIXES.get(t) or vanilla_capital(t)
        held = holds(t)
        if cap is None:
            note(not held, f"{t} owns nothing and declares no capital")
            continue
        src = ("mod" if (t in CAPS or t in CAPITAL_FIXES) else "vanilla")
        note(cap in held, f"{t} holds its {src} capital {cap} "
                          f"({len(held)} province{'s' if len(held) != 1 else ''})")

    # Rulers are age-checked, because the +577 shift that keeps a king's 867 age
    # also turns a genuinely young 867 ruler into a child in 1444. A minor monarch
    # must therefore be flagged regent = yes, or the realm is silently ruled by
    # someone the game thinks cannot rule.
    print("\n== 867 rulers ==")
    # CK3 is only needed for the name/dynasty cross-check below. Everything else in
    # validate.py runs without it, so a missing install skips exactly these checks
    # with an explicit message instead of taking the whole validator down.
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

    # Both checks below read ck3ruler's registries rather than keeping a second copy
    # of the tag list here, because a list in two places is a list that will drift.
    #
    #   * coverage: every tag owning land at the start date must be classified as
    #     either CK3-derived (TITLES) or deliberately not (NOT_CK3). ck3ruler
    #     derives the set from the generated province files, so a realm added to the
    #     mod later shows up here unclassified instead of escaping the audit.
    #   * drift: for each CK3-derived tag, name and dynasty must still equal what
    #     CK3 says. Dynasty resolution goes through ck3ruler's own function because
    #     the house-vs-nested-dynasty preference is subtle enough to get wrong twice.
    if _b is not None:
        _holders = _b.land_holders()
        _unclassified = sorted(t for t in _holders
                               if t not in _b.TITLES
                               and t not in _b.NOT_CK3)
        for t in _unclassified:
            note(False, f"{t} owns {_holders[t]} provinces at the start date but is "
                        f"in neither _b.TITLES nor _b.NOT_CK3")
        note(not _unclassified,
             f"all {len(_holders)} start-date land-holders are classified as "
             f"CK3-derived or deliberately not ({len(_b.TITLES)} + "
             f"{len(_b.NOT_CK3)})")

        for t in sorted(_b.TITLES):
            want = _b.resolve(t, _titles, _chars, _dyn, _houses)
            if "error" in want:
                note(False, f"{t} CK3 lookup failed: {want['error']}")
                continue
            cp = os.path.join(COUNTRY_OUT, f"{t}.txt")
            if not os.path.exists(cp):
                # Mapped in ck3ruler.TITLES but no mod country file: the mod keeps the
                # vanilla one, so there is no name/dynasty of ours to compare. ck3ruler
                # reports the CK3 values as a NOTE. The coverage check above is what
                # guarantees a realm cannot slip through unclassified, so this is a
                # skip rather than a failure - NAV is the current example.
                print(f"  SKIP {t} has no mod country file; keeps vanilla's ruler "
                      f"(CK3 {t} would be {want['name']} / {want['dynasty']})")
                continue
            body = open(cp, encoding="utf-8", errors="replace").read()
            blk = re.search(r"^1444\.1\.1 = \{\s*\n\tmonarch = \{(.*?)^\t\}", body,
                            re.M | re.S)
            if not blk:
                note(False, f"{t} has a 1444 monarch")
                continue
            got_n, got_d = _b.current(blk.group(1))
            note(got_n == want["name"] and got_d == want["dynasty"],
                 f"{t} ruler name/dynasty matches CK3 867 "
                 f"({want['name']} / {want['dynasty']})")
        print("        run tools/_b.py --fix to resync")

    START_DT = (1444, 11, 11)
    for t in TAGS + RULER_TAGS:
        p = os.path.join(COUNTRY_OUT, f"{t}.txt")
        if not os.path.exists(p):
            note(False, f"{t} has a history file")
            continue
        body = open(p, encoding="utf-8", errors="replace").read()
        blk = re.search(r"^1444\.1\.1 = \{\s*\n\tmonarch = \{(.*?)^\t\}", body,
                        re.M | re.S)
        if not blk:
            note(False, f"{t} has a 1444 monarch")
            continue
        m = blk.group(1)
        nm = re.search(r'name = "([^"]+)"', m)
        bd = re.search(r"birth_date = (\d+)\.(\d+)\.(\d+)", m)
        if not (nm and bd):
            note(False, f"{t} monarch has a name and birth_date")
            continue
        y, mo, d = (int(x) for x in bd.groups())
        # days from birth to the start date, ignoring leap years
        age = START_DT[0] - y - ((START_DT[1], START_DT[2]) < (mo, d))
        regent = "regent = yes" in m
        note(age >= 15 or regent,
             f"{t} ruled by {nm.group(1)}, {age} in 1444"
             + (" (regent)" if regent else ""))
        print(f"        {t} {nm.group(1):14} born {y} "
              f"{'-> age %d at the start date' % age}{', flagged regent' if regent else ''}")

    # Every localisation file must start with a UTF-8 BOM. All 143 vanilla
    # *_l_english.yml files do, and the engine silently discards any that do not -
    # no error, no log line, the file just never loads. That is exactly how the
    # realm names stayed "France" and "Germany" while this file looked correct.
    # Walked recursively: localisation/replace/ is where overrides of vanilla keys
    # must live, and a flat scan skipped it entirely - the one folder whose files
    # matter most here would have gone unchecked.
    LOC = os.path.join(MOD, "localisation")
    print("\n== localisation files load ==")
    for root, _dirs, files in os.walk(LOC):
        for fn in sorted(files):
            if not fn.endswith("_l_english.yml"):
                continue
            raw = open(os.path.join(root, fn), "rb").read(3)
            rel = os.path.relpath(os.path.join(root, fn), MOD)
            note(raw == b"\xef\xbb\xbf", f"{rel} starts with a UTF-8 BOM")

    # The five Carolingian realms must all be one dynasty, heirs included. A shared
    # dynasty is what unlocks Claim Cushion, so a hand-written dynasty on a single
    # heir - which is exactly how Arnulf and Berengar used to end up "of Carinthia"
    # and "of Italy" - quietly breaks reunification by marriage the first time that
    # realm changes ruler.
    print("\n== shared Carolingian dynasty ==")
    KAROLINGIAN = ["FRA", "LOT", "GER", "BAV", "ITA"]
    seen_dyn = set()
    for t in KAROLINGIAN:
        p = os.path.join(COUNTRY_OUT, f"{t}.txt")
        body = open(p, encoding="utf-8", errors="replace").read()
        blk = re.search(r"^1444\.1\.1 = \{.*?^\}", body, re.M | re.S)
        ds = re.findall(r'dynasty = "([^"]+)"', blk.group(0)) if blk else []
        note(bool(ds) and len(set(ds)) == 1,
             f"{t} 1444 ruler and heir share one dynasty")
        for d in set(ds):
            print(f"        {t}: {d}")
        seen_dyn |= set(ds)
    note(len(seen_dyn) == 1,
         f"all five realms use the same dynasty string ({', '.join(sorted(seen_dyn))})")

    # No localisation file may be missing its BOM, and no realm may keep a
    # hand-written dynasty that silently diverges from the house.
    # The HRE must not exist at the start date. There is no empire switch in 1.37:
    # a country holds a vote purely because its history says `elector = yes` at that
    # date, and vanilla dissolves the empire the same way - seven files carry
    # `1806.7.12 = { elector = no }`, REG's commented "# the HRE is dissolved". That
    # dated block is why a 1821 start has no HRE; a 1444 start never reaches it.
    print("\n== HRE is dissolved ==")


    def electors_as_of(directory):
        """Tags holding a vote at START_DT, not tags that ever mention `elector`.

        A column-0 `elector = yes` is the baseline state. The same key inside a dated
        block is a later state and counts only once that date has arrived. Grepping
        for the key at all conflates the two - it demands an override for Regensburg,
        which only gains a vote in 1803 and holds none in 1444.
        """
        live = set()
        for fn in sorted(os.listdir(directory)):
            if not fn.endswith(".txt"):
                continue
            text = open(os.path.join(directory, fn), encoding="utf-8",
                        errors="replace").read()
            base = re.search(r"^elector\s*=\s*(\w+)", text, re.M)  # column 0 only
            state = bool(base and base.group(1) == "yes")
            for m in re.finditer(r"^(\d{1,4}(?:\.\d{1,2}){0,2})\s*=\s*\{", text, re.M):
                parts = [int(x) for x in m.group(1).split(".")]
                if tuple((parts + [1, 1, 1])[:3]) > START_DT:
                    break  # later dates are history this start date never reaches
                end = text.find("\n}", m.end())
                body = text[m.end():len(text) if end == -1 else end]
                vals = re.findall(r"^\s*elector\s*=\s*(\w+)", body, re.M)
                if vals:
                    state = vals[-1] == "yes"
            if state:
                # vanilla names files "BOH - Bohemia.txt", the mod writes "BOH.txt"
                live.add(fn.split(" - ")[0].removesuffix(".txt"))
        return live


    van_electors = electors_as_of(GH)
    mod_electors = electors_as_of(COUNTRY_OUT)
    note(not mod_electors,
         f"no mod country holds a vote at {START_DT[0]}.{START_DT[1]}.{START_DT[2]} "
         f"(vanilla: {', '.join(sorted(van_electors))})")
    for t in sorted(van_electors):
        note(os.path.exists(os.path.join(COUNTRY_OUT, f"{t}.txt")),
             f"{t} votes in vanilla, so the mod overrides it to dissolve its vote")

    # An empty country file reads as "no elector = yes" to every grep, so a crashed
    # generator can look clean. Size catches it.
    for fn in sorted(os.listdir(COUNTRY_OUT)):
        if fn.endswith(".txt") and os.path.getsize(os.path.join(COUNTRY_OUT, fn)) < 200:
            note(False, f"{fn} is suspiciously small "
                        f"({os.path.getsize(os.path.join(COUNTRY_OUT, fn))} bytes) "
                        f"- generator probably crashed mid-write")

    # No province the mod writes may keep a culture that postdates 867. Checked
    # against the generator's own table rather than a list of 37 province ids, so a
    # province added to the map later is caught instead of quietly staying Turkish.
    # Culture alone is not enough: Sivas 329 is vanilla shiite, not sunni, so a
    # sunni-only rewrite left it greek + Muslim on Byzantine land without failing
    # anything. Hence the religion assertion too.
    gone = set(CULTURE_GONE_867)
    stale_culture, stale_religion = [], []
    for fn in sorted(os.listdir(PDIR)):
        if not fn.endswith(".txt"):
            continue
        # Vanilla is not consistent about the separator: most files are "318 - Sugla"
        # but at least one is "1853- Kastoria", so take the leading digits rather than
        # splitting on " - " and trusting it.
        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        pid = int(m.group(1))
        text = open(os.path.join(PDIR, fn), encoding="utf-8",
                    errors="surrogateescape").read()
        m = re.search(r"^\s*culture\s*=\s*(\w+)", text, re.M)
        culture = m.group(1) if m else None
        if culture in gone:
            stale_culture.append(f"{pid} {fn} ({culture})")
        if culture == "greek" and pid not in CONQUERED_BY_THE_ARABS:
            for rel in re.findall(r"^\s*religion\s*=\s*(\w+)", text, re.M):
                if rel in MUSLIM_RELIGIONS_867:
                    stale_religion.append(f"{pid} {fn} ({rel})")
    note(not stale_culture,
         "no mod-written province keeps a culture that postdates 867"
         + ("" if not stale_culture else f": {', '.join(stale_culture)}"))
    note(not stale_religion,
         "every Greek province outside the Arab conquest is orthodox"
         + ("" if not stale_religion else f": {', '.join(stale_religion)}"))

    print("\n" + ("ALL CHECKS PASSED" if not fail else f"{len(fail)} FAILURES"))

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(run())
