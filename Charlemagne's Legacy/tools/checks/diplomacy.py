#!/usr/bin/env python3
"""Start-date relations: subjects, relation slots, CK3 lieges, friendships, subject types and the preset wars."""

import os
import re
from checks.report import note
from tagdb import DIPLOMACY
from checks.context import BY_TAG, CACHE, GAME, MOD, _REALMS, country_path


def subjects_and_relation_limit() -> None:
    """Starting subjects; no tag starts over its diplomatic relation limit."""
    print("\n== starting subjects ==")
    dip = os.path.join(MOD, "history", "diplomacy", "karolingian_vassals.txt")
    raw_dip = open(dip, encoding="cp1252", errors="replace").read()
    found = list(
        zip(
            re.findall(r"first\s*=\s*([A-Z]{3})", raw_dip),
            re.findall(r"second\s*=\s*([A-Z]{3})", raw_dip),
        )
    )
    from marriages import all_relations  # noqa: E402

    expected_dip = [(d.liege, d.subject) for d in all_relations()]
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

    def _modifier_slots(tag):
        """diplomatic_upkeep that the tag's start-date country modifiers add (kar_caliphal_governors)."""
        extra = getattr(BY_TAG.get(tag), "extra", "") or ""
        total = 0
        for name in re.findall(r"add_country_modifier\s*=\s*\{[^}]*?name\s*=\s*(\w+)", extra):
            for fn in os.listdir(os.path.join(MOD, "common", "event_modifiers")):
                mb = _blocks(_read(f"common/event_modifiers/{fn}")).get(name)
                if mb:
                    m = re.search(r"(?m)^\s*diplomatic_upkeep\s*=\s*(-?\d+)", mb)
                    total += int(m.group(1)) if m else 0
        return total

    def _limit_of(tag):
        return _limit(BY_TAG[tag].rank) + _modifier_slots(tag)

    used = {}
    peers = set()  # an alliance and a royal marriage with the same country share one slot
    for d in all_relations():
        if d.relation in PEER_RELATIONS:
            peers.add(frozenset((d.liege, d.subject)))
        elif _takes_slot({"union": "personal_union"}.get(d.relation, d.relation)):
            used[d.liege] = used.get(d.liege, 0) + 1
    for pair in peers:
        for t in pair:
            used[t] = used.get(t, 0) + 1
    over = [
        f"{t}: {n} relations, limit {_limit_of(t)} (rank {BY_TAG[t].rank})"
        for t, n in sorted(used.items())
        if t in BY_TAG and n > _limit_of(t)
    ]
    from marriages import subjects_without_alliances  # noqa: E402

    stuck = sorted(
        f"{d.liege}/{d.subject} {d.relation}" for d in all_relations()
        if d.relation in PEER_RELATIONS
        and (d.liege in subjects_without_alliances() or d.subject in subjects_without_alliances())
    )
    note(not stuck, f"no vassal or union subject holds an alliance or marriage of its own ({len(stuck)} do)")
    for x in stuck:
        print("        " + x)
    note(not over, f"no tag starts over its diplomatic relation limit ({len(over)} over, base {base})")
    for o in over:
        print("        " + o)
    tight = [f"{t} {n}/{_limit_of(t)}" for t, n in sorted(used.items())
             if t in BY_TAG and n == _limit_of(t)]
    if tight:
        print("  WARN at the limit already (one more subject puts them over): " + ", ".join(tight))


def vassalage_matches_ck3_s_867_lieges() -> None:
    """Vassalage matches CK3's 867 lieges (tools/lieges.py)."""
    print("\n== vassalage matches CK3's 867 lieges (tools/lieges.py) ==")
    # An independent tag (and a tributary, which CK3 writes as `tributary_of`, never `liege =`) must have no liege in
    # CK3's 867 title history; a vassal, march or appanage must have exactly its overlord's realm as liege (a governor
    # folded into a tag counts as that tag; a union subject may instead share its overlord's ruler).
    from lieges import mismatches  # noqa: E402

    lg_bad = mismatches()
    note(not lg_bad, f"every tag's liege is what CK3 gives it at 867 ({len(lg_bad)} differ)")
    for tag, mod, ck in lg_bad:
        print(f"        {tag}: mod says {mod}, CK3 says {ck}")
    from lieges import governor_province_mismatches  # noqa: E402

    gp_bad = governor_province_mismatches()
    note(not gp_bad, "governor and realm provinces follow CK3's 867 vassal chains "
         f"({len(gp_bad)} off)")
    for pid, county, owner, want in gp_bad:
        print(f"        {pid} {county}: owned by {owner}, CK3 says {want}")


def lotharingian_partition_covers_lotharingia() -> None:
    """The Treaty of Meerssen event hands over exactly the provinces LOT owns, and its subjects go to the right kings."""
    print("\n== the partition of Lotharingia covers its realm (events/LotharingianPartition.txt) ==")
    txt = open(os.path.join(MOD, "events", "LotharingianPartition.txt"), encoding="cp1252").read()
    ceded = {side: set(map(int, re.findall(rf"(\d+) = \{{ limit = \{{ owned_by = ROOT \}} remove_core = ROOT cede_province = {side} add_core = {side} \}}", txt)))
             for side in ("FRA", "GER")}
    claimed = {}
    for ev, side in (("2", "FRA"), ("3", "GER")):
        body = txt.split(f"id = kar_lotharingia.{ev}\n", 1)[1].split("\ncountry_event", 1)[0]
        claimed[side] = set(map(int, re.findall(r"(\d+) = \{ limit = \{ owned_by = LOT \} add_permanent_claim = ROOT", body)))
    owned = set(BY_TAG["LOT"].provinces)
    note(ceded["FRA"] | ceded["GER"] == owned and not ceded["FRA"] & ceded["GER"],
         f"FRA and GER shares are LOT's {len(owned)} provinces, each given once "
         f"(FRA {len(ceded['FRA'])}, GER {len(ceded['GER'])})")
    for side in ("FRA", "GER"):
        note(claimed[side] == ceded[side], f"{side}'s claims are the share it gets at Meerssen")
    for ev, want in (("DAU", "FRA"), ("HOL", "GER"), ("KOL", "GER"), ("TRI", "GER")):
        in_ev = f"{want} = {{ vassalize = {ev} }}" in txt
        liege = [d.liege for d in DIPLOMACY if d.subject == ev]
        note(in_ev and liege == ["LOT"], f"{ev} is LOT's subject at the start and Meerssen hands it to {want}")


def historical_friendships_and_rivalries() -> None:
    """Historical friendships and rivalries."""
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


def subject_types_keep_ck3_true_vassal_ranks() -> None:
    """Subject types keep CK3-true vassal ranks."""
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
    msub_text = open(os.path.join(MOD, "common", "subject_types", "00_subject_types.txt"),
                     encoding="cp1252", errors="replace").read()
    # the mod's own subject types sit between BEGIN/END markers; everything outside them is vanilla's
    msub_text = re.sub(r"(?s)# BEGIN kar [^\n]*\n.*?# END kar [^\n]*\n", "", msub_text)
    _tmp = os.path.join(str(CACHE), "subject_types_without_ours.txt")
    open(_tmp, "w", encoding="cp1252").write(msub_text)
    msub = _code_lines(_tmp)
    sdiff = [(a, b) for a, b in zip(vsub, msub) if a != b]
    # the mod's edits: the vassal rank cap, and no subject type adding force limit, naval force limit,
    # manpower or sailors to its overlord
    MILITARY = ("forcelimit_to_overlord", "naval_forcelimit_to_overlord", "manpower_to_overlord",
                "sailors_to_overlord")

    def _allowed(a, b):
        if (a, b) == ("max_government_rank = 1", "max_government_rank = 0"):
            return True
        ka, _, va = a.partition(" = ")
        kb, _, vb = b.partition(" = ")
        return ka == kb and ka in MILITARY and vb.split("#")[0].strip() == "0.0"

    note(
        len(vsub) == len(msub) and all(_allowed(a, b) for a, b in sdiff),
        "subject types = vanilla copy with only the vassal cap lifted and every overlord bonus cut to 0",
    )
    ours = open(os.path.join(MOD, "common", "subject_types", "00_subject_types.txt"),
                encoding="cp1252", errors="replace").read()
    gives = [f"{k} = {v}" for k, v in re.findall(
        r"(?m)^\s*(%s)\s*=\s*([0-9.]+)" % "|".join(MILITARY), ours) if float(v) != 0.0]
    note(not gives, f"no subject type adds force limit or manpower to its overlord ({len(gives)} do)")


def preset_wars_use_live_tags_and_real_cbs() -> None:
    """Preset wars use live tags and real CBs."""
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


def subjects_have_the_right_subject_type() -> None:
    """Every subject relation uses the subject type its realm calls for."""
    print("\n== subjects have the right subject type ==")
    from marriages import all_relations  # noqa: E402
    from tagdb import PEER_RELATIONS  # noqa: E402

    # The rules, one per subject type. `vassal` is the default; a republic cannot be a vassal (Venice is
    # Byzantium's tributary); the theme type is Byzantium's alone (the Abbasid governors are ordinary
    # vassals); daimyo are Japan's; a union is the king's other crown; a tributary is a republic or one
    # of the realms CK3 itself marks as tribute-paying (Egypt to the Abbasids, Makuria to Egypt).
    TRIBUTARY = {("ARB", "EGY"), ("EGY", "MAK")}
    # a theme can hold themes of its own (Strymon's Thessalonika and Thessaly)
    byz_themes = {d.subject for d in all_relations() if d.relation == "theme_subject_type" and d.liege == "BYZ"}
    bad = []
    for d in all_relations():
        if d.relation in PEER_RELATIONS:
            continue
        sub = BY_TAG.get(d.subject)
        republic = bool(sub) and getattr(sub, "government", "") == "republic"
        want = None
        if republic:
            want = "tributary_state"
        elif d.relation == "theme_subject_type" and d.liege != "BYZ" and (d.liege not in byz_themes):
            want = "vassal"
        elif d.relation == "daimyo_vassal" and d.liege != "JAP":
            want = "vassal"
        elif d.relation == "tributary_state" and (d.liege, d.subject) not in TRIBUTARY:
            want = "vassal"
        if want and want != d.relation:
            bad.append(f"{d.liege}/{d.subject}: {d.relation}, should be {want}")
    note(not bad, f"every subject has the subject type its realm calls for ({len(bad)} wrong)")
    for b in bad:
        print("        " + b)


def force_limit_comes_from_provinces() -> None:
    """No flat base force limit: every country's land and naval force limit is its provinces' alone."""
    print("\n== force limit comes from the provinces ==")
    text = open(os.path.join(MOD, "common", "static_modifiers", "00_static_modifiers.txt"),
                encoding="cp1252", errors="replace").read()
    flat = []
    m = re.search(r"(?ms)^all_nations = \{(.*?)^\}", text)
    for k, v in re.findall(r"(?m)^\s*((?:land|naval)_forcelimit)\s*=\s*(-?[0-9.]+)", m.group(1) if m else ""):
        if float(v) != 0.0:
            flat.append(f"all_nations: {k} = {v}")
    m = re.search(r"(?ms)^subject_nation = \{(.*?)^\}", text)
    for k, v in re.findall(r"(?m)^\s*(\w+)\s*=\s*(-?[0-9.]+)", m.group(1) if m else ""):
        if float(v) != 0.0:
            flat.append(f"subject_nation: {k} = {v}")
    note(not flat, "no flat base force limit and no subject_nation malus"
         + (": " + ", ".join(flat) if flat else ""))


def vassals_cannot_be_integrated_at_the_start() -> None:
    """Every starting subject relation carries its creation date, and a vassal waits 50 years."""
    print("\n== subject status has a creation date ==")
    from tagdb import CTRY_DATE  # noqa: E402

    path = os.path.join(MOD, "history", "diplomacy", "karolingian_vassals.txt")
    text = open(path, encoding="cp1252", errors="replace").read()
    undated = []
    for m in re.finditer(r"(?m)^(vassal|union|dependency)\s*=\s*\{(.*?)^\}", text, re.S):
        if f"start_date = {CTRY_DATE}" not in m.group(2):
            f = re.search(r"first\s*=\s*(\w+)", m.group(2))
            s2 = re.search(r"second\s*=\s*(\w+)", m.group(2))
            undated.append(f"{f.group(1) if f else '?'}/{s2.group(1) if s2 else '?'}")
    note(not undated, f"every starting subject relation is dated {CTRY_DATE}"
         + (": " + ", ".join(undated[:8]) if undated else ""))
    defines = open(os.path.join(MOD, "common", "defines.lua"), encoding="cp1252", errors="replace").read()
    m = re.search(r"INTEGRATE_VASSAL_MIN_YEARS\s*=\s*(\d+)", defines)
    rp = re.search(r"LIBERTY_DESIRE_RELATIVE_POWER\s*=\s*([0-9.]+)", defines)
    note(rp is not None and float(rp.group(1)) == 37.5,
         f"relative army power pulls half as hard as the base game's 75 (defines say {rp.group(1) if rp else 'nothing'})")
    sub = open(os.path.join(MOD, "common", "subject_types", "00_subject_types.txt"), encoding="cp1252", errors="replace").read()
    cls = lambda name: (re.search(r"(?ms)^%s = \{[ \t]*\r?\n.*?relative_power_class\s*=\s*(\d+)" % name, sub) or [None, None])[1]
    tc = cls("theme_subject_type")
    note(tc is not None and int(tc) >= 2 and tc != cls("vassal"),
         f"themes weigh their army against the emperor's as a pool of their own (class {tc}, the vassals' is {cls('vassal')})")
    theme_base = re.search(r"(?ms)^theme_subject_type = \{.*?base_liberty_desire\s*=\s*(-?[0-9.]+)", sub)
    note(rp is not None and theme_base is not None
         and abs(float(theme_base.group(1)) + 0.9 * float(rp.group(1))) < 1e-6,
         "a theme's loyalty offset cancels 90% of the relative-power pull (it keeps a tenth of a vassal's): "
         f"base_liberty_desire {theme_base.group(1) if theme_base else None} vs -0.9 x "
         f"{rp.group(1) if rp else None}")
    note(m is not None and int(m.group(1)) == 50,
         f"a vassal can be integrated 50 years after its status was created (defines say {m.group(1) if m else 'nothing'})")


def run() -> None:
    subjects_and_relation_limit()
    vassalage_matches_ck3_s_867_lieges()
    lotharingian_partition_covers_lotharingia()
    historical_friendships_and_rivalries()
    subject_types_keep_ck3_true_vassal_ranks()
    subjects_have_the_right_subject_type()
    force_limit_comes_from_provinces()
    vassals_cannot_be_integrated_at_the_start()
    preset_wars_use_live_tags_and_real_cbs()
