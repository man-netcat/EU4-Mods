# Italy partition (CK3 867.1.1)

Status: implemented in `tools/tags.db`, built and validated.

## Francia precedent
- One kingdom tag per Carolingian king: FRA, GER, LOT, ITA.
- Another title held by the same king is a `union` (AQI, BAV, DAU, PRO).
- A duchy held by someone else who answers directly to the king is a rank-2
  `vassal` tag (FLA, NRM, AGR, SWA, THU, WFR, HOL and the archbishoprics).
- Counts answering directly to the king, and vassals of a duke, are folded
  into the king's or duke's tag. EU4 has no sub-vassal layer.

## New tags (all vassals of ITA, rank 2, catholic, western tech)

| Tag | CK3 title | 867 holder | Capital | Provinces | Culture |
|---|---|---|---|---|---|
| FRL | d_friuli (+ d_verona) | Unruoch III | 111 | 111 Friuli, 1769 Gorz, 4738 Trieste, 130 Istria, 1774 Treviso, 4729 Padova, 108 Verona, 110 Trent | franconian |
| TUS | d_toscana | Adalbert I | 116 | 116 Firenze, 2980 Lucca, 2978 Arezzo, 117 Siena, 115 Pisa, 2976 Umbria, 1247 Corsica | frankish |
| SPL | d_spoleto | Lambert I | 4731 | 4731 Spoleto, 119 Ancona, 2977 Urbino, 114 Romagna, 4730 Bologna, 113 Ferrara, 120 Abbruzzi, 105 Parma | italian |
| UBG | d_upper_burgundy | Conrad the Younger | 205 | 205 Savoie, 4720 Geneva | bavarian |

TUS and SPL reuse vanilla tag codes (added to `VANILLA_REUSE` in
`tools/validate.py`). FRL and UBG are new codes.

## Other moves
- 4719 is Bresse in-game (the DB labels it Annecy) and stays with LOT.
- 102 Nice: ITA -> PRO (Provence).
- 4732 Terracina: ITA -> PAP (c_tivoli is the Pope's).
- 120 Abbruzzi: BNV -> SPL (c_abruzzi is Lambert's).
- 1247 Corsica: ITA -> TUS.
- ITA keeps 15 provinces: 101, 103, 104, 106, 107, 109, 1862, 1875,
  2979, 2981, 2992, 4727, 4728, 4739, 4740.

## Decisions taken (not confirmed by the user)
- Upper Burgundy is its own tag.
- Parma goes to Spoleto (user's call, overriding CK3's Tuscany).
- Friuli takes a new code (FRL), not VRN or AQU.
- Cultures were set by hand from each ruler's CK3 culture via
  `culturelift.CK3_TO_EU4` (french -> frankish, franconian, italian,
  bavarian), because `addtag.py` could not run in the cloud session.

## Open items
- No flags exist for FRL, TUS, SPL, UBG (validate only warns).
