---
name: cl-subjects
description: Vassals, governors, unions, tributaries, alliances and royal marriages in Charlemagne's Legacy - the diplomacy table, subject types, relation-slot limits, the CK3 liege check, and the Byzantine/Abbasid governor pattern.
---

# Subjects and relations

Tasks this covers: make a tag a vassal / union subject / tributary / governor of another; add an alliance or royal marriage;
find why a tag is over its relation limit; check lieges against CK3. Steps: decide from CK3 (the liege chain), insert the
`diplomacy` row, then `build.py` and `validate.py` and read "starting subjects", "no tag starts over its diplomatic relation
limit" and "vassalage matches CK3's 867 lieges".

## The table

`diplomacy(liege, subject, relation)`, primary key on all three columns, so a pair may hold several relations.
Relations in use: `vassal`, `march`/`appanage` (vanilla types), `union`, `tributary_state`, `daimyo_vassal`,
`theme_subject_type` (our slotless governor type), and the peer relations `alliance` and `royal_marriage`
(`PEER_RELATIONS` in `tagdb.py`). Add a row by SQL:
`python3 -c "import sqlite3;c=sqlite3.connect('tools/tags.db');c.execute(\"insert into diplomacy values('BYZ','EPI','theme_subject_type')\");c.commit()"`
(there is no `sqlite3` CLI in the sandbox), then build.
The build writes `history/diplomacy/karolingian_vassals.txt` from the table plus the CK3-lifted marriages
(`marriages.py`); validate checks the file lists exactly those.

## Rules the checks enforce

- **Lieges follow CK3** (`tools/lieges.py`; `python3 tools/lieges.py` prints mismatches, no output is good): a tag with no
  subject relation, or only a tributary one, must have no `liege =` in CK3's 867; a vassal's overlord must be its CK3 liege's
  realm (a governor folded into a tag counts as that tag; a union subject may share its overlord's ruler).
- **Relation slots:** a tag's limit is `base_values` `diplomatic_upkeep` (patched to 5) plus its government rank's
  `diplomatic_upkeep` in `common/government_ranks/zz_kar_government_ranks.txt` (rank 1: 5, duchy 6, kingdom 7, empire 8,
  rank 5: 9; validate reads both files). A subject uses the overlord's slot when its subject type's `takes_diplo_slot`
  is yes (vassal, march, appanage, personal union); tributary, daimyo and `theme_subject_type` do not. An alliance or
  royal marriage costs both parties one slot, and an alliance plus a marriage with the same country cost one. Validate
  fails a tag that starts over its limit and WARNs on tags exactly at it.
- **Subjects (except tributaries) cannot hold alliances or marriages**; the lift skips them and validate fails them.
- **No subject adds force limit or manpower to its overlord** (`vassal`, `march`, `theme_subject_type` are 0).
- Subject types come from `tools/vanillapatch.py` edits to `common/subject_types/00_subject_types.txt`; the governor type
  sits between `# BEGIN kar theme` / `# END kar theme` markers (validate expects them). Edit the patch table, never the output.

## Governors (the Byzantine themes, the Abbasid governors)

Duchy-rank direct vassals of the sovereign in CK3's 867 become vassal tags on `theme_subject_type`, with their sub-vassals'
provinces folded in. County-rank direct vassals stay inside the overlord's tag. `lieges.governor_province_mismatches`
(validate) checks every province of BYZ and ARB against the CK3 chain. Provinces CK3 holds under someone else go to that
CK3 owner's tag. Tag names come from CK3 (`tagloc.family_region` for the `d_nf_*` theme families).

## Partition by event

Lotharingia splits at Meerssen by `events/LotharingianPartition.txt` (hand-written; see `cl-events`). Validate keeps its
province lists equal to LOT's land; if LOT's provinces change, update the lists.
