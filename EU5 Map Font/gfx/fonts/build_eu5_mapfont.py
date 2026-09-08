#!/usr/bin/env python3
"""Build EU4 Mapfont.fnt + Mapfont.dds from EU5 CormorantGaramond-SemiBold.

Replicates the vanilla EU4 Mapfont conventions:
  - .fnt line formats byte-exact (confirmed from vanilla file)
  - 1024x1024 BGRA DDS, 11 mips, total 5,592,532 bytes, header identical to vanilla
  - alpha = round(gray * 0.75), RGB ramp recovered from vanilla texture
  - 8px cell padding (fallback 6/4/2/0), xoffset = left - pad, yoffset = base - top - pad
"""
import struct
from pathlib import Path
import numpy as np
import freetype
from fontTools.ttLib import TTFont

EU5_TTF = "/home/rick/Paradox/Games/Europa Universalis V/game/loading_screen/fonts/MapNamesFonts/CormorantGaramond-SemiBold.ttf"
VANILLA_FNT = "/home/rick/Paradox/Games/Europa Universalis IV/gfx/fonts/Mapfont.fnt"
VANILLA_DDS = "/home/rick/Paradox/Games/Europa Universalis IV/gfx/fonts/Mapfont.dds"
OUT_DIR = Path("/tmp/opencode/eu5map")
OUT_FNT = OUT_DIR / "Mapfont.fnt"
OUT_DDS = OUT_DIR / "Mapfont.dds"

SIZE = 100          # bake size in px (vanilla: size=100)
UPEM = 1000
ATLAS = 1024
GAP = 1             # spacing=1,1 like vanilla
FACE = "Cormorant Garamond SemiBold"

# cp1252 bytes 0x80-0x9F -> unicode codepoint (ids 0xA0-0xFF are identical to latin-1)
CP1252 = {
    0x80: 0x20AC, 0x82: 0x201A, 0x83: 0x0192, 0x84: 0x201E, 0x85: 0x2026,
    0x86: 0x2020, 0x87: 0x2021, 0x88: 0x02C6, 0x89: 0x2030, 0x8A: 0x0160,
    0x8B: 0x2039, 0x8C: 0x0152, 0x8E: 0x017D, 0x91: 0x2018, 0x92: 0x2019,
    0x93: 0x201C, 0x94: 0x201D, 0x95: 0x2022, 0x96: 0x2013, 0x97: 0x2014,
    0x98: 0x02DC, 0x99: 0x2122, 0x9A: 0x0161, 0x9B: 0x203A, 0x9C: 0x0153,
    0x9E: 0x017E, 0x9F: 0x0178,
}
# glyphs absent from Cormorant -> substitute codepoint (U+00B5 mu is missing)
SUBST = {0x00B5: 0x03BC}


def parse_fnt_chars(path):
    ids = []
    for line in Path(path).read_text("latin-1").splitlines():
        if line.startswith("char "):
            kv = dict(tok.split("=", 1) for tok in line.split()[1:])
            ids.append(int(kv["id"]))
    return ids


def codepoint_of_id(cid):
    if cid <= 0x7F:
        return cid
    if 0x80 <= cid <= 0x9F:
        return CP1252[cid]
    return cid  # 0xA0-0xFF identical to unicode


def recover_ramp():
    """Recover alpha->gray mapping from the vanilla texture (pure function test)."""
    data = Path(VANILLA_DDS).read_bytes()
    arr = np.frombuffer(data, dtype=np.uint8, count=4 * 1024 * 1024, offset=128)
    arr = arr.reshape(1024, 1024, 4)  # BGRA
    alpha = arr[..., 3]
    ramp = np.zeros(192, np.int64)
    missing = []
    for a in range(1, 192):
        sel = arr[alpha == a]
        if sel.size:
            ramp[a] = int(round(np.mean(sel[:, :3].astype(np.float32))))
        else:
            missing.append(a)
    if missing:
        known = [a for a in range(1, 192) if a not in missing]
        for a in missing:
            lo = max((x for x in known if x < a), default=None)
            hi = min((x for x in known if x > a), default=None)
            if lo is not None and hi is not None:
                ramp[a] = int(round(int(ramp[lo]) + (a - lo) * (int(ramp[hi]) - int(ramp[lo])) / (hi - lo)))
            elif lo is not None:
                ramp[a] = int(ramp[lo])
            elif hi is not None:
                ramp[a] = int(ramp[hi])
        print(f"  note: interpolated {len(missing)} missing alpha levels: {missing}")
    ramp = np.clip(ramp, 0, 255).astype(np.uint8)
    probe = {a: int(ramp[a]) for a in (1, 10, 40, 80, 120, 130, 131, 140, 150, 160, 170, 180, 190, 191)}
    print(f"  recovered ramp (alpha:gray): {probe}")
    return ramp


def extract_kerning(tt, cmap, char_ids):
    """Sum GPOS PairPos XAdvance for all pairs within our char set (font units)."""
    gpos = tt["GPOS"].table
    target = set()
    for cid in char_ids:
        cp = codepoint_of_id(cid)
        cp = SUBST.get(cp, cp)
        if cp in cmap:
            target.add(cmap[cp])
    pairs = {}

    def value_adv(vr):
        if vr is None:
            return 0
        return vr.XAdvance if (vr.getFormat() & 0x0004) else 0

    from fontTools.ttLib.tables.otTables import PairPos, ExtensionPos

    def gather_pairpos(st):
        if isinstance(st, ExtensionPos):
            if st.ExtensionLookupType == 2:
                for sub in (st.ExtSubTable,):
                    yield sub
            return
        if isinstance(st, PairPos):
            yield st

    for lookup in gpos.LookupList.Lookup:
        if lookup.LookupType not in (2, 9):
            continue
        for st in lookup.SubTable:
            for pp in gather_pairpos(st):
                if pp.Format == 1:
                    cov = pp.Coverage.glyphs
                    for i, first in enumerate(cov):
                        if first not in target:
                            continue
                        for rec in pp.PairSet[i].PairValueRecord:
                            second = rec.SecondGlyph
                            if second not in target:
                                continue
                            k = value_adv(rec.Value1) + value_adv(getattr(rec, "Value2", None))
                            if k:
                                pairs[(first, second)] = pairs.get((first, second), 0) + k
                elif pp.Format == 2:
                    cov = pp.Coverage.glyphs
                    cd1 = pp.ClassDef1.classDefs
                    cd2 = pp.ClassDef2.classDefs
                    for i, first in enumerate(cov):
                        if first not in target:
                            continue
                        c1 = cd1.get(first, 0)
                        if c1 >= len(pp.Class1Record):
                            continue
                        recs1 = pp.Class1Record[c1]
                        for j, second in enumerate(cov):
                            if second not in target:
                                continue
                            c2 = cd2.get(second, 0)
                            if c2 >= len(recs1.Class2Record):
                                continue
                            rec = recs1.Class2Record[c2]
                            k = value_adv(rec.Value1) + value_adv(getattr(rec, "Value2", None))
                            if k:
                                pairs[(first, second)] = pairs.get((first, second), 0) + k
    return pairs


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print("== stage 1: char set from vanilla fnt")
    char_ids = parse_fnt_chars(VANILLA_FNT)
    print(f"  {len(char_ids)} chars: ids {min(char_ids)}..{max(char_ids)}")
    absent = [c for c in range(32, 256) if c not in char_ids]
    print(f"  absent ids: {absent}")

    print("== stage 2: vanilla RGB ramp")
    ramp = recover_ramp()

    print("== stage 3: font metrics")
    tt = TTFont(EU5_TTF)
    cmap = tt.getBestCmap()
    upem = tt["head"].unitsPerEm
    ascent = tt["hhea"].ascent * SIZE / upem
    descent = -tt["hhea"].descent * SIZE / upem
    line_height = int(round(ascent + descent))
    base = int(round(ascent))
    print(f"  ascent={ascent:.1f} descent={descent:.1f} lineHeight={line_height} base={base}")
    hmtx = {g: m[0] for g, m in tt["hmtx"].metrics.items()}

    print("== stage 4: GPOS kerning")
    pairs = extract_kerning(tt, cmap, char_ids)
    id_of_name = {}
    for cid in char_ids:
        cp = codepoint_of_id(cid)
        cp = SUBST.get(cp, cp)
        name = cmap.get(cp)
        if name is not None:
            id_of_name[name] = cid
    kerns = {}
    for (a, b), v in pairs.items():
        if a in id_of_name and b in id_of_name:
            kerns[(id_of_name[a], id_of_name[b])] = int(round(v * SIZE / upem))
    print(f"  {len(kerns)} kern pairs (vanilla had 3789)")

    print("== stage 5: bake glyphs")
    face = freetype.Face(EU5_TTF)
    face.set_pixel_sizes(0, SIZE)
    ft_load = freetype.FT_LOAD_RENDER | freetype.FT_LOAD_NO_HINTING
    cells = {}
    empty = []
    subbed = []
    for cid in char_ids:
        cp = codepoint_of_id(cid)
        orig = cp
        cp = SUBST.get(cp, cp)
        gidx = face.get_char_index(cp)
        if gidx == 0:
            cp = 0x20  # missing -> empty (space-like)
            gidx = face.get_char_index(cp)
            empty.append((cid, hex(orig)))
        elif cp != orig:
            subbed.append((cid, hex(orig), hex(cp)))
        face.load_char(chr(cp), ft_load)
        g = face.glyph
        bm = g.bitmap
        ink = None
        if bm.rows and bm.width:
            ink = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.width)
        xadv = int(round(hmtx.get(cmap.get(cp, ""), 0) * SIZE / upem))
        cells[cid] = {"ink": ink, "left": g.bitmap_left, "top": g.bitmap_top, "xa": xadv}
    print(f"  empty glyphs: {empty}")
    print(f"  substitutions: {subbed}")

    print("== stage 6: pack cells (shelf)")
    ok = False
    for pad in (8, 6, 4, 2, 0):
        placements = {}
        items = []
        for cid in char_ids:
            ink = cells[cid]["ink"]
            w, h = (17, 0) if ink is None else (ink.shape[1] + 2 * pad, ink.shape[0] + 2 * pad)
            items.append((cid, w, h))
        row_y, row_h, row_x = 0, 0, 0
        ok = True
        for cid, w, h in sorted(items, key=lambda t: -t[2]):
            if h == 0:
                placements[cid] = (0, 0, w, h)
                continue
            if row_x + w > ATLAS:
                row_y += row_h + GAP
                row_x, row_h = 0, 0
            if row_y + h > ATLAS:
                ok = False
                break
            placements[cid] = (row_x, row_y, w, h)
            row_x += w + GAP
            row_h = max(row_h, h)
        if ok:
            print(f"  packed at padding={pad}, used height={row_y + row_h}/{ATLAS}")
            break
        print(f"  padding={pad}: overflow, retrying with smaller padding")
    if not ok:
        raise SystemExit("atlas does not fit")

    print("== stage 7: compose atlas + emit fnt/dds")
    atlas = np.full((ATLAS, ATLAS, 4), 255, np.uint8)  # BGRA, opaque white background
    atlas[..., 3] = 0  # alpha 0
    fnt_lines = [
        f'info face="{FACE}" size={SIZE} bold=1 italic=0 charset="" '
        f"stretchH=100 smooth=1 aa=1 padding={pad},{pad},{pad},{pad} spacing=1,1",
        f"common lineHeight={line_height} base={base} scaleW={ATLAS} scaleH={ATLAS} pages=1",
    ]
    for cid in char_ids:
        c = cells[cid]
        ink = c["ink"]
        x, y, w, h = placements[cid]
        if ink is None:
            xo, yo = -pad, base - pad
        else:
            nh, nw = ink.shape
            xo = c["left"] - pad
            yo = base - c["top"] - pad
            alpha = np.rint(ink.astype(np.float32) * 0.75).clip(0, 191).astype(np.uint8)
            sub = atlas[y + pad:y + pad + nh, x + pad:x + pad + nw]
            sub[..., 0] = ramp[alpha]
            sub[..., 1] = ramp[alpha]
            sub[..., 2] = ramp[alpha]
            sub[..., 3] = alpha
        fnt_lines.append(
            f"char id={cid:<5} x={x:<6} y={y:<6} width={w:<6} height={h:<5} "
            f"xoffset={xo:<6} yoffset={yo:<6} xadvance={c['xa']:<6} page=0"
        )
    fnt_lines.append(f"kernings count={len(kerns)}")
    fnt_lines.extend(
        f"kerning first={a:<4} second={b:<4} amount={v:<4}"
        for (a, b), v in sorted(kerns.items())
    )
    OUT_FNT.write_text("\n".join(fnt_lines) + "\n", encoding="ascii")

    # mips: 2x2 box average down to 1x1 (11 levels)
    levels = [atlas]
    cur = atlas
    while cur.shape[0] > 1:
        cur = ((cur[0::2, 0::2].astype(np.uint32) + cur[1::2, 0::2]
                + cur[0::2, 1::2] + cur[1::2, 1::2]) // 4).astype(np.uint8)
        levels.append(cur)
    data = b"".join(lv.tobytes() for lv in levels)
    assert len(data) == 5592404, len(data)
    hdr = (b"DDS " + struct.pack("<7I", 124, 0xA1007, 1024, 1024, 4194304, 0, 11)
           + b"\x00" * 44
           + struct.pack("<8I", 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
           + struct.pack("<5I", 0x00401008, 0, 0, 0, 0))
    assert len(hdr) == 128, len(hdr)
    OUT_DDS.write_bytes(hdr + data)

    vanilla_hdr = Path(VANILLA_DDS).read_bytes()[:128]
    print(f"  header identical to vanilla: {hdr == vanilla_hdr}")
    print(f"  wrote {OUT_FNT} ({OUT_FNT.stat().st_size} bytes)")
    print(f"  wrote {OUT_DDS} ({OUT_DDS.stat().st_size} bytes, expected 5592532)")
    assert OUT_DDS.stat().st_size == 5592532


if __name__ == "__main__":
    main()