#!/usr/bin/env python3
"""Start-date relations: subjects, relation slots, CK3 lieges, friendships, subject types and the preset wars."""

import os
import re
from checks.report import note
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
        f"{t}: {n} relations, limit {_limit(BY_TAG[t].rank)} (rank {BY_TAG[t].rank})"
        for t, n in sorted(used.items())
        if t in BY_TAG and n > _limit(BY_TAG[t].rank)
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
    tight = [f"{t} {n}/{_limit(BY_TAG[t].rank)}" for t, n in sorted(used.items())
             if t in BY_TAG and n == _limit(BY_TAG[t].rank)]
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


def run() -> None:
    subjects_and_relation_limit()
    vassalage_matches_ck3_s_867_lieges()
    historical_friendships_and_rivalries()
    subject_types_keep_ck3_true_vassal_ranks()
    preset_wars_use_live_tags_and_real_cbs()
