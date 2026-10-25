#!/usr/bin/env python3
"""Province religions that track CK3's counties (curated, region by region).

A province's religion is the religion lifting the CK3 faith of the county it
corresponds to: the county's capital barony carries a `rite` in CK3's
history/provinces, the rite belongs to a faith (rite_types), and
faiths.FAITH_RELIGION says which EU4 religion lifts that faith. The EU4
province -> CK3 county pairing is a curated table (PROVINCE_COUNTY), one region
at a time; provinces in the table are verified, the rest are not.

Japan is audited first: CK3 splits it between the Shinto, Mahayana and
Vajrayana faiths (plus the Ryukyuan utaki faith), where the area-basis pass had
set the whole archipelago to one religion.

    python3 tools/provfaiths.py          # print the audit
    python3 tools/provfaiths.py apply    # write the expected religions to tags.db
"""
import os
import re
import sqlite3
import sys

from paths import CK3_GAME

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "tags.db")

# EU4 province id -> CK3 county (Japan, reviewed against the names and the
# geography of both maps; the old provmap.json guesses are corrected here).
PROVINCE_COUNTY = {
    1012: "c_satsuma", 1014: "c_bungo", 1015: "c_ucinaa", 1017: "c_suo",
    1018: "c_izumo", 1019: "c_harima", 1020: "c_yamashiro", 1021: "c_settsu",
    1023: "c_echizen", 1024: "c_echigo", 1025: "c_tokisara", 1027: "c_hitachi",
    1028: "c_musashi", 1029: "c_kai", 1030: "c_owari", 1818: "c_chikuzen",
    1819: "c_tosa", 1820: "c_awa", 1825: "c_aki", 1830: "c_tajima",
    1832: "c_yamato", 1835: "c_mino", 1837: "c_etchu", 1839: "c_totomi",
    1843: "c_kozuke", 4180: "c_hyuga", 4181: "c_higo", 4182: "c_hizen",
    4183: "c_iwami", 4184: "c_bizen", 4185: "c_tango", 4186: "c_iyo",
    4187: "c_kii", 4188: "c_shinano", 4189: "c_sagami", 4190: "c_shimosa",
    4191: "c_shimotsuke", 4192: "c_nushiro", 4359: "c_ise", 4360: "c_mikawa",
    4651: "c_tsushima",
}

# East Asia (China, Korea, Manchuria) and the Japanese gaps: EU4 province ->
# CK3 county by the prefecture each EU4 name stands for (EU4 uses Wade-Giles,
# Cantonese and Korean forms where CK3 has pinyin Tang names). Provinces whose
# prefecture has no certain county stay out and are reported, never guessed.
PROVINCE_COUNTY.update({
    # Japan: Tohoku, Hokkaido, Sakhalin (the counties of the Ainu realms)
    1026: "c_korehari", 4131: "c_isawa", 1031: "c_soya", 1032: "c_chupka",
    1847: "c_iskar", 1852: "c_menas", 4193: "c_uskes", 1033: "c_kusunkotan",
    4658: "c_pogibi", 738: "c_siraya", 2154: "c_hoanya", 2155: "c_amis",
    # North China
    687: "c_dengzhou_1", 688: "c_bianzhou", 689: "c_xingyuan", 690: "c_qingzhou",
    691: "c_qizhou", 692: "c_huaizhou", 693: "c_taiyuan", 694: "c_pingyang",
    695: "c_hejian", 696: "c_yizhou_1", 697: "c_datong_2", 698: "c_lingzhou",
    700: "c_jingzhao", 703: "c_lzj_chengde", 1816: "c_youzhou", 1836: "c_henan",
    1838: "c_lujiang", 2137: "c_weizhou", 2139: "c_laizhou", 2140: "c_yanzhou",
    2141: "c_xuzhou_1", 2143: "c_haozhou", 2144: "c_yingzhou", 2175: "c_caizhou",
    2176: "c_songzhou", 2179: "c_yan_an", 2180: "c_qinzhou_1", 2181: "c_jingzhou",
    4195: "c_zhenzhou", 4196: "c_haizhou", 4198: "c_fengxiang",
    # South China
    665: "c_duanzhou", 666: "c_jiangling", 667: "c_guangzhou_1", 668: "c_dongguan",
    669: "c_fuzhou_1", 670: "c_qianzhou", 671: "c_tanzhou", 672: "c_langzhou",
    681: "c_xiazhou_1", 682: "c_ezhou", 683: "c_hongzhou", 684: "c_hangzhou",
    685: "c_yangzhou", 686: "c_shuzhou", 1821: "c_jiangning", 1822: "c_suzhou_2",
    1824: "c_wenzhou_2", 1829: "c_quanzhou", 1833: "c_jizhou_3", 1840: "c_guizhou_1",
    2145: "c_runzhou", 2146: "c_xuanzhou", 2147: "c_shezhou", 2148: "c_yuezhou",
    2149: "c_mingzhou_1", 2150: "c_wuzhou", 2151: "c_raozhou", 2152: "c_jian_an",
    2153: "c_tingzhou", 2156: "c_chaozhou", 2157: "c_huizhou_1", 2158: "c_shaozhou_1",
    2159: "c_leizhou", 2160: "c_yazhou", 2161: "c_lianzhou_1", 2162: "c_wuzhou_1",
    2163: "c_liuzhou", 2164: "c_yongzhou_1", 2171: "c_xiangyang", 2173: "c_chenzhou_1",
    2174: "c_hengzhou", 4197: "c_huangzhou",
    # Korea
    733: "c_hwangju", 734: "c_wonju", 735: "c_yangju", 736: "c_sangju",
    737: "c_jeonju", 1013: "c_cheongju", 1845: "c_seogyeong", 2694: "c_myeongju",
    2741: "c_tamna", 2745: "c_gyeongju", 4227: "c_jinju", 4228: "c_naju",
    4229: "c_chungju", 4230: "c_dangseong", 4231: "c_haeju",
    # Manchuria
    726: "c_LIAO_shenyang", 731: "c_BAL_ilanshan", 2107: "c_BAL_ningzhou",
})

# Egypt: the governorates the EU4 provinces stand for (Coptic Egypt is the
# Delta, the Nile valley and the oases of Kharga and Dakhla; the cities,
# Cyrenaica, Sinai, the Red Sea desert and the western oases follow Sunni law).
PROVINCE_COUNTY.update({
    356: "c_barqa", 357: "c_derna", 358: "c_alexandria", 359: "c_fayyum",
    360: "c_qus", 361: "c_cairo", 362: "c_al-buhaira", 363: "c_damietta",
    365: "c_sinai", 1231: "c_aswan", 1233: "c_kharga", 2315: "c_farama",
    2316: "c_al-gharbiya", 2317: "c_bahnasa", 2318: "c_bahriya",
    2319: "c_ushmun", 2320: "c_jabal_quzlum", 2321: "c_qusayr", 2325: "c_alexandria",
    2326: "c_sullum", 4316: "c_sharkiya", 4317: "c_al-buhaira", 4318: "c_cairo",
    4319: "c_qus", 4320: "c_asyut", 4323: "c_farafra",
})

# Japanese provinces with no certain CK3 county yet: reported, never guessed.
UNMAPPED = {}

_cache = {}


def _county_data():
    """({county: [barony ...]}, {barony: province id}, {province id: rite})."""
    if "d" in _cache:
        return _cache["d"]
    root = os.path.join(CK3_GAME, "common", "landed_titles")
    cnty, bprov = {}, {}
    for fn in sorted(os.listdir(root)):
        text = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
        stack = []
        for m in re.finditer(r"(?m)^(\t*)([bcdke]_[\w-]+)\s*=\s*\{", text):
            depth, tid = len(m.group(1)), m.group(2)
            while stack and stack[-1][0] >= depth:
                stack.pop()
            stack.append((depth, tid))
            if not tid.startswith("b_"):
                continue
            end = text.find("\n" + "\t" * depth + "}", m.end())
            pm = re.search(r"province\s*=\s*(\d+)", text[m.end(): end])
            c = next((t for _, t in reversed(stack[:-1]) if t.startswith("c_")), None)
            if pm and c:
                bprov[tid] = int(pm.group(1))
                cnty.setdefault(c, []).append(tid)
    prov_rite = {}
    hroot = os.path.join(CK3_GAME, "history", "provinces")
    for f in os.listdir(hroot):
        t = open(os.path.join(hroot, f), encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r"(?m)^(\d+)\s*=\s*\{(.*?)^\}", t, re.S):
            r = re.search(r'^\s*(?:rite|religion|faith)\s*=\s*"?(\w+)', m.group(2), re.M)
            if r:
                prov_rite[int(m.group(1))] = r.group(1)
    _cache["d"] = (cnty, bprov, prov_rite)
    return _cache["d"]


def county_rite(county):
    cnty, bprov, prov_rite = _county_data()
    for b in cnty.get(county, []):
        r = prov_rite.get(bprov[b])
        if r:
            return r
    return None


def expected(pid):
    """(EU4 religion, CK3 rite, CK3 faith) for a table province, else Nones."""
    from faiths import FAITH_RELIGION, ck3_rites

    rite = county_rite(PROVINCE_COUNTY[pid])
    faith = ck3_rites().get(rite)
    return FAITH_RELIGION.get(faith), rite, faith


def db_religions():
    c = sqlite3.connect(DB)
    out = {p: r for p, r in c.execute("select pid, religion from provinces")}
    c.close()
    return out


def verify():
    """Errors/warnings: each table province carries the religion of its CK3 county's faith."""
    err, warn = [], []
    have = db_religions()
    for pid, county in sorted(PROVINCE_COUNTY.items()):
        rel, rite, faith = expected(pid)
        if rite is None:
            err.append(f"province {pid}: CK3 county {county} has no rite on any barony")
        elif rel is None:
            err.append(f"province {pid}: CK3 county {county} follows the {rite} rite (faith {faith}), which no EU4 religion lifts")
        elif have.get(pid) != rel:
            err.append(f"province {pid}: religion '{have.get(pid)}' but CK3 county {county} follows {rite} ({faith}) -> '{rel}'")
    if UNMAPPED:
        warn.append("Japanese provinces not yet matched to a CK3 county (religion not audited): "
                    + "; ".join(f"{p} {n}" for p, n in sorted(UNMAPPED.items())))
    return err, warn


def apply():
    c = sqlite3.connect(DB)
    n = 0
    for pid in PROVINCE_COUNTY:
        rel = expected(pid)[0]
        if rel and c.execute("update provinces set religion=? where pid=? and religion is not ?", (rel, pid, rel)).rowcount:
            n += 1
    c.commit()
    c.close()
    print(f"{n} province religions rewritten in tags.db")


if __name__ == "__main__":
    if sys.argv[1:] == ["apply"]:
        apply()
    have = db_religions()
    for pid, county in sorted(PROVINCE_COUNTY.items()):
        rel, rite, faith = expected(pid)
        flag = "ok " if have.get(pid) == rel else "FIX"
        print(f"{flag} {pid:5} {county:14} {str(rite):12} {str(faith):16} db={have.get(pid)} expected={rel}")
    for e in verify()[1]:
        print("WARN", e)
