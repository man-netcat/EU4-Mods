# Charlemagne's Legacy

A Crusader Kings III-flavoured total conversion for Europa Universalis IV:
the 867 world rebuilt on the EU4 map — some 94 realms, five government-rank
tiers, and rulers, colours and land lifted straight from CK3's 867 bookmark.

## Playing

Enable **Charlemagne's Legacy** in the launcher and pick the **Charlemagne's Legacy**
bookmark (start date 867.1.1). Needs the usual DLC for government and
Mandate mechanics to behave (Mandate of Heaven for Tang).

## Credits

All flag artwork in `gfx/flags/` is adapted from coats of arms on
[WappenWiki](https://wappenwiki.org/index.php/Main_Page): converted from
SVG, rescaled and mounted on flag fields (most of them — including the
newest: Provence's Bosonid cross, the Viennois Dauphin, the Chelmno and
Płock eagles, the Sandomierz stars and the Orkney lymphad). Those
WappenWiki-derived flags are licensed under [CC BY-NC-SA
3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/) per the site's
terms; the mod itself is and stays free. If you reuse those flags, credit
WappenWiki and share them under the same license.

The Tulunids used to carry an inscription banner traced from Ahmad ibn
Tulun's gold dinar of AH 268; per the CK3-CoA pipeline they now carry
Patrum Scuta's Or/Argent crescent design like every other covered tag.

The dynasty CoAs (`tools/coaflags.py`) render straight from CK3's own
coat-of-arms system instead: Patrum Scuta's authored designs come first
(its files load after the base game's, so its blocks win in-game), then
the base game's `90_dynasties.txt`; dynasties with no authored design
(the CK3-random ones — every muslim realm from ALG to ZAM and the
Mozarabic houses BGS, CUE, MLR, SLM, VLL among them) read
their generated instance out of a non-ironman 867 bookmark — the save's
`coat_of_arms_manager_database` carries every CoA the engine rolled,
reached through the dynasty record's `coat_of_arms_id` (`save_dynasty_coa`,
with the title entity as fallback), so the flags match what CK3 itself
displays for the dynasty at the start date. Colours snap to the
WappenWiki tincture canon per the palette table in
`tools/FLAG_NOTES.md`.

## Developing

Everything is generated from a SQLite database. From the mod folder:

```bash
python3 tools/build.py     # regenerate the mod (~2 s warm, ~40 s cold)
python3 tools/validate.py  # run all checks (~3 s)
```

- `tools/tags.db` is the single source of truth (tags, provinces, reforms,
  diplomacy, government data).
- `tools/` holds the toolchain: `tagdb` (model + loading), `eu4`
  (generation), `ck3` (867 holder/ruler sync), `histgen` (country text),
  `build` (orchestrator), `validate` (checks), `models`/`db` (schema +
  connection), `enc` (transliteration for cp1252 output).
- Generated output (`history/`, `common/countries/`, `common/country_tags/`,
  `decisions/`, `gfx/flags/` for cloned ones) is overwritten on every build —
  never hand-edit it. Hand-written sources: `tools/*.py`, `localisation/`,
  `common/government_names/`, `common/government_ranks/`,
  `common/defines.lua`, custom `gfx/flags/*.tga`, the `.mod` files.
- See `AGENTS.md` for the full contributor instructions and `tools/FLAG_NOTES.md`
  for the flag palette and layout.
