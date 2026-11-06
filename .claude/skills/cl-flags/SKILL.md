---
name: cl-flags
description: Flags in Charlemagne's Legacy - placeholder flags, which flags are the user's own, and why real flags cannot be built in a cloud session. Use when a tag is added, renamed or removed, or when asked to make flags.
---

# Flags

- `gfx/flags/<TAG>.tga` is 256x256, 24bpp, uncompressed. `gfx/flags` is `replace_path`'d: a tag with no file shows the
  base game's missing-flag image.
- **Placeholders:** `python3 tools/placeholder_flags.py` writes one for every tag and formable without a flag (the tag's
  colour on one diagonal, black on the other, like the game's missing flag). It never overwrites. `--list` names every flag
  that still looks like a placeholder (validate warns with the same list). Replace one by deleting it or dropping the real
  flag over it.
- **Never overwrite or delete a flag that is not a placeholder**; uncommitted or custom `gfx/flags/*.tga` are the user's
  own work. Never reuse a base-game flag (validate fails if a flag equals one of the base game's, where the base game's flag files are present). `retag.py` moves a flag
  with its tag and refuses to overwrite one.
- Deleting a tag: remove its placeholder flag only (`placeholder_flags.py --list` tells which).
- **Real flags** have two distinct paths (`tools/FLAG_NOTES.md`): a user-named WappenWiki charge SVG hand-composed on a flat
  field (not through `coaflags.py`), or a CK3 coat-of-arms bake with `tools/coaflags.py`. WappenWiki-derived flags carry a
  CC BY-NC-SA credit in the README.
- **Cloud sessions cannot make real flags:** `wappenwiki.org` and Wikimedia are unreachable from the sandbox, Inkscape is not
  installed, and the bake needs a CK3 save, the Patrum Scuta workshop files and the user's charges. If the user wants flags, they
  download the SVGs locally; offer to write the compositing script, never fake the result.
