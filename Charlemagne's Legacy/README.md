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
