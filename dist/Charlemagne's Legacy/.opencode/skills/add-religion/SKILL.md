---
name: add-religion
description: Add a new religion to Charlemagne's Legacy with icon strips and interface sprites in sync
---

# Add a new religion

Religion lives in `common/religions/00_religion.txt`, a full vanilla copy with our faiths appended (engine file-override is by exact filename). Precedent: `slavic`/`romuva`/`suomenusko` (CK2 867 names/colours/icons, our descs, Norse-clone mechanics, small thematic country bonus, no personal deities), `taltosist` and `krstjani` (CK3 name/colour/icon). The Christian set is closed at catholic (displayed as Chalcedonian) + `krstjani` — no rite splits. See `AGENTS.md` standing conventions and `tools/validate.py:1058-1153`.

## Workflow

1. Append the faith to the right group in `common/religions/00_religion.txt` with the next `icon = N` number. Register the key in `tools/tags.db` `religions` when tags/provinces will reference it — every `religion = X` in output must be a vanilla key or one of our additions.
2. Extend all four vanilla DDS strips in place, same filenames, uncompressed 32-bit RGBA exactly like vanilla, with the new icon as the next frame: `gfx/interface/icon_religion.dds`, `icon_religion_small.dds`, `country_icon_religion.dds`, `province_view_religion.dds`. Miss a strip and icons shift (the classic bug).
3. Update all three full vanilla copies of the interface sprites, keeping their sprite lists byte-identical to vanilla except the frame bump: `interface/countryview.gfx` (`GFX_icon_religion`, `GFX_country_icon_religion`, `GFX_icon_religion_small`), `interface/ledger.gfx` (`GFX_religion_icon_strip`), `interface/provinceview.gfx` (`GFX_province_view_religion`). Every listed sprite gets `noOfFrames` == max icon number and must point at our DDS strip; the strip width must equal frames × 64 or 32 px.
4. Add display loc in `localisation/replace/karolingian_religion_l_english.yml` (vanilla-key renames must live in `localisation/replace/`; UTF-8 with BOM).
5. Re-sync all eight files against the base game on every patch. Validate guards the vanilla key set, both sprite lists, the TGA targets, and the frame counts.
6. Run `python3 tools/build.py && python3 tools/validate.py` — both green — and confirm the icons render correctly in-game (country view, ledger, province view).
