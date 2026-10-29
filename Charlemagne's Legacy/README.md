# Charlemagne's Legacy

A Crusader Kings III-flavoured total conversion for Europa Universalis IV: the 867 world rebuilt on the EU4 map,
with realms, rulers, colours, cultures and faiths lifted from CK3's 867 bookmark.

## Playing

Enable **Charlemagne's Legacy** in the launcher and pick its bookmark (start date 867.1.1).

## Credits

Flag artwork in `gfx/flags/` is mostly adapted from coats of arms on
[WappenWiki](https://wappenwiki.org/index.php/Main_Page) and licensed under
[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/) per the site's terms; if you reuse those flags,
credit WappenWiki and share them under the same license. The rest are rendered from CK3's own coats of arms
(including Patrum Scuta's designs) or are placeholders awaiting a real flag. The mod itself is free.

## Developing

Everything is generated from a SQLite database (`tools/tags.db`). From the mod folder:

```bash
python3 tools/build.py     # regenerate the mod
python3 tools/validate.py  # run all checks
```

Generated output is overwritten on every build, so change the database or the tools instead of editing it.
See `AGENTS.md` for the contributor instructions and `tools/FLAG_NOTES.md` for the flag layout.
