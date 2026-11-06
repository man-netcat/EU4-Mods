# Province audit (6 Nov 2026)

`python3 tools/audit_provinces.py` walks every owned province: the paired CK3 county's 867 holder, then his liege chain to the
nearest lord who rules a tag of the mod (a governor folded into a tag counts as that tag). The province should belong to that
tag. `--classify` adds the evidence, `--apply [PID,..]` moves land. validate runs it as a check: the hit count may not exceed
`BACKLOG` in `tools/checks/provinces.py` (lower it as the list is worked off) and the strongly evidenced hits are WARNed.

## What it found

250 provinces (185 with an expected tag, 65 whose chain reaches no tag). Now 197 (141 and 56).

Root causes, in order of weight:

1. **Capitals paired with a neighbouring county.** 42 county-title tags (Rogaland, Yatvyagi, Berestye, Rounala, Fuerteventura,
   ...) had their only or capital province paired by name with someone else's county (Agdeside with c_agdeside, which Nedenes
   holds) while the tag's own county was paired to nothing. Fixed in `provfaiths.py` (the block "Province audit of 6 Nov 2026"):
   a county-title tag's capital pairs with that county. Culture and faith follow the new county (`provfaiths.py apply`).
2. **Pairing by place is an approximation.** `PROVINCE_COUNTY` pairs EU4 provinces with CK3 counties by name and area; several
   provinces share a county, homonyms exist (EU4 "Viborg" is Karelian Vyborg, not Jutland's; "Holstein" paired with c_slesvig;
   "Kildare" with c_dublin; "Lauenburg" with c_dannenberg). Moving land on such a pairing would make it worse, so a move needs
   the name to match *and* geography to back it (the paired county is the expected tag's own, or more of the province's
   EU4-area neighbours belong to the expected tag than to the owner).
3. **Swaps.** Cheboksary/Nizhny Novgorod/Starodub/Alatyr had their provinces split between CHB, OBR, KHZ the wrong way round.
4. **CK3 itself.** A holder's own duchy can be written independent (Bavaria's duke Karlmann), so the chain reaches no tag.

## What was fixed

- 42 re-pairings (above).
- 11 moves, name-matched and geography-backed or plainly right: Nijni-Novgorod (CHB -> OBR), Alatyr (KHZ -> CHB), Starodub
  (CHB -> KHZ), Tyumen (ISM -> TMN), Ferah (TIM -> SAF), Shaki (MLK -> SRV), Cambridgeshire (HRF -> NFK), Damxung (NAQ -> PHA),
  Castellon (ARG -> ADU), Menorca and Ibiza (ADU -> MLR). Capitals moved with the land: CHB 306 -> 2423, ISM 1075 -> 4690.

Not applied although the first, evidence-only pass proposed them (reverted after a name check): about 40 more moves such as Holstein -> JYL,
Kildare -> LOI, Karelia -> ONG, Lauenburg -> AGR, Cherkasy -> KIE; and Zaporozhia (283) and Cherkasy (1944) away from the
Magyars, whose settlement events (`AGENTS.md`, six Etelkoz provinces) are built on them.

## What is left (197)

| Class | Count | What it means | Next step |
|---|---|---|---|
| `none` | 56 | the holder's chain reaches no tag (independent lords, Bavaria's duke) | a modelling decision: a tag for the lord, or accept (Bavarian provinces are Ludwig's union) |
| `holder-rules` only | 45 | the holder rules the expected tag himself; true of every direct holding, so it does not say whether the owner or the pairing is wrong | per province: find the right county for the EU4 province, or move |
| `weak` | 26 | no supporting evidence | as above |
| `area` / `area+holder-rules` | 34 | geography favours the expected tag but the name does not match | check the pairing, then move |
| `own-county(+...)` | 14 | the county is the expected tag's own title; the owner is a one-province tag whose single province is paired with it | the owner's province needs a county of its own; needs the de jure county list |
| `name`, `name+holder-rules` | 17 | the name matches but no geography backs it (homonyms: Viborg, Parma, Ferrara, Teruel...) | look at the map by hand |
| `ambiguous` | 5 | two tags qualify (Gorz and Aquileia: ITA or PRO; Saarbrucken and Groningen: DAU or LOT) | the user's call (Meerssen, union) |

The tool cannot list a duchy's de jure counties (`ck3.load_titles()` is flat), so it cannot suggest the right county for a
mis-paired province. Parsing the nesting of CK3's landed titles would let `audit_provinces.py` propose re-pairings: the
counties under the owner's duchy that no owned province is paired to.

## Method for the next batch

1. `python3 tools/audit_provinces.py --classify`, pick a class.
2. For each hit open the EU4 province name, its county, the owner and the expected tag; decide pairing or ownership.
3. Pairing: add the pid to the audit block in `provfaiths.py`, run `provfaiths.py apply`. Ownership: `--apply PID,PID`.
4. `tagloc.py write`, `build.py`, `validate.py`; lower `BACKLOG`; commit with the data.
