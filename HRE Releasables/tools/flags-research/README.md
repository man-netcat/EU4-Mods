# Flag research: HRE releasable tags

This folder holds the coat-of-arms research for the 9 new HRE releasable tags.
It contains the WappenWiki source pages, the source SVG files, and the
confirmed historical blazon for each tag. The `svg-sources/` folder holds the
source SVG files. The confirmed flags are built by the per-tag builders in
`tools/flags-research/` and installed to `gfx/flags/`.

## Summary

| Tag | State (1444) | Confirmed blazon | WappenWiki source |
|-----|--------------|------------------|-------------------|
| WRM | Prince-Bishopric of Worms | Azure, a key argent (Zurich Roll variant) | Prince-Bishopric_of_Worms |
| HBS | Prince-Bishopric of Halberstadt | Per pale argent and gules, a wolf's hook sable | Prince-Bishopric_of_Halberstadt |
| MRB | Prince-Bishopric of Merseburg | Or, a cross sable | File:Merseburg.svg |
| TCK | County of Tecklenburg | Argent, three water-lily leaves gules | County_of_Tecklenburg |
| GBH | Principality of Grubenhagen | Per fess: Brunswick two-lions / Everstein / Homburg | House_of_Brunswick |
| RZB | Prince-Bishopric of Ratzeburg | Per pale azure and or: gold staff, blue castle | Prince-Bishopric_of_Ratzeburg |
| DPH | County of Diepholz | Or, a crowned lion statant gules (historical) | House/File:Diepholz.svg |
| SYE | Prince-Bishopric of Speyer | Azure, a cross argent | Prince-Bishopric_of_Speyer |
| ~~NIE~~ | ~~Lordship of Nienburg~~ | ~~DROPPED~~ | ~~none (not a state)~~ |

NIE (Nienburg) was dropped. Nienburg was never an independent imperial state.
It was held by the Counts of Hoya, then the Dukes of Luneberg-Celle. There is
no legitimate Nienburg coat of arms on WappenWiki.

## Detail

### WRM - Prince-Bishopric of Worms

- WappenWiki page: https://wappenwiki.org/index.php/Prince-Bishopric_of_Worms
- SVG source: https://wappenwiki.org/images/5/53/Worms.svg
- File: `svg-sources/WRM_Worms.svg`
- Confirmed field colours (rendered): azure field ~56%, argent ~38%.

WappenWiki shows the Zurich Roll variant: an upright silver key on a blue
field. The later standard bishopric arms are a sable field with a silver key
per bend and 4:4 gold billets. The user chose the Zurich Roll variant shown on
WappenWiki.

### HBS - Prince-Bishopric of Halberstadt

- WappenWiki page: https://wappenwiki.org/index.php/Prince-Bishopric_of_Halberstadt
- SVG source: https://wappenwiki.org/images/2/24/Halberstadt.svg
- File: `svg-sources/HBS_Halberstadt.svg`
- Confirmed field colours (rendered): argent ~34%, gules ~33%, sable outline.

Blazon: parted per pale argent and gules, charged with a black wolf's hook
(Doppelhaken). This is the arms of the bishopric and of the state.

### MRB - Prince-Bishopric of Merseburg

- WappenWiki file page: https://wappenwiki.org/index.php?title=File:Merseburg.svg
- SVG source: https://wappenwiki.org/images/e/e8/Merseburg.svg
- File: `svg-sources/MRB_Merseburg.svg`
- Confirmed field colours (rendered): or ~35%, sable ~31%.

Blazon: or, a cross sable (a black cross on a gold field).

### TCK - County of Tecklenburg

- WappenWiki page: https://wappenwiki.org/index.php/County_of_Tecklenburg
- SVG source: https://wappenwiki.org/images/c/cc/Tecklemburg.svg
- File: `svg-sources/TCK_Tecklemburg.svg`
- Confirmed field colours (rendered): argent ~41%, gules ~23%.

Blazon: argent, three water-lily leaves (Seeblatter) gules. This is the symbol
of the territory since the oldest counts (1139-1247). The file
`svg-sources/TCK_ref_Tecklenburg_Lingen_quartered.svg` is the later quartered
version (after 1493), kept for reference.

### GBH - Principality of Grubenhagen

- Primary source: http://www.welt-der-wappen.de/Heraldik/seiten/welfen2.htm
  (Bernhard Peter, "Wappen, Linien und Territorien der Welfen (2)")
- Flag file: `build_gbh_flag.py` (composed, not a single WappenWiki shield)

Confirmed 1444 blazon (per fess, chosen by the user):

- Top band: Braunschweig, gules, two lions passant guardant or (the Brunswick
  arms fill the whole top half).
- Bottom-left: Everstein, azure, a lion rampant argent crowned or.
- Bottom-right: Homburg, within a bordure compony azure and argent, gules, a
  lion rampant or armed and langued azure.

The Grubenhagen princes bore these arms after the fall of Everstein (1408)
and Homburg (1409/1415), so they are correct for 1444 (Heinrich III
1437-1464, Albrecht II co-regent from 1441). The user chose the top half of
the Braunschweig-Lüneburg flag (`BRU.tga` in the "WappenWiki Flags for EUIV -
Custom" mod), transplanted pixel-for-pixel onto the new GBH flag as the top
band, so the Brunswick two-lions fill the whole top half. The later 5-field
Schildfuß variant with Lauterberg appears only from 1593, not in 1444. The
old file `svg-sources/GBH_Brunswick-Grubenhagen.svg` (labelled "after
conquering Scharzfeld and Lauterberg") is anachronistic and was rejected.

Component sources:

- Top band: `BRU.tga` (WappenWiki Flags for EUIV - Custom), top half
  transplanted pixel-for-pixel = Braunschweig, gules, two lions passant
  guardant or.
- Bottom-left: `svg-sources/GBH_Everstein.svg` (azure, argent lion, or crown).
- Bottom-right: `svg-sources/GBH_Ernst_II_15th_century.svg`, the 4th quarter
  of the Ernst II Braunschweig-Lüneburg arms
  (https://wappenwiki.org/images/1/1b/Ernst_II_Braunschweig-Luneburg.svg),
  lifted wholesale = Homburg, gules a lion rampant or within a bordure
  compony argent and azure. The checked bordure is the genuine Ernst II art,
  not drawn programmatically.

### RZB - Prince-Bishopric of Ratzeburg

- WappenWiki page: https://wappenwiki.org/index.php/Prince-Bishopric_of_Ratzeburg
- SVG source: https://wappenwiki.org/images/f/f9/Ratzeburg.svg
- File: `svg-sources/RZB_Ratzeburg.svg`
- Confirmed field colours (rendered): azure ~40%, or ~20%.

Blazon: parted per pale. Dexter, azure with a gold bishop's staff. Sinister,
or with a blue castle. This form was used from Bishop Detlev von Parkentin
(1395-1414), so it is correct for 1444.

### DPH - County of Diepholz

- WappenWiki file page: https://wappenwiki.org/index.php?title=File:Diepholz.svg
- SVG source: https://wappenwiki.org/images/4/40/Diepholz.svg
- File: `svg-sources/DPH_Diepholz.svg`
- Confirmed field colours (rendered): or ~21%, azure ~14%, gules ~12%, argent ~7%.

Note: WappenWiki `Diepholz.svg` is the modern (1951) quartered DISTRICT arms
(lion, eagle, and bear-paws). It is not the historical 1444 county arms. The
historical County of Diepholz arms is or with a crowned lion statant gules.
Confirm which arms to use before making the flag.

### SYE - Prince-Bishopric of Speyer

- WappenWiki page: https://wappenwiki.org/index.php/Prince-Bishopric_of_Speyer
- SVG source: https://wappenwiki.org/images/f/fc/Speyer.svg
- File: `svg-sources/SYE_Speyer.svg`
- Confirmed field colours (rendered): azure ~35%, argent ~31%.

Blazon: azure, a plain or silver cross. This is the arms of the Hochstift
Speyer, used since the 14th century Zurich Roll.

## Method

For each tag I confirmed the blazon from written sources (Bernhard Peter,
heraldry-wiki) and cross-checked the WappenWiki SVG by rendering pixels. The
rendered colour data appears under each entry above.
