---
name: add-flag
description: Add a new flag TGA to Charlemagne's Legacy following canvas, palette, and layout conventions
---

# Add a new flag

Flags live in `gfx/flags/` (replace_path — no vanilla content loads there). Missing flags must stay visibly missing.

## Workflow

1. Read `tools/FLAG_NOTES.md` and `AGENTS.md` items 5-6. Check `tools/eu4.py` flag step (`step_custom`, `flag_from`/`flag_source` cols on `tags`) and `tools/validate.py:594-602` (custom registration + flag check WARNS only).
2. Conventions:
   - Canvas: 256x256 TGA.
   - Charge flags (LUT, RAN, BOH, ABK precedent): charge 176x210, pasted at (40,23) on the field colour.
   - Palette (`tools/FLAG_NOTES.md:9-19`):
     Or 242,188,81 / Azure 13,103,147 / Argent 246,246,246 / Sable 51,51,51 / Gules 188,46,46 / Purpure 145,58,106 / Vert 0,150,70.
3. Never clone placeholders. If there is no real design yet, leave the flag missing — validate only WARNS.
4. Render Illustrator SVGs with inkscape (cairosvg chokes). Verify the TGA visually after render (open the actual bytes, not just the SVG).
5. Filename must be `<TAG>.tga` matching the tag code exactly. `tools/tags.db` `tags.flag_from`/`flag_source` borrows a flag only when vanilla ships none for the tag — do not point it at a placeholder.
6. Run `python3 tools/build.py && python3 tools/validate.py` — flag absence is a WARN, everything else must be green. Confirm in-game if layout is uncertain.
