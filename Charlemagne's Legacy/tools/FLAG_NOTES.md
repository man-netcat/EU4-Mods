# Flag conventions (copied from Historical European Tags/tools/FLAG_NOTES.md)

## Sourcing

- Charges traced from WappenWiki SVGs produce CC BY-NC-SA 3.0 derivatives:
  every `gfx/flags/*.tga` except direct mod-to-mod copies is covered by the
  README Credits section — keep that statement true when adding flags,
  and keep the mod free.

## Canvas and charge position

- Flag canvas: 256x256 TGA.
- Charge flags (LUT, RAN, BOH, ABK): charge 176x210, pasted at (40,23)
  on the field colour.
- Charge proportions are immutable: only uniform scaling of the whole
  charge is permitted. Never stretch, squash, crop or reshape the artwork
  to fill the slot — fit it inside 176x210 keeping its aspect ratio, and
  centre the result on the (40,23) slot.

## Standard palette

Canonical tinctures lifted from WappenWiki's own swatch SVGs (the
`view-source` of https://wappenwiki.org/index.php/Heraldic_Elements lists
every swatch; each hex is read straight out of the swatch's fill, so flags
made with these values match the WappenWiki Flags for EUIV mod exactly).

Metals (https://wappenwiki.org/images/9/99/Metal-Or.svg,
/c/ca/Metal-Argent.svg):

| Tincture | RGB | Hex |
|---|---|---|
| Or (gold) | 242,188,81 | #F2BC51 |
| Argent (white) | 246,246,246 | #F6F6F6 |

Traditional tinctures (Tincture-Azure/Gules/Purpure/Sable/Vert.svg):

| Tincture | RGB | Hex |
|---|---|---|
| Azure (blue) | 13,103,147 | #0D6793 |
| Gules (red) | 188,46,46 | #BC2E2E |
| Purpure (purple) | 145,58,106 | #913A6A |
| Sable (black) | 51,51,51 | #333333 |
| Vert (green) | 62,147,62 | #3E933E |

Stains (Stain-Murrey/Sanguine/Tenné.svg):

| Tincture | RGB | Hex |
|---|---|---|
| Murrey (mulberry) | 164,44,69 | #A42C45 |
| Sanguine (blood red) | 165,47,45 | #A52F2D |
| Tenné (tawny) | 191,117,50 | #BF7532 |

Non-traditional tinctures (Tincture-Bisque/Bleu Celeste/Brunatre/
Carnation/Cendree/Orange/Rose/Senois.svg):

| Tincture | RGB | Hex |
|---|---|---|
| Bisque (pale yellow-green) | 244,217,163 | #F4D9A3 |
| Bleu Céleste (sky blue) | 53,156,183 | #359CB7 |
| Brunâtre (brown) | 114,89,66 | #725942 |
| Carnation (flesh) | 234,191,162 | #EABFA2 |
| Cendrée (ash grey) | 122,122,122 | #7A7A7A |
| Orange | 229,138,56 | #E58A38 |
| Rose | 217,146,146 | #D99292 |
| Senois (russet brown) | 151,68,56 | #974438 |

Mod-only additions (kept from pre-existing flags, not from WappenWiki):

| Colour | RGB | Used by |
|---|---|---|
| Vert (Welsh green) | 0,150,70 | Wales/pre-existing green fields |
