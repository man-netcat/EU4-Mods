# The Karolingians

A Crusader Kings III-flavoured total conversion for Europa Universalis IV:
the 867 world rebuilt on the EU4 map — some 94 realms, five government-rank
tiers, and rulers, colours and land lifted straight from CK3's 867 bookmark.

## Playing

Enable **The Karolingians** in the launcher and pick the **Karolingians**
bookmark (start date 867.1.1). Needs the usual DLC for government and
Mandate mechanics to behave (Mandate of Heaven for Tang).

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
