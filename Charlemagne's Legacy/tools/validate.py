#!/usr/bin/env python3

import json, os, re, sys
from paths import EU4_GAME, local_mod_path
from collections import Counter
from build import parse
from db import core_deny_map
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"

GAME = EU4_GAME
MOD = str(HERE.parent)
PDIR = os.path.join(MOD, "history", "provinces")
COUNTRY_OUT = os.path.join(MOD, "history", "countries")
from build import TAGS as _REALMS  # noqa: E402

from enc import encname  # noqa: E402

TAGS = sorted(t.tag for t in _REALMS if t.ck3_title)

sys.path.insert(0, str(HERE))
from build import (
    PROVINCES,
    CAPITAL,
    empire_core,
    karling_realms,
)

# this mod's 867 culture/religion expectations, checked against the files
# the build writes
CONQUERED_BY_THE_ARABS = {327, 332, 2303, 4298, 4310, 124, 125, 4736, 4737}
MUSLIM_RELIGIONS_867 = ("sunni", "shia", "kharijite")
from build import effective  # noqa: E402

CAPS = CAPITAL

from build import RANK, KEPT_REALMS  # noqa: E402

from build import BY_TAG  # noqa: E402

from tagdb import BY_FORMABLE, CTRY_DATE, DIPLOMACY, DORMANT, FORMABLES, FORMABLE_TAGS, required_count  # noqa: E402

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
        local_mod_path("/home/rick/.local/share/Paradox Interactive/Europa Universalis IV/mod/Charlemagne's Legacy.mod"),
        f"{MOD}/descriptor.mod",
        f"{MOD}/localisation/replace/countries_l_english.yml",
    ]:
        note(os.path.exists(p), f"exists {os.path.relpath(p, MOD)}")

    print("\n== country definitions ==")
    GH = os.path.join(GAME, "history", "countries")
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

    print("\n== 867 only ==")
    n = 0
    bad = []
    for d in (PDIR, COUNTRY_OUT):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".txt"):
                continue
            n += 1
            t = open(
                os.path.join(d, fn), encoding="utf-8", errors="surrogateescape"
            ).read()
            for m in re.finditer(r"(?m)^\s*(\d+\.\d+\.\d+)\s*=", t):
                if m.group(1) != "867.1.1":
                    bad.append(f"{fn}: {m.group(1)}")
                    break
    note(not bad, f"no non-867 history in {n} files")
    for b in bad[:10]:
        print("        " + b)

    print("\n== country files ==")


    def country_path(t: str) -> str:
        for fn in os.listdir(COUNTRY_OUT):
            if fn.startswith(f"{t} - ") and fn.endswith(".txt"):
                return os.path.join(COUNTRY_OUT, fn)
        return os.path.join(COUNTRY_OUT, f"{t}.txt")


    vanilla_hist = {
        fn.split(" - ")[0]
        for fn in os.listdir(os.path.join(GAME, "history", "countries"))
        if fn.endswith(".txt")
    }
    for t in TAGS:
        spec = BY_TAG.get(t)
        if spec is not None and not spec.country_file and t not in vanilla_hist:
            note(
                False,
                f"{t} needs country_file set (else its file is '{t} - {t}.txt')",
            )


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

    print("\n== no province is in the vanilla HRE ==")
    # 867 knows no Holy Roman Empire: vanilla heads ship `hre = yes` on the
    # whole former empire's land, and one leaking line puts a whole realm
    # (whatever sits on that capital) inside the vanilla HRE.
    hre_dirty = []
    for fn in sorted(os.listdir(PDIR)):
        if fn.endswith(".txt") and re.search(
            r"^hre\s*=\s*yes",
            open(os.path.join(PDIR, fn), encoding="utf-8", errors="replace").read(),
            re.M,
        ):
            hre_dirty.append(fn)
    note(not hre_dirty, f"no hre = yes in {len(files)} province files ({len(hre_dirty)} dirty)")
    for b in hre_dirty[:10]:
        print("        " + b)

    from eu4 import (  # noqa: E402
        lake_ids,
        sea_ids,
        vanilla_prov_file,
        vanilla_prov_ids,
        waste_ids,
    )

    for label, ids in (("wasteland", waste_ids()), ("lake", lake_ids())):
        wfiles = [p for p in ids if vanilla_prov_file(p)]
        wmiss = sorted(p for p in wfiles if p not in files)
        note(not wmiss, f"every vanilla {label} province has a file ({len(wmiss)} missing)")
        for b in wmiss[:8]:
            print("        " + str(b))
        wowned = sorted(
            p for p in wfiles if p in files and parse(files[p])[0].get("owner") is not None
        )
        note(not wowned, f"no owner on {label} provinces ({len(wowned)} problems)")
        for b in wowned[:8]:
            print("        " + str(b))

    print("\n== unownable land is unowned in the database ==")
    # The database is the source of truth: catch a grey/water claim in a
    # tag row before any file is generated. The build asserts the merged
    # output; this checks the claims themselves - wastelands, lakes and
    # sea tiles alike can have no landlord.
    from eu4 import build  # noqa: E402
    unownable = set(waste_ids()) | set(lake_ids()) | set(sea_ids())
    claimed = sorted(
        {p for _tag, ps in build().items() for p in ps if p in unownable}
    )
    note(
        not claimed,
        f"no database tag claims grey or water ({len(claimed)} problems)",
    )
    for b in claimed[:8]:
        print("        " + str(b))

    print("\n== the New World and Australia stay uncolonised ==")
    # Unsupported by this mod: every land province of the American
    # superregions and of Australia must stay empty - no owner, controller,
    # core, population or database row, and no tag sitting there.
    def _block(text, name):
        m = re.search(r"(?m)^" + re.escape(name) + r"\s*=\s*\{", text)
        if not m:
            return ""
        depth, k = 0, text.index("{", m.start())
        for i in range(k, len(text)):
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                return text[k + 1:i]
        return ""

    _map = lambda f: open(os.path.join(GAME, "map", f), encoding="utf-8", errors="replace").read()
    _sup, _reg, _area = _map("superregion.txt"), _map("region.txt"), _map("area.txt")
    _regions = {"australia_region"}
    for sr in ("north_america_superregion", "south_america_superregion", "andes_superregion",
               "central_america_superregion", "new_world_superregion"):
        _regions |= set(re.findall(r"(\w+_region)\b", _block(_sup, sr)))
    _newworld = set()
    for rg in _regions:
        for ar in re.findall(r"(\w+_area)\b", _block(_reg, rg)):
            _newworld |= {int(x) for x in re.findall(r"\b(\d+)\b",
                          re.sub(r"color\s*=\s*\{[^}]*\}", "", re.sub(r"#[^\n]*", "", _block(_area, ar))))}
    _newworld -= set(sea_ids()) | set(lake_ids())
    note(len(_newworld) > 500, f"{len(_newworld)} New World and Australian provinces identified")
    _owned = sorted({p for _t, ps in build().items() for p in ps if p in _newworld})
    note(not _owned, f"no tag owns New World or Australian land ({len(_owned)} problems)")
    for b in _owned[:8]:
        print("        " + str(b))
    import sqlite3 as _sq
    _db = _sq.connect(str(HERE / "tags.db"))
    _rows = sorted(r[0] for r in _db.execute("select pid from provinces") if r[0] in _newworld)
    _caps = sorted(r[0] for r in _db.execute("select tag from tags where capital in (%s)" % ",".join(map(str, _newworld))))
    _db.close()
    note(not _rows, f"no database province row in the New World or Australia ({len(_rows)} problems)")
    for b in _rows[:8]:
        print("        " + str(b))
    note(not _caps, f"no tag has a New World or Australian capital ({len(_caps)} problems)")
    _dirty = []
    for p in sorted(_newworld):
        if p not in files:
            continue
        sc, c0, ca = parse(files[p])
        if c0 or ca or any(k in sc for k in ("owner", "controller", "culture", "religion",
                                              "base_tax", "base_production", "base_manpower")):
            _dirty.append(p)
    note(not _dirty, f"New World and Australian province files carry no owner, core or population ({len(_dirty)} problems)")
    for b in _dirty[:8]:
        print("        " + str(b))

    vmiss = sorted(p for p in vanilla_prov_ids() if p not in files)
    note(not vmiss, f"every vanilla province has a file ({len(vmiss)} missing)")
    for b in vmiss[:8]:
        print("        " + str(b))
    seaset = set(sea_ids())  # sea tiles stay undated, tags and all
    vtags = sorted(
        p
        for p in files
        if p not in seaset
        and re.search(
            r"(?m)^\s*discovered_by\s*=\s*([A-Z]{3})\s*$",
            open(files[p], encoding="utf-8", errors="surrogateescape").read(),
        )
    )
    note(not vtags, f"no tag-specific discovery on land ({len(vtags)} problems)")
    for b in vtags[:8]:
        print("        " + str(b))

    print("\n== no base-game flag is reused ==")
    # Vanilla flags never carry over: gfx/flags is replace_path'd, a reused code
    # (BNG, SND ...) stays visibly flagless until it has its own flag, and no
    # flag file may equal one of the base game's (checked where the install has them).
    import hashlib as _hl
    from tagdb import TAGS as _tg0
    vflag_dir = os.path.join(GAME, "gfx", "flags")
    from_vanilla = [t_.tag for t_ in _tg0 if t_.flag_from]
    note(not from_vanilla, f"no tag takes its flag from the base game ({len(from_vanilla)} do)")
    if os.path.isdir(vflag_dir):
        vsum = {}
        for fn in os.listdir(vflag_dir):
            if fn.lower().endswith(".tga"):
                vsum.setdefault(_hl.md5(open(os.path.join(vflag_dir, fn), "rb").read()).hexdigest(), fn)
        dup = [fn for fn in sorted(os.listdir(os.path.join(MOD, "gfx", "flags")))
               if fn.lower().endswith(".tga")
               and _hl.md5(open(os.path.join(MOD, "gfx", "flags", fn), "rb").read()).hexdigest() in vsum]
        note(not dup, f"no flag file equals a base-game flag ({len(dup)} do)")
        for fn in dup[:20]:
            print(f"        {fn} is byte-identical to the base game's")

    print("\n== reuse tags keep vanilla tech ==")
    # A tag whose code exists in the base game carries the same tech group
    # vanilla gives it - anything else hides its neighbours (the Arabia
    # class of bug). 867-correct divergences get named rows below; each
    # must earn its keep in the AGENTS notes.
    from tagdb import TAGS as _tagrows  # noqa: E402
    import glob as _glob
    deliberate = set()  # no landed tag carries deliberate vanilla-tech drift
    drift = []
    for t in _tagrows:
        hits = _glob.glob(os.path.join(GAME, "history", "countries",
                                       f"{t.tag} - *.txt"))
        if not hits:
            continue
        txt = open(hits[0], encoding="cp1252", errors="replace").read()
        m = re.search(r"(?m)^\s*technology_group\s*=\s*([a-z_]+)", txt)
        if not m:
            continue
        if t.technology_group != m.group(1) and (t.tag, t.technology_group) \
                not in deliberate:
            drift.append(f"{t.tag}: ours {t.technology_group}, "
                         f"vanilla {m.group(1)}")
    note(
        not drift,
        f"reuse tags carry vanilla tech ({len(drift)} drifting)",
    )
    for b in drift[:8]:
        print("        " + b)

    print("\n== tags carry their ruler's culture and faith ==")
    # Every tag takes its CK3 title's 867 holder culture and faith - the
    # ruler calls stand even on foreign land (Norse tags on Slavic
    # ground), and provinces keep their vanilla culture regardless.
    # Holders with unscripted CK3 data slip out (counted, not verified).
    from culturelift import holder_culture, holder_faith, FAITH_TO_RELIGION  # noqa: E402
    cult_drift, rel_drift, unscripted = [], [], []
    for t in _tagrows:
        if not t.ck3_title:
            continue
        # a tag follows the holder of its title, or of its ruler_title when it has one
        lanes = [t.ck3_title] + ([t.ruler_title] if t.ruler_title else [])
        ecus, erels = [], []
        for ttl in lanes:
            _h, cculture = holder_culture(ttl)
            _h2, faith = holder_faith(ttl)
            ecus.append(cculture or None)
            erels.append(FAITH_TO_RELIGION.get(faith) if faith else None)
            if ttl == t.ck3_title:
                c0, f0 = cculture, faith
        if not c0:
            unscripted.append(f"{t.tag} (no ruler culture)")
        elif not ecus[0]:
            unscripted.append(f"{t.tag} (ruler culture {c0} unmapped)")
        elif t.culture not in ecus:
            cult_drift.append(f"{t.tag}: db {t.culture}, ruler {ecus[0]}")
        if not f0:
            unscripted.append(f"{t.tag} (no ruler faith)")
        elif not erels[0]:
            unscripted.append(f"{t.tag} (faith {f0} unmapped)")
        elif t.religion not in erels:
            rel_drift.append(f"{t.tag}: db {t.religion}, ruler {erels[0]}")
    note(
        not cult_drift,
        f"tag cultures track the ruler ({len(cult_drift)} drifting)",
    )
    for b in cult_drift[:8]:
        print("        " + str(b))
    note(
        not rel_drift,
        f"tag faiths track the ruler ({len(rel_drift)} drifting)",
    )
    for b in rel_drift[:8]:
        print("        " + str(b))
    note(
        len(unscripted) < 40,
        f"CK3 data covers most lookups "
        f"({len(_tagrows) * 2 - len(unscripted)} verified, "
        f"{len(unscripted)} holders unscripted)",
    )
    for b in unscripted[:200]:
        print("        " + str(b))

    unownable = set(waste_ids()) | set(lake_ids())  # never owned by design

    own, badown, multicore = Counter(), [], []
    cores_new = {}
    for pid, path in files.items():
        s, c0, ca = parse(path)
        o = s.get("owner")
        ctrl = s.get("controller")
        if o is None and ctrl is None:

            if int(pid) not in PROVINCES or int(pid) in unownable:
                pass  # a vanilla sea tile, lake or wasteland (no owner by design)
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

    denied = {}
    for owner, holders in core_deny_map().items():
        denied.setdefault(owner, set()).update(holders)
    stray = []
    for pid, path in files.items():
        s, _, _ = parse(path)
        o = s.get("owner")
        if o in denied:
            text = open(path, encoding="utf-8", errors="surrogateescape").read()
            hit = sorted(
                set(re.findall(r"(?m)^\s*add_core\s*=\s*([A-Z]{3})", text))
                & denied[o]
            )
            if hit:
                stray.append(f"{pid} owned by {o} still cored by {hit}")
    note(not stray, f"denied cores stay out ({len(stray)} problems)")
    for b in stray[:8]:
        print("        " + b)

    print("\n== realm sizes ==")
    for t in TAGS:
        if t in DORMANT:
            note(own[t] == 0, f"{t} dormant (has {own[t]})")
            continue
        note(own[t] > 0, f"{t} owns {own[t]} provinces")
    note(own["HLR"] == 0, f"HLR owns 0 provinces (has {own['HLR']})")
    print(f"        new total = {sum(own[t] for t in TAGS)}")

    print("\n== capitals inside own realm ==")
    for t in TAGS:
        if t in DORMANT:
            continue
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
    alive = KEPT_REALMS | {'HLR'}
    dead = []
    for pid, path in files.items():
        for c in parse(path)[1]:
            if c not in alive:
                dead.append(f'{pid}: core for {c}')
    note(not dead, f'every core belongs to a living tag ({len(dead)} dead)')
    for d in dead[:10]:
        print('        ' + d)

    print('\n== forts only where the database says so ==')
    kept = {pid for pid, p in PROVINCES.items() if p.fort}
    fort_bad = []
    for pid, path in files.items():
        text = open(path, encoding="utf-8", errors="surrogateescape").read()
        has = bool(re.search(r"(?m)^\s*fort_15th\s*=", text))
        if pid in kept and not has:
            fort_bad.append(f"{pid}: keep-flagged but unfortified")
        elif pid not in kept and has:
            fort_bad.append(f"{pid}: fortified without a flag")
    note(not fort_bad, f"forts match the database ({len(fort_bad)} bad)")
    for b in fort_bad[:10]:
        print('        ' + b)

    print("\n== untouched neighbours intact ==")

    reassigned = {pid for pid, p in files.items() if parse(p)[0].get("owner") in TAGS}
    for t in [
        "SARD",
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

    print("\n== finland decisions cover finland and bothnia ==")

    finland = {27, 28, 29, 31, 4123, 19, 4113, 4152}
    fblk = re.search(
        r"kar_form_finland_provinces_trigger = \{(.*?)\n\}",
        trig,
        re.S,
    )
    fbody = fblk.group(1) if fblk else ""
    freq = {int(x) for x in re.findall(r"province_id = (\d+)", fbody)}
    for a in re.findall(r"^\s*area = (\w+)", fbody, re.M):
        freq |= {int(x) for x in cdata["areas"].get(a, ())}
    note(freq == finland, f"trigger covers exactly the {len(finland)} finnish provinces")
    cblk = re.search(
        r"kar_form_finland_capital_trigger = \{(.*?)\n\}",
        trig,
        re.S,
    )
    cbody = cblk.group(1) if cblk else ""
    creq = {int(x) for x in re.findall(r"province_id = (\d+)", cbody)}
    for a in re.findall(r"^\s*area = (\w+)", cbody, re.M):
        creq |= {int(x) for x in cdata["areas"].get(a, ())}
    note(creq == finland, "capital trigger covers exactly the finnish provinces")
    findec = open(
        os.path.join(MOD, "decisions", "FinlandKingdom.txt"),
        encoding="utf-8",
        errors="replace",
    ).read()
    note(
        "tag = FIN" in findec and "change_tag = FIN" in findec,
        "crown path stays FIN, form path changes to FIN",
    )
    note(
        "NOT = { government_rank = 3 }" in findec,
        "crown path needs Finland below kingdom rank",
    )
    note(
        "NOT = { exists = FIN }" in findec,
        "form path needs Finland gone",
    )
    note(
        "primary_culture = finnish" in findec,
        "form path is finnish-gated",
    )
    note(
        findec.count("NOT = { government_rank = 3 }") >= 2,
        "both finland paths need a non-kingdom firer",
    )
    note(
        "set_government_rank = 3" in findec,
        "both paths crown rank 3",
    )
    finloc = open(
        os.path.join(MOD, "localisation", "finland_l_english.yml"),
        encoding="utf-8",
        errors="replace",
    ).read()
    note(
        "kar_form_finland_title:0" in finloc
        and "kar_crown_finland_title:0" in finloc,
        "both decisions named in loc",
    )

    print("\n== starting subjects ==")
    dip = os.path.join(MOD, "history", "diplomacy", "karolingian_vassals.txt")
    raw_dip = open(dip, encoding="cp1252", errors="replace").read()
    found = list(
        zip(
            re.findall(r"first\s*=\s*([A-Z]{3})", raw_dip),
            re.findall(r"second\s*=\s*([A-Z]{3})", raw_dip),
        )
    )
    expected_dip = [(d.liege, d.subject) for d in DIPLOMACY]
    note(found == expected_dip, "diplomacy file lists exactly the starting subjects")
    if found != expected_dip:
        print(f"        in file    : {found}")
        print(f"        in tagdb   : {expected_dip}")

    print("\n== no tag starts over its diplomatic relation limit ==")
    # Vassals, marches, appanages and personal unions each take a relation slot (tributaries and daimyo do not,
    # per their subject type's takes_diplo_slot); alliances and royal marriages take one for each party (an alliance and a marriage with the same country share one slot). The
    # limit is the base game's base_values diplomatic_upkeep (as patched) plus the government rank's own
    # diplomatic_upkeep, both read from the mod's files so a tuning change cannot drift from this check.
    from tagdb import PEER_RELATIONS  # noqa: E402

    def _blocks(text):
        out = {}
        for m in re.finditer(r"(?m)^(\w+) = \{\n", text):
            i, d = m.end(), 1
            while d and i < len(text):
                d += (text[i] == "{") - (text[i] == "}")
                i += 1
            out[m.group(1)] = text[m.end():i]
        return out

    def _read(rel):
        return open(os.path.join(MOD, rel), encoding="cp1252", errors="replace").read()

    sub_blocks = _blocks(_read("common/subject_types/00_subject_types.txt"))

    def _takes_slot(kind, depth=0):
        b = sub_blocks.get(kind, "")
        m = re.search(r"(?m)^\s*takes_diplo_slot\s*=\s*(yes|no)", b)
        if m:
            return m.group(1) == "yes"
        c = re.search(r"(?m)^\s*copy_from\s*=\s*(\w+)", b)
        return _takes_slot(c.group(1), depth + 1) if c and depth < 8 else True

    base = int(re.search(r"(?m)^\s*diplomatic_upkeep\s*=\s*(-?\d+)",
                         _blocks(_read("common/static_modifiers/00_static_modifiers.txt"))["base_values"]).group(1))
    rank_blocks = _blocks(_read("common/government_ranks/zz_kar_government_ranks.txt"))

    def _limit(rank):
        b = rank_blocks.get(str(rank), "")
        m = re.search(r"(?m)^\s*diplomatic_upkeep\s*=\s*(-?\d+)", b)
        return base + (int(m.group(1)) if m else 0)

    used = {}
    peers = set()  # an alliance and a royal marriage with the same country share one slot
    for d in DIPLOMACY:
        if d.relation in PEER_RELATIONS:
            peers.add(frozenset((d.liege, d.subject)))
        elif _takes_slot({"union": "personal_union"}.get(d.relation, d.relation)):
            used[d.liege] = used.get(d.liege, 0) + 1
    for pair in peers:
        for t in pair:
            used[t] = used.get(t, 0) + 1
    over = [
        f"{t}: {n} relations, limit {_limit(BY_TAG[t].rank)} (rank {BY_TAG[t].rank})"
        for t, n in sorted(used.items())
        if t in BY_TAG and n > _limit(BY_TAG[t].rank)
    ]
    note(not over, f"no tag starts over its diplomatic relation limit ({len(over)} over, base {base})")
    for o in over:
        print("        " + o)
    tight = [f"{t} {n}/{_limit(BY_TAG[t].rank)}" for t, n in sorted(used.items())
             if t in BY_TAG and n == _limit(BY_TAG[t].rank)]
    if tight:
        print("  WARN at the limit already (one more subject puts them over): " + ", ".join(tight))

    print("\n== historical friendships and rivalries ==")
    bad_rel = []
    for tag in sorted(BY_TAG):
        t = BY_TAG[tag]
        body = open(
            country_path(tag), encoding="utf-8", errors="surrogateescape"
        ).read()
        for other in t.rivals:
            if f"historical_rival = {other}" not in body:
                bad_rel.append(f"{tag} vs {other}")
        for other in t.friends:
            if f"historical_friend = {other}" not in body:
                bad_rel.append(f"{tag} + {other}")
    note(not bad_rel, "all rivalries and friendships written "
         f"({len(bad_rel)} missing)")
    for b in bad_rel[:10]:
        print("        " + b)

    print("\n== reconquista claims ==")
    from eu4 import IBERIA_AREAS  # noqa: E402

    area_of = {}
    for a, pids in cdata["areas"].items():
        for pid in pids:
            area_of[int(pid)] = a
    bad_rec = []
    for pid, path in files.items():
        s, _, _ = parse(path)
        if s.get("owner") != "ADU" or area_of.get(pid) not in IBERIA_AREAS:
            continue
        text = open(path, encoding="utf-8", errors="surrogateescape").read()
        m = re.search(r"^867\.1\.1 = \{(.*?)^\}", text, re.M | re.S)
        blk = m.group(1) if m else ""
        if "add_claim = ASU" not in blk or "add_claim = NAV" not in blk:
            bad_rec.append(str(pid))
    note(not bad_rec, f"andalusi iberia carries asu+nav claims ({len(bad_rec)} missing)")
    for b in bad_rec[:10]:
        print("        " + b)

    print()
    print("== vanilla tag reuse is deliberate ==")
    VANILLA_REUSE = frozenset(
        "ADU ALG ARB ARM ASU BAV BOH BRI BUL BYZ CRO CRT CRN DAL DAN DAU EGY ENG EST FIN FRA GAL "
        "GBR GER GMA GOT HLR HSA HUN ICE IRE ITA KIE KRA KRL KUR LIT LOI LOT LVA MAI MLK MOR MZB NAP NAV NOR NOV PAP PLT POL POM PRU PRO ROM RUG SAR "
        "SIL SCA SCO SER SIC SLZ SPA CAS ARA POR VAL SMI SOR SRV STE SWE SWA THU TNG TRA TRP TUN VEN VOL WLS WOL NAJ HDR MHR OMA JAP "
        "TIM KHO AFG TRS KSH TOU GUY FLA NRM HOL HAM KOL TRI TUS SPL ANU RYU MAK ALO ETH ADA NUB BNG ASS ORI CEY NPL MLB MUL MAD TNJ KMN GDW RTT SBP KGR BST YOR SND LWA CHA ARK HSE PEG AVA SUK KHM MTR SUN KUT BNJ TDO DGL KED BEU PAH BLI BEI MRI TER TID SUL MGD LNO PGS BTU LUW BRS KAN WGD KBU JOL KNG NUP MBA MLI PTE SMB MNS ULS MTH DMS ORD LEI KRY MDI DAM HOB KAZ PRM GUG PHA CDL PGR LIG VIE LUA BPR TAB YEM TFL MON HRZ KBO AIR ASH SON BON GUR ADA WLY SOA PAT TIB UTS KAM BHU LDK JIN SLL KOR BRT MGE SIB DAI".split()    )

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
    clash = [
        t for t in KEPT_REALMS | FORMABLE_TAGS
        if t in vtags and t not in VANILLA_REUSE
    ]
    note(not clash, f"no accidental vanilla tag reuse ({', '.join(sorted(clash)) or 'none'})")

    print("\n== custom tags registered ==")

    cdata = json.load(open(str(CACHE / "provdata.json")))
    # every tag - vanilla-reused and formable included - ships its own flag in the mod;
    # the base game's flags are never a fallback
    noflag = sorted(
        t for t in {x.tag for x in _REALMS} | set(FORMABLE_TAGS)
        if not os.path.exists(os.path.join(MOD, "gfx", "flags", f"{t}.tga"))
    )
    note(not noflag, "every tag has its own flag in the mod (vanilla flags never count)"
         + (f" (missing: {', '.join(noflag)})" if noflag else ""))
    import placeholder_flags  # noqa: E402

    ph = placeholder_flags.placeholders()
    if ph:
        print(f"  WARN {len(ph)} placeholder flags (colour and black diagonal) still to replace: {', '.join(ph)}")

    done = set()
    from eu4 import VANILLA_FORMATION_FILES  # noqa: E402

    supp_files = {
        k: open(
            os.path.join(MOD, "decisions", fn),
            encoding="utf-8",
            errors="replace",
        ).read()
        for fn, keys in VANILLA_FORMATION_FILES.items()
        for k in keys
    }
    for t in _REALMS:
        if not t.forms or t.forms in done:
            continue
        done.add(t.forms)
        starters = [s for s in _REALMS if s.forms == t.forms]
        fb = BY_FORMABLE[t.forms]
        key = t.decision
        land = {int(pid) for a in fb.areas for pid in cdata["areas"].get(a, ())}
        land |= set(fb.provinces)
        trig = open(
            os.path.join(
                MOD, "common", "scripted_triggers", "KarolingianFormations.txt"
            ),
            encoding="utf-8",
            errors="replace",
        ).read()
        blk = re.search(
            re.escape(key) + r"_provinces_trigger = \{(.*?)\n\}",
            trig,
            re.S,
        )
        body = blk.group(1) if blk else ""
        required = {int(x) for x in re.findall(r"province_id = (\d+)", body)}
        for a in re.findall(r"^\s*area = (\w+)", body, re.M):
            required |= {int(x) for x in cdata["areas"].get(a, ())}
        note(
            required == land,
            f"{key} requires exactly the {len(land)} {fb.name} provinces",
        )
        if required != land:
            print(f"        only in decision : {sorted(required - land)}")
            print(f"        only in the land : {sorted(land - required)}")
        dec = open(
            os.path.join(MOD, "decisions", f"Form{t.forms}.txt"),
            encoding="utf-8",
            errors="replace",
        ).read()
        note(
            f"change_tag = {t.forms}" in dec,
            f"{key} changes the tag to {t.forms}",
        )
        if fb.culture_group:
            note(
                all(f"culture_group = {g}" in dec for g in fb.culture_group),
                f"{key} is group-gated on {', '.join(fb.culture_group)}",
            )
        elif fb.culture:
            note(
                all(f"primary_culture = {c}" in dec for c in fb.culture.split()),
                f"{key} is culture-gated on {' or '.join(fb.culture.split())}",
            )
        else:
            note(
                all(f"tag = {s.tag}" in dec for s in starters),
                f"{key} is gated on its starters",
            )
        if fb.exclusive:
            missing = [
                f"{s.tag} fires while {o.tag} lives"
                for s in starters
                for o in starters
                if o != s and f"NOT = {{ exists = {o.tag} }}" not in dec
            ]
            note(not missing, f"{key} is exclusive between starters")
            for b in missing[:4]:
                print("        " + b)
        val = re.search(r"num_of_owned_provinces_with = \{\s*value = (\d+)", dec)
        exp = required_count(len(land), fb.percent)
        note(
            bool(val) and int(val.group(1)) == exp,
            f"{key} enacts at {exp} of {len(land)} provinces"
            + (f" ({fb.percent}%)" if fb.percent else ""),
        )
        if fb.own_capital:
            note(
                fb.capital in land,
                f"{fb.name} capital {fb.capital} is inside the requirement land",
            )
            note(
                f"owns = {fb.capital}" in dec,
                f"{key} requires holding the capital ({fb.capital})",
            )
        if fb.home_capital:
            note(
                f"{key}_capital_trigger = yes" in dec,
                f"{key} requires a homeland capital",
            )
            cblk = re.search(
                re.escape(key) + r"_capital_trigger = \{(.*?)\n\}",
                trig,
                re.S,
            )
            cbody = cblk.group(1) if cblk else ""
            creq = {int(x) for x in re.findall(r"province_id = (\d+)", cbody)}
            for a in re.findall(r"^\s*area = (\w+)", cbody, re.M):
                creq |= {int(x) for x in cdata["areas"].get(a, ())}
            note(
                creq == land,
                f"{key} capital trigger covers exactly the {len(land)} provinces",
            )
        if fb.rank_required == -1:
            note("government_rank" not in dec.split("allow = {")[0],
                 f"{key} carries no rank gate (rank_required = -1)")
        elif fb.rank_required:
            note(
                f"government_rank = {fb.rank_required}" in dec,
                f"{key} needs rank {fb.rank_required}",
            )
        elif fb.rank == 3:
            note(
                "NOT = { government_rank = 3 }" in dec,
                f"{key} needs a non-kingdom firer",
            )
        for culture, stag, name, prov in fb.renames:
            trig = (f"tag = {stag}" if stag else f"owns = {prov}" if prov
                    else f"primary_culture = {culture}")
            note(
                trig in dec and f"override_country_name = {name}" in dec,
                f"{key} renames to {name} for {trig}",
            )
        for sk in sorted({k for s in starters for k in s.suppress}):
            pat = re.escape(sk) + r"\s*=\s*\{\s*potential\s*=\s*\{\s*always\s*=\s*no"
            note(
                sk in supp_files and bool(re.search(pat, supp_files[sk])),
                f"vanilla {sk} decision neutralized in its own file",
            )

    print("\n== events carry no tag references ==")
    from eu4 import event_mentions_tag, split_event_blocks, all_known_tags  # noqa: E402

    tagset = all_known_tags()
    vdir = os.path.join(GAME, "events")
    vanilla_events = {fn for fn in os.listdir(vdir) if fn.endswith(".txt")}
    edir = os.path.join(MOD, "events")
    n_files, dirty = 0, []
    for fn in sorted(os.listdir(edir)):
        if not fn.endswith(".txt") or fn not in vanilla_events:
            continue
        n_files += 1
        text = open(os.path.join(edir, fn), encoding="utf-8", errors="replace").read()
        for kind, lines in split_event_blocks(text):
            if kind == "event" and event_mentions_tag("\n".join(lines), tagset):
                dirty.append(fn)
                break
    note(not dirty, f"no tag-specific events in {n_files} files ({len(dirty)} dirty)")
    for b in dirty[:10]:
        print("        " + b)

    print("\n== decisions carry no tag references ==")
    from eu4 import split_decision_blocks, VANILLA_FORMATION_FILES  # noqa: E402

    vddir = os.path.join(GAME, "decisions")
    vanilla_decs = {fn for fn in os.listdir(vddir) if fn.endswith(".txt")}
    ddir = os.path.join(MOD, "decisions")
    n_files, dirty = 0, []
    for fn in sorted(os.listdir(ddir)):
        if not fn.endswith(".txt") or fn not in vanilla_decs:
            continue
        if fn in VANILLA_FORMATION_FILES:
            continue
        n_files += 1
        text = open(os.path.join(ddir, fn), encoding="utf-8", errors="replace").read()
        for kind, key, lines in split_decision_blocks(text):
            if kind == "decision" and event_mentions_tag("\n".join(lines), tagset):
                dirty.append(f"{fn}:{key}")
                break
    note(not dirty, f"no tag-specific decisions in {n_files} files ({len(dirty)} dirty)")
    for b in dirty[:10]:
        print("        " + b)

    print("\n== vanilla HRE electorate decisions stubbed dead ==")
    from eu4 import VANILLA_STUB_DECISION_FILES  # noqa: E402

    for fn, keys in sorted(VANILLA_STUB_DECISION_FILES.items()):
        text = open(
            os.path.join(ddir, fn), encoding="utf-8", errors="replace"
        ).read()
        dead = [
            k
            for k in keys
            if re.search(rf"^\s*{k}\s*=\s*\{{", text, re.M)
            and re.search(r"^\s*always\s*=\s*no", text, re.M)
        ]
        note(
            len(dead) == len(keys),
            f"{fn} stubbed dead ({len(dead)}/{len(keys)})",
        )

    print("\n== custom script has no per-pid limit blocks ==")
    # A bare `PID = { ... }` effect block takes no `limit` child (the
    # engine rejects it and drops surrounding effects): condition province
    # work with `if = { limit = { PID = { ... } } }` (Brazil pattern) and
    # keep area scopes (which do take limits) for the rest. Only our own
    # files can carry the bug: vendored vanilla files stay byte-identical.
    import glob as _glob

    def _mod_only(subdir, vanilla_dir):
        vanilla = {
            fn for fn in os.listdir(vanilla_dir) if fn.endswith(".txt")
        }
        return sorted(
            p
            for p in _glob.glob(os.path.join(MOD, subdir, "*.txt"))
            if os.path.basename(p) not in vanilla
        )

    scope_bad = []
    for path in (
        _mod_only("events", os.path.join(GAME, "events"))
        + _mod_only("common/scripted_effects", os.path.join(GAME, "common", "scripted_effects"))
        + _mod_only("common/on_actions", os.path.join(GAME, "common", "on_actions"))
    ):
        text = open(path, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"(?m)^\t*(\d+) = \{$", text):
            depth, i = 1, m.end()
            while depth > 0 and i < len(text):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                i += 1
            inner, d = text[m.end() : i], 0
            for ln in inner.splitlines():
                code = ln.split("#", 1)[0]
                if d == 0 and re.match(r"^\s*limit\s*=", code):
                    scope_bad.append(
                        f"{os.path.basename(path)}:{m.group(1)}"
                    )
                    break
                d += code.count("{") - code.count("}")
    note(not scope_bad, f"no per-pid limits in {len(scope_bad)} blocks ({len(scope_bad)} bad)")
    for b in scope_bad[:10]:
        print("        " + b)

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

    for t in sorted(KEPT_REALMS):
        if t in DORMANT:
            continue
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
    for t in sorted(KEPT_REALMS):
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

    LOC = os.path.join(MOD, "localisation")
    print("\n== localisation files load ==")
    for root, _dirs, files in os.walk(LOC):
        for fn in sorted(files):
            if not fn.endswith("_l_english.yml"):
                continue
            raw = open(os.path.join(root, fn), "rb").read()
            rel = os.path.relpath(os.path.join(root, fn), MOD)
            note(raw.startswith(b"\xef\xbb\xbf"), f"{rel} starts with a UTF-8 BOM")
            # A headerless file segfaults the loc parser at startup
            # (SLanguageData::AddKeyValuePair -> LocalizeYmlAddKey, no
            # language registered): the l_english: line must come first.
            body = raw[3:].decode("utf-8", errors="replace")
            head = next((ln for ln in body.splitlines()
                         if ln.strip() and not ln.strip().startswith("#")), "")
            note(head.strip() == "l_english:",
                 f"{rel} declares the l_english: header first (got {head.strip()!r})"
                 if head.strip() != "l_english:" else f"{rel} declares l_english: first")

    print("\n== loc values use glyphs EU4 renders ==")
    # EU4's text pipeline drops any character its font set lacks (error.log
    # "Couldn't find Latin1 character" e.g. the CK3 macrons a-ogonek
    # title rows) while still rendering vanilla's Polish/Celtic marks, so
    # the honest baseline is the glyph set vanilla English loc itself uses.
    ALLOWED = {
        chr(c) for c in range(0x20, 0x7F)
    } | {
        chr(c) for c in range(0xA0, 0x100)
    }
    vdir = os.path.join(
        GAME,
        "localisation")
    for fn in sorted(os.listdir(vdir)):
        if not fn.endswith("_l_english.yml"):
            continue
        raw = open(os.path.join(vdir, fn), "rb").read()
        try:
            txt = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            txt = raw.decode("cp1252", errors="replace")
        ALLOWED |= set(txt)   # chars directly, not findall chunks
    ALLOWED |= {chr(c) for c in range(0x20, 0x7F)}
    # e-ogonek: beyond vanilla's set? proven rendered either way (never
    # logged as dropped with our Polish names live); keep it allowed so the
    # check measures what drops, not what lotr-writers used.
    ALLOWED |= set("ę")   # e-ogonek: renders (never logged, our Polish names live)
    ALLOWED |= set("Ł")   # capital L-stroke: renders the same way (no log drops)
    bad_glyph = []
    for root, _dirs, files in os.walk(LOC):
        for fn in sorted(files):
            if not fn.endswith("_l_english.yml"):
                continue
            for ln in open(os.path.join(root, fn), encoding="utf-8-sig").read().splitlines():
                if '"' not in ln:
                    continue
                val = ln.split('"')[1]
                bad = [c for c in val if c not in ALLOWED]
                if bad:
                    bad_glyph.append(
                        f"{fn}: {val.strip()!r} "
                        f"(unrenderable: {''.join(bad)!r} - the game drops "
                        f"the string, see error.log 'Couldn't find Latin1 "
                        f"character'; fold via encname)")
    note(not bad_glyph,
         f"all loc glyphs render ({len(bad_glyph)} bad)"
         if bad_glyph else "all loc glyphs render")
    for b in bad_glyph[:8]:
        print("        " + b)

    print("\n== formables carry their loc ==")
    allloc = ""
    for root, _dirs, files in os.walk(LOC):
        for fn in files:
            if fn.endswith("_l_english.yml"):
                allloc += open(os.path.join(root, fn),
                               encoding="utf-8-sig").read() + "\n"

    def has_loc(key):
        return re.search(rf"(?m)^ {re.escape(key)}:\d* ", allloc) is not None

    dkeys = sorted({t.decision for t in _REALMS if getattr(t, "decision", None)})
    missing = [f"{k}{suf}" for k in dkeys for suf in ("_title", "", "_desc")
               if not has_loc(f"{k}{suf}")]
    note(not missing, "every formation decision has title, name and desc loc"
         + (f" (missing: {', '.join(missing)})" if missing else ""))
    gameloc = ""
    gdir = os.path.join(GAME, "localisation")
    for fn in os.listdir(gdir):
        if fn.endswith("_l_english.yml"):
            gameloc += open(os.path.join(gdir, fn),
                            encoding="utf-8-sig").read() + "\n"
    unnamed = [f"{t}{suf}" for t in sorted(FORMABLE_TAGS) for suf in ("", "_ADJ")
               if not has_loc(f"{t}{suf}")
               and not re.search(rf"(?m)^ {t}{suf}:\d* ", gameloc)]
    note(not unnamed, "every formable tag has its name and adjective loc (ours or the base game's)"
         + (f" (missing: {', '.join(unnamed)})" if unnamed else ""))

    unnamed_landed = [f"{t}{suf}" for t in sorted(TAGS) for suf in ("", "_ADJ")
                      if not has_loc(f"{t}{suf}")
                      and not re.search(rf"(?m)^ {t}{suf}:\d* ", gameloc)]
    note(not unnamed_landed, "every landed tag has its name and adjective loc (ours or the base game's)"
         + (f" (missing: {', '.join(unnamed_landed)})" if unnamed_landed else ""))

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

    print("\n== interface religion-strip overrides stay in sync ==")
    max_icon = max(
        int(n)
        for n in re.findall(
            r"(?m)^\t\ticon = (\d+)",
            open(
                os.path.join(MOD, "common", "religions", "00_religion.txt"),
                encoding="utf-8",
                errors="replace",
            ).read(),
        )
    )
    REL_SPRITES = {
        "countryview.gfx": [
            "GFX_icon_religion",
            "GFX_country_icon_religion",
            "GFX_icon_religion_small",
        ],
        "ledger.gfx": ["GFX_religion_icon_strip"],
        "provinceview.gfx": ["GFX_province_view_religion"],
    }
    gfx_bad = []
    missing_strips = set()
    for fn, want in REL_SPRITES.items():
        vtext = open(
            os.path.join(GAME, "interface", fn), encoding="utf-8", errors="replace"
        ).read()
        mtext = open(os.path.join(MOD, "interface", fn), encoding="utf-8").read()
        vspr = re.findall(r'name = "(GFX_[^"]+)"', vtext)
        mspr = re.findall(r'name = "(GFX_[^"]+)"', mtext)
        if vspr != mspr:
            gfx_bad.append(f"{fn} sprite list drifted")
        for spr in want:
            m = re.search(
                r'name = "' + spr + r'".*?texturefile = "([^"]+)"',
                mtext,
                re.S,
            )
            if not m or not m.group(1).endswith(".dds"):
                gfx_bad.append(f"{fn} {spr} not pointed at our DDS strip")
                continue
            rel = re.split(r"[\\/]+", m.group(1))[-1]
            full = os.path.join(MOD, "gfx", "interface", rel)
            if not os.path.exists(full):
                # the strips are images, made by a local `faiths.py icons` run; a package
                # built from the text alone has none
                missing_strips.add(rel)
                continue
            with open(full, "rb") as fh:
                head = fh.read(24)
            import struct as _st

            w = _st.unpack("<I", head[16:20])[0] if head[:4] == b"DDS " else 0
            if w % max_icon or w // max(1, max_icon) not in (64, 32):
                gfx_bad.append(f"{fn} {spr} strip width {w} != {max_icon} frames")
            f = re.search(
                r'name = "' + spr + r'".*?noOfFrames = (\d+)', mtext, re.S
            )
            if not f or int(f.group(1)) != max_icon:
                gfx_bad.append(f"{fn} {spr} frames != {max_icon}")
    note(not gfx_bad, f"religion icon overrides intact ({len(gfx_bad)} bad)")
    if missing_strips:
        warn("religion icon strips not built here: " + ", ".join(sorted(missing_strips)))
    for b in gfx_bad[:8]:
        print("        " + b)

    print("\n== government rank strip matches the rank count ==")
    rank_bad = []
    mgfx = open(os.path.join(MOD, "interface", "countrydiplomacyview.gfx")).read()
    vgfx = open(
        os.path.join(GAME, "interface", "countrydiplomacyview.gfx"),
        encoding="utf-8",
        errors="replace",
    ).read()
    if re.findall(r'name = "(GFX_[^"]+)"', vgfx) != re.findall(
        r'name = "(GFX_[^"]+)"', mgfx
    ):
        rank_bad.append("countrydiplomacyview.gfx sprite list drifted")
    f = re.search(
        r'name = "GFX_government_rank_strip".*?noOfFrames = (\d+)', mgfx, re.S
    )
    want = 5 if os.path.exists(os.path.join(MOD, "gfx", "interface", "government_rank_strip.dds")) else 3
    if not f or int(f.group(1)) != want:
        rank_bad.append(f"GFX_government_rank_strip frames != {want} (county..hegemony)")
    dds = os.path.join(MOD, "gfx", "interface", "government_rank_strip.dds")
    if os.path.exists(dds):
        with open(dds, "rb") as fh:
            head = fh.read(24)
        import struct as _st2

        w = _st2.unpack("<I", head[16:20])[0] if head[:4] == b"DDS " else 0
        if w != 200:
            rank_bad.append(f"government_rank_strip width {w} != 5x40 frames")
    else:
        warn("government_rank_strip.dds not built here (an image: made locally); ranks keep the base game's 3 icons")
    note(not rank_bad, f"rank strip intact ({len(rank_bad)} bad)")
    for b in rank_bad[:8]:
        print("        " + b)

    print("\n== every religion key exists in vanilla or our additions ==")
    vrel = set(
        re.findall(
            r"(?m)^\s*([a-z_]+)\s*=\s*\{",
            open(
                os.path.join(GAME, "common", "religions", "00_religion.txt"),
                encoding="utf-8",
                errors="replace",
            ).read(),
        )
    )
    own_rel = os.path.join(MOD, "common", "religions", "00_religion.txt")
    if os.path.exists(own_rel):
        vrel |= set(
            re.findall(
                r"(?m)^\s*([a-z_]+)\s*=\s*\{",
                open(own_rel, encoding="utf-8", errors="replace").read(),
            )
        )
    bad_rel = []
    for fn in sorted(os.listdir(PDIR)):
        if not fn.endswith(".txt"):
            continue
        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        text = open(
            os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
        ).read()
        for rel in set(re.findall(r"^\s*religion\s*=\s*(\w+)", text, re.M)):
            if rel not in vrel:
                bad_rel.append(f"{m.group(1)} {rel}")
    note(not bad_rel, f"all province religions are real keys ({len(bad_rel)} bad)")
    for b in bad_rel[:8]:
        print("        " + b)

    print("\n== subject types keep CK3-true vassal ranks ==")
    # The mod ships an exact-filename copy of vanilla subject_types with one
    # gameplay edit: vassal max_government_rank 1 -> 0. The engine
    # (CCountry::CalcGovernmentRank) clamps a subject's displayed rank down to
    # its subject type's cap; our CK3-true vassal duchies (TRA/VSG/GTH/DAL/
    # SIQ/CST/ARG/PRT) must read as Duchy, and personal_union/tributary_state
    # inherit the default (no limit). Re-copy the file on patches, keep the
    # vassal line flipped.

    def _code_lines(p):
        txt = open(p, encoding="cp1252", errors="replace").read()
        return [
            l.split("#", 1)[0].strip()
            for l in txt.splitlines()
            if l.split("#", 1)[0].strip()
        ]

    vsub = _code_lines(os.path.join(GAME, "common", "subject_types",
                                    "00_subject_types.txt"))
    msub = _code_lines(os.path.join(MOD, "common", "subject_types",
                                    "00_subject_types.txt"))
    sdiff = [(a, b) for a, b in zip(vsub, msub) if a != b]
    # the mod's edits: the vassal rank cap, and vassals/marches adding less force limit to the overlord
    expected_sdiff = [
        ("max_government_rank = 1", "max_government_rank = 0"),
        ("forcelimit_to_overlord = 0.1", "forcelimit_to_overlord = 0.0"),
        ("forcelimit_to_overlord = 0.2", "forcelimit_to_overlord = 0.1"),
    ]
    note(
        len(vsub) == len(msub) and sdiff == expected_sdiff,
        "subject types = vanilla copy with only the vassal cap lifted and the vassal force limit cut",
    )
    if len(vsub) != len(msub) or len(sdiff) != 1:
        print(f"        {len(vsub)} vanilla vs {len(msub)} ours, "
              f"{len(sdiff)} code-line diffs: {sdiff[:4]}")

    print("\n== culture blocks sit at group depth ==")
    # A culture block nested inside another culture silently does nothing
    # in game (the carantanian bug): the engine reads cultures only at
    # group depth. Every culture the mod actually uses must own exactly
    # one depth-1 block. Same-name groups and cultures (frankish,
    # maghrebi) are the mod's own split-group pattern and are fine.
    from db import session as db_session
    from models import Culture as DbCulture

    _s2 = db_session()
    # every row keyed on a culture column, in any table
    used_cultures = set()
    for _tbl in [
        r[0]
        for r in _s2.execute(
            __import__("sqlalchemy").text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        )
    ]:
        _tabs = [
            r[1]
            for r in _s2.execute(
                __import__("sqlalchemy").text(f"PRAGMA table_info({_tbl})")
            )
        ]
        if "culture" in _tabs:
            used_cultures |= {
                c  # formables.culture may list several cultures
                for r in _s2.execute(
                    __import__("sqlalchemy").text(
                        f"SELECT DISTINCT culture FROM {_tbl} WHERE culture IS NOT NULL"
                    )
                )
                for c in r[0].split()
            }
    _s2.close()
    for fn in sorted(os.listdir(PDIR)):
        if fn.endswith(".txt"):
            for c in re.findall(
                r"(?m)^\s*culture\s*=\s*([a-z_0-9]+)",
                open(os.path.join(PDIR, fn), encoding="utf-8", errors="replace").read(),
            ):
                used_cultures.add(c)
    cpath = os.path.join(MOD, "common", "cultures", "00_cultures.txt")
    openers = []  # (key, depth) for every block opener, comments stripped
    _depth = 0
    for ln in open(cpath, encoding="utf-8", errors="replace").read().splitlines():
        code = ln.split("#", 1)[0]
        m = re.match(r"\s*([A-Za-z_0-9]+)\s*=\s*\{", code)
        if m:
            openers.append((m.group(1), _depth))
        _depth += code.count("{") - code.count("}")
    # name lists and vanilla's country/province interaction blocks are
    # fields, never cultures
    FIELD_BLOCKS = frozenset(
        {"male_names", "female_names", "dynasty_names", "unit_names", "ship_names",
         "army_names", "fleet_names", "names_from_culture", "country", "province"}
    )
    bad_cult = [f"{k} nests at depth {d}" for k, d in openers
                if k not in FIELD_BLOCKS and d >= 2]
    for k in sorted(used_cultures):
        ds = [d for key, d in openers if key == k and d >= 1]
        if ds.count(1) != 1:
            bad_cult.append(
                f"{k} appears {len(ds)}x as a culture block (need exactly one depth-1 block)"
            )
    note(
        not bad_cult,
        f"all {len(used_cultures)} used cultures own exactly one depth-1 block"
        + ("" if not bad_cult else f" ({len(bad_cult)} bad)"),
    )
    for b in bad_cult[:12]:
        print("        " + b)

    print("\n== vanilla tech-group visibility survives everywhere ==")
    from eu4 import undated_group_visibility  # noqa: E402

    vis_bad = []
    for fn in sorted(os.listdir(PDIR)):
        if not fn.endswith(".txt"):
            continue
        m = re.match(r"^(\d+)", fn)
        if not m:
            continue
        ours = {
            ln.strip()
            for ln in open(
                os.path.join(PDIR, fn), encoding="utf-8", errors="surrogateescape"
            )
            if ln.strip().startswith("discovered_by")
        }
        for vfn in os.listdir(os.path.join(GAME, "history", "provinces")):
            if vfn == fn:
                want = undated_group_visibility(
                    open(
                        os.path.join(GAME, "history", "provinces", vfn),
                        encoding="utf-8",
                        errors="replace",
                    ).read()
                )
                missing = [ln for ln in want if ln.strip() not in ours]
                if missing:
                    vis_bad.append(f"{m.group(1)} drops {len(missing)}")
                break
    note(not vis_bad, f"no dropped tech-group discovery ({len(vis_bad)} bad)")
    for b in vis_bad[:8]:
        print("        " + b)

    print("\n== country history uses vanilla key shapes ==")
    # EU4's country-history parser rejects `general = {`/`advisor = {`
    # ("Unknown effect type" in error.log - the block silently vanishes;
    # generals are `leader = { type = general }`, advisors belong in
    # history/advisors/). Guarded because tags.extra is hand-written and
    # this killed ADU's 867 general silently once.
    badkey = []
    for fn in sorted(os.listdir(COUNTRY_OUT)):
        if not fn.endswith(".txt"):
            continue
        text = open(os.path.join(COUNTRY_OUT, fn),
                    encoding="cp1252", errors="replace").read()
        for m in re.finditer(r"(?m)^\s*(general|advisor)\s*=\s*\{", text):
            badkey.append(f"{fn}: {m.group(0).strip()}")
    note(not badkey, "no general/advisor keys in country history"
         if not badkey else
         f"{len(badkey)} wrong-key country-history blocks")
    for b in badkey[:8]:
        print("        " + b)

    print("\n== preset wars use live tags and real CBs ==")
    cbkeys = set(
        re.findall(
            r"(?m)^\s*(cb_[a-z_]+) = \{",
            open(
                os.path.join(GAME, "common", "cb_types", "00_cb_types.txt"),
                encoding="utf-8",
                errors="replace",
            ).read(),
        )
    )
    own_cb = os.path.join(MOD, "common", "cb_types")
    if os.path.isdir(own_cb):
        for fn in sorted(os.listdir(own_cb)):
            if fn.endswith(".txt"):
                cbkeys |= set(
                    re.findall(
                        r"(?m)^\s*((?:cb|kar)_[a-z_]+) = \{",
                        open(
                            os.path.join(own_cb, fn),
                            encoding="utf-8",
                            errors="replace",
                        ).read(),
                    )
                )
    livetags = {t.tag for t in _REALMS} | set(BY_TAG)
    war_bad = []
    wdir = os.path.join(MOD, "history", "wars")
    for fn in sorted(os.listdir(wdir)):
        if not fn.endswith(".txt"):
            continue
        wtext = open(os.path.join(wdir, fn), encoding="utf-8").read()
        for side in re.findall(
            r"add_(?:attacker|defender)\s*=\s*([A-Z]{3})", wtext
        ):
            if side not in livetags:
                war_bad.append(f"{fn}: dead side {side}")
        for cb in re.findall(r"casus_belli\s*=\s*(\w+)", wtext):
            if cb not in cbkeys:
                war_bad.append(f"{fn}: unknown CB {cb}")
    note(not war_bad, f"preset wars are firable ({len(war_bad)} bad)")
    for b in war_bad[:8]:
        print("        " + b)

    print("\n== generated file names match base-game shapes ==")
    from eu4 import vanilla_prov_file  # noqa: E402

    # Vanilla replaces whole directories with nothing (replace_path),
    # but per-file it merges: history files that vanish from our tree
    # reappear in the vanilla copy, and same-content files union. A name
    # that drifts from the base game's exact filename therefore leaks
    # vanilla content back in - the check below has bitten twice (2018's
    # renaming races left stale display names behind, and a country file
    # registered under a hand-picked name for a vanilla-reused tag once
    # coexisted with the vanilla copy).
    prov_bad = []
    for fn in sorted(os.listdir(PDIR)):
        m = re.match(r"^(\d+)", fn)
        if not m:
            prov_bad.append(f"{fn}: not pid-prefixed")
            continue
        van = vanilla_prov_file(int(m.group(1)))
        if van is None:
            prov_bad.append(f"{fn}: no vanilla province with this pid")
        elif os.path.basename(van) != fn:
            prov_bad.append(f"{fn}: vanilla's file is '{os.path.basename(van)}'")
    note(
        not prov_bad,
        f"province files ride vanilla's names ({len(prov_bad)} off)",
    )
    for b in prov_bad[:8]:
        print("        " + b)

    # Generated country files follow eu4's rule: keep vanilla's exact
    # filename when the tag is a vanilla reuse (else the vanilla copy's
    # OTL history merges back), else '<TAG> - <country_file>.txt'. HLR
    # has no db row - it is formed in-game and its file is neutralized.
    from eu4 import hist_name  # noqa: E402

    want = {t.tag: hist_name(t) for t in _REALMS}
    want["HLR"] = "HLR - Holy Roman Empire.txt"
    cdir = COUNTRY_OUT
    cfiles = [fn for fn in os.listdir(cdir) if fn.endswith(".txt")]
    cty_bad = []
    for fn in cfiles:
        tag = fn.split(" - ", 1)[0]
        if tag not in want:
            cty_bad.append(f"{fn}: {tag} is no tag here")
        elif fn != want[tag]:
            cty_bad.append(f"{fn}: should be '{want[tag]}'")
    note(
        not cty_bad,
        f"country files follow eu4's naming ({len(cty_bad)} off)",
    )
    for b in cty_bad[:8]:
        print("        " + b)
    missing = [want[t] for t in sorted(want) if want[t] not in cfiles]
    note(
        not missing,
        f"every tag has its country file ({len(missing)} missing)",
    )
    for b in missing[:8]:
        print("        " + b)

    print("\n== Christian rite schools (tools/rites.py) ==")
    import rites

    rite_err, rite_warn = rites.verify()
    note(not rite_err, f"rite schools verified against CK3, vanilla and history ({len(rite_err)} problems)")
    for e in rite_err:
        print("        " + e)
    for w in rite_warn:
        warn(w)

    print("\n== tags reach their culture's title ladder (tools/govnames.py) ==")
    import govnames

    gn_miss = govnames.misses([(t.tag, t.culture) for t in _tagrows])
    note(not gn_miss, f"every tag passes the gate of its culture's government_names block ({len(gn_miss)} fall through)")
    for t, c, b in gn_miss[:20]:
        print(f"        {t}: culture {c} has a dedicated block but the tag lands on {b} "
              f"(run tools/culturetitles.py {t} to add a block gated on its government)")

    import culturalnames
    import tagloc

    tl_drift = tagloc.drift()
    note(not tl_drift, f"every tag's name and adjective is what tools/tagloc.py lifts from CK3 ({len(tl_drift)} stale - run the build)")
    for t, have, want in tl_drift[:20]:
        print(f"        {t}: {have} but CK3 gives {want}")

    ppl = culturalnames.people_drift([(t.tag, t.ck3_title, t.rank) for t in _tagrows if t.ck3_title])
    note(not ppl, f"steppe counties carry their people's name ({len(ppl)} missing)")
    for tg_, have, want in ppl[:20]:
        print(f"        {tg_}: {have!r} should be {want!r} (python3 tools/culturalnames.py peoples)")

    print("\n== religion groups follow CK3's religions (tools/faiths.py) ==")
    import faiths as _faiths

    gm = _faiths.group_misfits()
    note(not gm, f"every lifted religion sits in the group of its CK3 religion ({len(gm)} off)")
    for k, have, want in gm[:12]:
        print(f"        {k} is in {have} but CK3 files it under {want}")

    print("\n== cultures and religions are CK3's (tools/cultures.py, tools/religions.py) ==")
    import cultures as _cultures
    import religions as _religions

    not_ck3 = sorted(c for c in _cultures.used_in_db() if _cultures.group_of(c) is None)
    note(not not_ck3, f"every culture in use is a CK3 culture ({len(not_ck3)} are not)")
    for c in not_ck3[:12]:
        print(f"        {c}")
    no_block = sorted(f for f in _religions.used_faiths() if f not in _religions.TEMPLATE)
    note(not no_block, f"every religion in use is a CK3 faith the file has a block for ({len(no_block)} lack one)")
    for f in no_block[:12]:
        print(f"        {f}")

    print("\n== province religions track CK3's counties (tools/provfaiths.py) ==")
    import provfaiths

    pf_err, pf_warn = provfaiths.verify()
    note(not pf_err, f"audited province religions match CK3 ({len(pf_err)} off, {len(provfaiths.PROVINCE_COUNTY)} audited)")
    for e in pf_err[:20]:
        print("        " + e)
    for w in pf_warn:
        warn(w)

    print("\n" + ("ALL CHECKS PASSED" if not fail else f"{len(fail)} FAILURES"))

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(run())
