#!/usr/bin/env python3
"""Tags: their ruler's culture and faith, flags, tech, sizes, capitals, registration and base-game reuse."""

import json
import os
import re
from collections import Counter
from checks.report import note
from checks.context import BY_FORMABLE, BY_TAG, CACHE, CAPS, DORMANT, FORMABLE_TAGS, GAME, GH, KEPT_REALMS, MOD, PROVINCES, TAGS, _REALMS, core_deny_map, country_path, effective, parse, province_files, required_count


def no_base_game_flag_is_reused() -> None:
    """No base-game flag is reused."""
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


def tag_tech_culture_faith_and_size() -> None:
    """Reuse tags keep vanilla tech; tags carry their ruler's culture and faith; realm sizes."""
    files = province_files()

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

    from steps.provdata import lake_ids, waste_ids

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

    from tagdb import SEED_CORES  # noqa: E402

    dormant = []
    for pid, path in files.items():
        s, _, _ = parse(path)
        o = s.get("owner")
        if not o:
            continue
        text = open(path, encoding="utf-8", errors="surrogateescape").read()
        for c in set(re.findall(r"(?m)^\s*add_core\s*=\s*([A-Z]{3})", text)):
            if c != o and c not in SEED_CORES.get(pid, ()):
                dormant.append(f"{pid} owned by {o} still cored by {c}")
    note(not dormant, f"no dormant cores: every province is cored by its owner alone, bar seeded releasables ({len(dormant)} problems)")
    for b in dormant[:8]:
        print("        " + b)

    print("\n== realm sizes ==")
    for t in TAGS:
        if t in DORMANT:
            note(own[t] == 0, f"{t} dormant (has {own[t]})")
            continue
        note(own[t] > 0, f"{t} owns {own[t]} provinces")
    note(own["HLR"] == 0, f"HLR owns 0 provinces (has {own['HLR']})")
    print(f"        new total = {sum(own[t] for t in TAGS)}")


def vanilla_tag_reuse_is_deliberate() -> None:
    print("== vanilla tag reuse is deliberate ==")
    VANILLA_REUSE = frozenset(
        "ADU ALG ARB ARM ASU BAV BOH BRI BUL BYZ CRO CRT CRN DAL DAN DAU EGY ENG EST FIN FRA GAL "
        "GBR GER GMA GOT HLR HSA HUN ICE IRE ITA KIE KRA KRL KUR LIT LOI LOT LVA MAI MLK MOR MZB NAP NAV NOR NOV PAP PLT POL POM PRU PRO ROM RUG SAR "
        "SIL SCA SCO SER SIC SLZ SPA CAS ARA POR VAL SMI SOR SRV STE SWE SWA THU TNG TRA TRP TUN VEN VOL WLS WOL NAJ HDR MHR OMA JAP "
        "TIM KHO AFG TRS KSH TOU GUY FLA NRM HOL HAM KOL TRI TUS SPL ANU RYU MAK ALO ETH ADA NUB BNG ASS ORI CEY NPL MLB MUL MAD TNJ KMN GDW RTT SBP KGR BST YOR SND LWA CHA ARK HSE PEG AVA SUK KHM MTR SUN KUT BNJ TDO DGL KED BEU PAH BLI BEI MRI TER TID SUL MGD LNO PGS BTU LUW BRS KAN WGD KBU JOL KNG NUP MBA MLI PTE SMB MNS ULS MTH DMS ORD LEI KRY MDI DAM HOB KAZ PRM GUG PHA CDL PGR LIG VIE LUA BPR TAB YEM TFL MON HRZ KBO AIR ASH SON BON GUR ADA WLY SOA PAT TIB UTS KAM BHU LDK JIN SLL KOR BRT MGE SIB DAI MAG ULM OPL KOI ALS".split()    )

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


def custom_tags_registered() -> None:
    """Custom tags registered."""
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
    from steps.vanilla_scripts import VANILLA_FORMATION_FILES

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


def realm_holds_its_own_capital() -> None:
    """Every realm holds its own capital."""
    files = province_files()

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


def tag_capital_agrees_with_country_file() -> None:
    """Tag.capital agrees with the country file."""
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


def run() -> None:
    no_base_game_flag_is_reused()
    tag_tech_culture_faith_and_size()
    vanilla_tag_reuse_is_deliberate()
    custom_tags_registered()
    realm_holds_its_own_capital()
    tag_capital_agrees_with_country_file()
