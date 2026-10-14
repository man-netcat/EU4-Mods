---
name: add-formable
description: Add a new formable nation to The Karolingians via formables tables, shared decision, and suppression
---

# Add a new formable

Formable tags live on `formables` (+ `formable_areas`/`formable_provinces`), not on `tags`: they hold no land at the start date. See `AGENTS.md` "Formables", `tools/models.py:87-151`, `tools/tagdb.py:100-119,374-475`, `tools/histgen.py:99-238`, `tools/eu4.py:944-955,1126-1257`, `tools/validate.py:616-737`.

## Workflow

1. Require exact requirements before writing anything: land (areas + explicit provinces), starters, percent, capital, rank, CK3 title. If the request does not give them, ask first — never assume them.
2. Insert the `formables` row: `tag/name/adj/ck3_title/rank/color/percent/capital/own_capital/home_capital/rank_required/culture/culture_group/dynasty/exclusive`.
   - `percent` NULL = all land; otherwise enacted at that share rounded up (`required_count`, `tools/tagdb.py:130-134`). Validate checks the enacted value.
   - `own_capital` requires holding the formable's `capital` (lives on base `Tag`). `home_capital` requires the firing tag's capital inside the requirement land (Denmark/Norway/Sweden pattern); it excludes `own_capital`. Generated `own_capital` effects move the seat via `set_capital` (Somalia precedent).
   - `rank_required` requires an exact government rank to fire (Scandinavia/GBR kings-only = 3).
3. Point starters via `tags.forms`/`tags.decision`. All starters of one formable share a single decision key and one shared file `decisions/FormX.txt`. HLR's requirement stays dynamic (`empire_core`, `tools/eu4.py:184-189`); its custom decision stays handwritten.
   - FIN same-tag kingdom (`decisions/FinlandKingdom.txt`) and ROM restoration (`decisions/FormROM.txt`, hegemony rank 5) are custom the same way — no/extra formable row, hardcoded triggers.
4. Pick one gating flavour (never mix `culture` with `culture_group`, never mix `own_capital` with `home_capital`):
   - listed starter tags (Hungary, Volhynia, Iceland), primary `culture` (Wales, Sardinia, Poland, England), `culture_group`s space-separated (Britannia: british brythonic gaelic — gaelic displays as Celtic), `dynasty` (Karlings alone restore the Empire), `home_capital`, `exclusive` (listed starters mutual rivals, each fires only once the others are gone — Halych/Volodymyr).
   - A starter whose ruler culture misses the formable gate fails `selfcheck` — drop the starter link or keep the land culture.
5. Optional `formable_renames` rows (former tag or culture -> loc key via `override_country_name`, most-specific first; GBR fired by welsh becomes Prydain — the Armenia pattern). Exactly one of culture/tag set per row.
6. Suppress vanilla counterparts: starters list the vanilla decision key in `tag_suppress` (HUN/POL/ENG/ICE/IRE do; SAR/VOL/WLS/HLR have no vanilla counterpart). Neutralization is by same-filename dummy in `VANILLA_FORMATION_FILES` (`tools/eu4.py:944-955`) — duplicate keys coexist across files so stubs in our own files never win.
7. Decision `desc` is pure flavour in vanilla style ("Let us…"): never mention province counts or names. No bespoke tooltips (HLR alone keeps its own); reference the generated trigger plainly (`common/scripted_triggers/KarolingianFormations.txt`). Validate checks trigger land against the requirement table.
8. Run `python3 tools/build.py && python3 tools/validate.py` — both green. Commit only when explicitly asked.
