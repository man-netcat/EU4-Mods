# Flag conventions for WappenWiki shields

This file records the flag layout we standardised on. Reuse it for every new
WappenWiki flag in this mod.

## Canvas and shield position

- Flag canvas: 256x256 TGA.
- Shield assembly height: 230 px. This is 0.9 of the canvas. Two smaller
  versions tested too small in game: 208 px (0.812), then 218 px (0.852),
  then 223 px (0.872).
- Horizontal: centre the shield. x offset = (256 - width) // 2.
- Vertical: paste 8 px below geometric centre. For a 256 canvas with a
  230 px shield: y = 21. Top gap 21, bottom gap 5.
- This downward bias is tuned in game and approved on 2026-08-21. Use it as
  the default for new flags.
- Stock WappenWiki flags use geometric centre (top gap equals bottom gap).
  Our flags sit slightly lower on purpose.

## Standard palette

| Colour | RGB |
|---|---|
| Or (gold) | 242,188,81 |
| Azure (blue) | 13,103,147 |
| Argent (white) | 246,246,246 |
| Sable (black) | 51,51,51 |
| Gules (red) | 188,46,46 |

Canton overlays must use these exact values. The BAV.tga blue and white equal
the SVG values, so overlays blend with painted quarters without seams.

## Assembly recipe (LGN, STR, GOR, JMT)

1. Render the SVG at output_width=1640 with cairosvg and unsafe=True.
2. Crop to the alpha bounding box (alpha > 60).
3. Scale to 230 px height. Keep the aspect ratio.
4. Paste at x = (256 - w) // 2, y = 21.
5. Fill the background with the field colour. Auto-detect it as the most
   common opaque colour of the render, or set it by hand.

`svg2flag.py --assembly` runs this recipe. `--y-offset` overrides the
vertical position when a flag needs a different placement.

The script is the generic WappenWiki-to-EU4 converter. It downloads a SVG
by URL or reads a local file, strips the Adobe entity block, detects the
field colour, and writes the TGA. Modes: default charge fitting,
--assembly for full shields, --full-bleed for edge-to-edge designs.

## Remove a black outline layer

Some SVGs draw the outline as a separate pure-black layer. Example:
str.svg carries it in Layer_2.

1. Strip the Adobe DOCTYPE block. Substitute the ns_* entities with their
   values.
2. List the direct g elements under the switch element.
3. Render each layer alone. A layer that contains only (0,0,0) pixels is the
   outline. Drop it.
4. Rebuild the flag from the remaining layers.

Do not erode the alpha mask to remove an outline. Erosion also cuts real
content off the coat.

## Canton overlay for quarterly banners

Example: STR (Bavaria-Straubing) with Bavarian cantons.

1. Build the base flag with the assembly recipe.
2. Pick the reference flag TGA for the canton arms (example: BAV.tga).
3. Resize it to half the canvas: 128x128.
4. Paste at (0,0) and (128,128). Exact quadrant grid keeps the design
   aligned and centred.
