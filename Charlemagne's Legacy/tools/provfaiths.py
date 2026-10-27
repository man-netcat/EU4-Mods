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

# Nubia: Makuria's and Alodia's counties (every county the two Coptic kings
# hold is on the Coptic rite; Wadi el-Milk alone keeps the old Kushite faith).
PROVINCE_COUNTY.update({
    1234: "c_qasr_ibrim", 2322: "c_faras", 1228: "c_dongola", 1229: "c_atbara",
    2797: "c_meroe", 2798: "c_alodia", 1222: "c_gezira", 2799: "c_sennar",
    1217: "c_fazughli",
})

# The Horn of Africa: Abyssinia (k_abyssinia) and Adal (d_adal with the
# kingdom of Adal's other duchies), matched by the Ethiopian, Harari and Somali
# names the EU4 provinces carry; the Beja coast (Kushitism has no CK3 colour to
# lift), the Sidamo/Welayta south and the Somali coast stay unmapped.
PROVINCE_COUNTY.update({
    1227: "c_tigre", 2767: "c_intarta", 2766: "c_serae", 2787: "c_serae",
    2769: "c_lasta", 2768: "c_angot", 1214: "c_amhara", 2772: "c_dembiya",
    2771: "c_semien", 1224: "c_begemder", 1223: "c_gojjam", 2770: "c_agaw_meder",
    1213: "c_showa", 2791: "c_fetegar",
    1211: "c_harar", 1212: "c_zaila", 1208: "c_dakkar", 1209: "c_berbera",
    1215: "c_tadjoura", 1207: "c_fafan", 1210: "c_dawaro", 2761: "c_arusi",
    2773: "c_dakkar", 2764: "c_awssa", 2793: "c_fafan", 2792: "c_makhir", 2790: "c_makhir",
    2786: "c_busaso", 2789: "c_mait",
})

# Horn of Africa, corrected: every province follows the county its holder's
# realm names (the Somali clans, the Afar, Oromo and Sidamo counts, the
# Muslim coast and the pagan highlands each hold their own).
PROVINCE_COUNTY.update({
    1205: "c_mogadishu", 1206: "c_barbacadle", 1207: "c_gode", 1208: "c_fafan", 1209: "c_berbera", 1210: "c_dawaro", 1211: "c_harar", 1212: "c_zaila", 1215: "c_tadjoura", 1218: "c_sidamo", 1232: "c_suakin", 2024: "c_nugaal", 2324: "c_aydhab", 2756: "c_welamo", 2757: "c_kaffa", 2758: "c_wellega", 2759: "c_wellega", 2760: "c_hadya", 2761: "c_arusi", 2762: "c_damot", 2763: "c_berta", 2764: "c_awssa", 2765: "c_edd", 2773: "c_dakkar", 2775: "c_hiraab", 2776: "c_hiraab", 2778: "c_gode", 2779: "c_sitti", 2780: "c_hiraab", 2781: "c_luuq", 2782: "c_hiraab", 2783: "c_hobyo", 2784: "c_mudug", 2785: "c_mareeg", 2786: "c_busaso", 2788: "c_ras_hafun", 2789: "c_mait", 2790: "c_makhir", 2793: "c_fafan", 2795: "c_mareeg"
})

PROVINCE_COUNTY.update({1230: "c_massawa", 1226: "c_badi"})

PROVINCE_COUNTY.update({4158: "c_innarya"})  # Janjiro: Lebna holds Ennarea


# India (Hindusthan, West India, Bengal, the Deccan, Coromandel and Lanka): EU4
# province -> CK3 county by name inference. EU4 uses Mughal-era names where CK3
# has the Sanskrit ones (Ujjain = Ujjayini, Kota = Medapata for Mewar), so each
# pair is a name or a barony of the same name (CK3 files Etawah, Sirhind,
# Gorakhpur, Chaul ... under the county written here), else the county that
# holds the old capital the EU4 province is named for. Provinces whose county is
# not certain stay in UNMAPPED.
PROVINCE_COUNTY.update({
    # Sindh and the Punjab
    503: "c_kutch", 504: "c_debul", 505: "c_siwistan", 2088: "c_sonda", 4503: "c_mansura",
    4504: "c_mansura", 4505: "c_aror", 2072: "c_bhakkar", 506: "c_multan", 2079: "c_kafirkot",
    2086: "c_uch", 4508: "c_uch", 4509: "c_karor", 507: "c_lahur", 4510: "c_shorkot",
    4511: "c_bhera", 4513: "c_dipalpur", 2075: "c_trigarta", 509: "c_kangra",
    2076: "c_sakala", 4449: "c_sakala", 2077: "c_gurjaratra", 2078: "c_bannu",
    # Kashmir and the Himalaya
    508: "c_kasmira", 2074: "c_leh", 4521: "c_skardu", 2073: "c_skardu",
    511: "c_garwhal", 4493: "c_garwhal", 2069: "c_kumaon", 4492: "c_doti", 554: "c_jumla",
    4491: "c_dang", 4485: "c_lumbini", 2070: "c_kaski", 557: "c_kathmandu",
    4484: "c_simaramapura", 4483: "c_yangwarok", 2071: "c_ilam",
    # Delhi, the Doab, Rajasthan east of the Aravallis
    522: "c_delhi", 510: "c_sthanisvara", 4411: "c_sthanisvara", 2062: "c_sthanisvara",
    2060: "c_hastinapura", 2065: "c_tribandapura", 4463: "c_sarasvati",
    4498: "c_sambhal", 4499: "c_vodamayutja", 2061: "c_katehar", 4497: "c_kanyakubja",
    2063: "c_kanyakubja", 524: "c_kanyakubja", 4496: "c_asni", 556: "c_prayaga",
    523: "c_lakhnau", 4494: "c_naimisa", 2094: "c_naimisa", 4495: "c_ayodhya",
    2055: "c_sravasti", 555: "c_jaunpur", 2095: "c_varanasi", 4490: "c_chunar",
    525: "c_gwalior", 528: "c_kota", 4464: "c_kota", 4465: "c_ranthambore",
    4500: "c_sripatha", 519: "c_vairata", 520: "c_vairata", 2064: "c_sakarai",
    # Bundelkhand, Baghelkhand and Malwa
    740: "c_chanderi", 2059: "c_kalpi", 559: "c_mahoba", 4466: "c_mahoba",
    4467: "c_kalanjara", 4459: "c_damoh", 2097: "c_gurgi", 4468: "c_bandhugadha",
    2098: "c_kiranapura", 4461: "c_ujjayini", 2057: "c_vidisa", 2093: "c_dasapura",
    526: "c_dhara", 2056: "c_dadhipadra", 527: "c_burhanpur", 4434: "c_burhanpur",
    4453: "c_thalner",
    # Rajasthan west of the Aravallis, Marwar and Mewar
    512: "c_vikramapura", 2066: "c_nagauda", 4502: "c_nagauda", 4507: "c_reni",
    513: "c_ludrava", 514: "c_mandavyapura", 2067: "c_godwad", 4506: "c_satyapura",
    518: "c_chitrakut", 2058: "c_medapata", 2087: "c_ajayameru", 4501: "c_medapata",
    4462: "c_mohadavasaka",
    # Gujarat
    2053: "c_sarasvata_mandala", 4480: "c_mohadavasaka", 2054: "c_khetaka",
    4457: "c_khetaka", 516: "c_vadodara", 517: "c_navasarika", 4512: "c_navasarika",
    4430: "c_daman", 2051: "c_valabhi", 4456: "c_dhamalpur", 521: "c_dhamalpur",
    2052: "c_dvaraka", 515: "c_bhumilka", 4454: "c_bhumilka", 4455: "c_somnath",
    # Bihar, Nepal Terai, Bengal and Assam
    558: "c_magadha", 4469: "c_rothas", 4472: "c_mudgagiri", 2044: "c_mudgagiri",
    2047: "c_mithila", 4489: "c_mithila", 4487: "c_kusinagara", 4488: "c_simaramapura",
    560: "c_jharkand", 2096: "c_damin_i_koh", 563: "c_gauda", 4479: "c_pundravardhana",
    2045: "c_pundravardhana", 4486: "c_pundravardhana", 4478: "c_madhupur",
    564: "c_bikrampur", 4474: "c_bikrampur", 4475: "c_bikrampur", 561: "c_candradvipa",
    2039: "c_candradvipa", 4473: "c_samatata", 2081: "c_radha", 4476: "c_nabadwipa",
    4477: "c_saptagrama", 2038: "c_midnapore", 4471: "c_mallabhum",
    562: "c_kamatapur", 2042: "c_kamarupanagara", 566: "c_haruppeswara",
    571: "c_haruppeswara", 4440: "c_haruppeswara", 2040: "c_kundina", 567: "c_srihatta",
    573: "c_dimapur", 570: "c_dimapur", 2041: "c_manipur", 2091: "c_karmanta",
    # Orissa, Chhattisgarh and Gondwana
    552: "c_kataka", 2043: "c_viraja", 2049: "c_khinjali_mandala", 4441: "c_puri",
    4450: "c_khijjingakota", 553: "c_sambalpur", 4451: "c_suvarnapura",
    4447: "c_suvarnapura", 2082: "c_rayapura", 4452: "c_ratanpur", 547: "c_cakrakuta",
    4445: "c_cakrakuta", 4448: "c_swetaka_mandala", 2048: "c_khinjali_mandala",
    550: "c_tripuri", 551: "c_tripuri", 2092: "c_ramagiri", 4458: "c_chauragarh",
    4460: "c_chauragarh",
    # Maharashtra, Berar and the Konkan
    529: "c_surparaka", 2089: "c_surparaka", 530: "c_panaji", 4429: "c_panaji",
    2030: "c_kanara", 531: "c_kanara", 4427: "c_kanara", 544: "c_trikuta",
    4433: "c_trikuta", 2036: "c_trikuta", 545: "c_devagiri", 4437: "c_mulaka",
    4432: "c_kondana", 2034: "c_kondana", 1946: "c_karahataka", 4431: "c_kolhapur",
    4435: "c_naldurg", 569: "c_taradavadi", 546: "c_ramagiri", 548: "c_acalapura",
    2050: "c_canda", 4442: "c_vatsagulma", 4443: "c_vatsagulma", 4438: "c_ashmaka",
    2028: "c_mahur",
    # Karnataka, Telingana, Andhra and the Tamil country
    2035: "c_kalyani", 1948: "c_kalyani", 2029: "c_alupa", 4413: "c_alupa",
    2032: "c_banavasi", 532: "c_idatarainadu", 4428: "c_idatarainadu",
    2033: "c_vaijayanti", 533: "c_srirangapatna", 4421: "c_talakad", 2031: "c_muluvagil",
    4422: "c_parivi", 4426: "c_uchangidurga", 4423: "c_gutti", 4424: "c_gutti",
    541: "c_adoni", 1949: "c_candragiri", 2090: "c_renandu", 542: "c_racakonda",
    4436: "c_racakonda", 4439: "c_katukuru", 2037: "c_orangallu", 543: "c_nallamala",
    4425: "c_nallamala", 4419: "c_nallamala", 2083: "c_vengipura", 2084: "c_mosala",
    549: "c_vizagipatam", 2080: "c_kalinganagar", 4418: "c_nellore", 4420: "c_candragiri",
    534: "c_eranad", 535: "c_kerala", 537: "c_venadu", 4410: "c_venadu",
    536: "c_madurai", 2101: "c_madurai", 538: "c_kongu", 4414: "c_kongu",
    4412: "c_uraiyur", 2085: "c_tagadur", 2026: "c_cholamandalam", 4415: "c_cholamandalam",
    4416: "c_cholamandalam", 540: "c_cholamandalam", 1947: "c_tiruvannamalai",
    2027: "c_candragiri", 539: "c_kanchipuram", 4417: "c_kanchipuram",
    # Lanka
    572: "c_kotte", 4408: "c_kotte", 2099: "c_kandy", 2100: "c_phiti", 4409: "c_trincomalee",
    4407: "c_rohana",
})

# Burma and Indo-China, by name inference like India: each EU4 province is paired with the CK3
# county of the same name or the county holding the barony it is named for (Moulmein is
# Mawlamyine in Thaton, Ayutthaya sits in Nakhon Pathom, Savanh Nakhone is Mouang Camphon
# in Sanasomboon); the rest take the county of the nearest named province of their area.
PROVINCE_COUNTY.update({
    # Kachin, upper and central Burma, the Chindwin
    582: "c_myitkyina", 2395: "c_putao", 2396: "c_monyin", 4404: "c_momauk", 4405: "c_takon",
    581: "c_sagaing", 584: "c_kyaukse", 2399: "c_pagan", 585: "c_toungoo", 4394: "c_minbu",
    4395: "c_yamethin", 4396: "c_sriksetra", 580: "c_kale", 2397: "c_kale", 2398: "c_kale",
    4393: "c_hanlan",
    # Lower Burma and Arakan
    586: "c_pegu", 590: "c_thaton", 2403: "c_thaton", 1815: "c_kusumi", 4399: "c_dagon",
    568: "c_ramu", 579: "c_vaisali", 2402: "c_sandoway",
    # the Shan hills and Karenni
    583: "c_hsenwi", 2400: "c_hsenwi", 588: "c_mongnai", 4398: "c_mongnai", 4397: "c_nyaungshwe",
    4406: "c_nyaungshwe", 587: "c_moeng_laem", 2401: "c_mae_hong_son",
    # Vietnam and the Red River
    610: "c_simhapura", 2373: "c_simhapura", 1016: "c_nghe_an", 4821: "c_nghe_an",
    613: "c_thang_long", 616: "c_lam_tay", 2372: "c_hai_dong", 4819: "c_nam_dinh",
    4820: "c_quoc_oai",
    # Laos
    615: "c_luang_prabang", 4837: "c_luang_prabang", 1844: "c_vien_chan", 2371: "c_quoc_oai",
    2381: "c_chiang_khaeng", 614: "c_vien_chan", 611: "c_salo_tai", 2384: "c_ku_kaeo",
    2385: "c_ku_kaeo", 2382: "c_sanasomboon", 4840: "c_sanasomboon", 608: "c_stung_treng",
    4838: "c_mukdahan", 4839: "c_ubon_ratchathani",
    # Siam
    600: "c_nakhon_pathom", 4831: "c_nakhon_pathom", 603: "c_mueang_phra_rot",
    4830: "c_mueang_phra_rot", 4832: "c_lop_buri", 4836: "c_lop_buri", 4834: "c_khu_bua",
    601: "c_sukhothai", 2388: "c_phetchabun", 4833: "c_phetchabun", 2389: "c_chakangrao",
    589: "c_haripunjaya", 4841: "c_haripunjaya", 602: "c_ngoenyang", 1817: "c_nan_asia",
    4842: "c_lampang", 612: "c_dong_si_mahosot", 2383: "c_dong_si_mahosot", 2386: "c_canasha",
    # Cambodia and the Mekong
    604: "c_angkor_borey", 2380: "c_angkor_borey", 2379: "c_pursat", 4825: "c_pursat",
    4826: "c_botum_sakor", 609: "c_angkor", 1823: "c_stung_treng", 2378: "c_kracheh_nokor",
    4827: "c_sambhupura", 4828: "c_prea_vihear", 605: "c_baigaur", 2376: "c_kracheh_nokor",
    2377: "c_ca_mau", 4829: "c_vyadhapura",
    # Champa and the highlands
    606: "c_panduranga", 607: "c_vijaya", 1022: "c_indrapura", 4822: "c_indrapura",
    2374: "c_kauthara", 2375: "c_ratanakiri", 4823: "c_pleiku", 4824: "c_pleiku",
})

# No county carries these names: each takes the county of the nearest province
# of the same area (user rule - no province may stay uncolonized).
PROVINCE_COUNTY.update({
    2046: "c_suvarnagram",  # Nasirabad (Mymensingh): beside Dacca/Haibatnagar
    4444: "c_racakonda",    # Manidurg (Medak): Golconda is the nearest province
    4446: "c_suvarnapura",  # Kalahandi: south of Patna-Garjat and Sonpur
    4470: "c_jharkand",     # Soumelpur (Chota Nagpur): between Jharkand and Mahurbanj
})
# China: the provinces of the Tang realm the first pass left unpaired or paired wrongly, by
# name (Jingzhou is Jiangling, Bozhou is Bochuan, Hetao the Wuyuan of Yanzhou) and then by
# the nearest Tang-era prefecture; the tribal and Tai polities of the south-west and the
# Onggud of the Langshan keep their own states (Lingyun is Guile's Tianzhou region, Cao Bang
# the Nong of Xiyuan, Guiyang the Xie of Zangke).
PROVINCE_COUNTY.update({
    666: "c_danzhou_1", 2172: "c_jiangling", 616: "c_siyuan", 664: "c_guile",
    673: "c_shizhou_1", 674: "c_yingzhou_4", 4199: "c_sizhou", 2168: "c_bochuan",
    679: "c_chengdu", 680: "c_yuzhou_2", 4211: "c_tongchuan", 2169: "c_jianzhou_1",
    4212: "c_jiazhou", 4213: "c_luzhou_2", 2142: "c_chuzhou_2", 2138: "c_zichuan",
    2136: "c_huaian", 4194: "c_pinzhou", 2177: "c_xinzhou", 2178: "c_longde",
    2183: "c_hezhou_2", 701: "c_xiazhou", 702: "c_shengzhou", 709: "c_alxa",
    4223: "c_wuyuan", 2747: "c_langshan", 4670: "c_keyimen",
})

# Maritime South-East Asia (Malaya, Indonesia, the Philippines and the Moluccas), by name where
# CK3 has the place (Johor, Kedah, Brunei, Banjar, Bali, Gorontalo, Ternate, Tondo ...) and else by
# the county of the same coast or river basin: EU4 splits the islands into more provinces than
# CK3 has counties, so several provinces share a county.
PROVINCE_COUNTY.update({
    # Sumatra
    617: "c_SUM_lambri", 2673: "c_SUM_perlak", 2674: "c_SUM_perlak", 2685: "c_SUM_perlak",
    4809: "c_SUM_panai", 618: "c_SUM_panai", 620: "c_SUM_pekanbaru", 2675: "c_SUM_rokan",
    4810: "c_SUM_panai", 621: "c_SUM_bengkulu", 622: "c_SUM_palembang", 623: "c_SUM_lampung",
    2678: "c_SUM_bangka-belitung", 2679: "c_SUM_bangka-belitung", 659: "c_SUM_lingga",
    2676: "c_SUM_indragiri", 2677: "c_SUM_jambi", 4816: "c_SUM_indragiri", 619: "c_SUM_panai",
    2682: "c_SUM_minangkabau", 2684: "c_nias", 4811: "c_SUM_barus", 2680: "c_SUM_bengkulu",
    2681: "c_SUM_minangkabau", 2683: "c_mentawai", 4817: "c_SUM_minangkabau",
    4818: "c_SUM_riak_nan_berbedur",
    # the Malay peninsula and the Isthmus of Kra
    593: "c_THAI_tambralinga", 2390: "c_THAI_tambralinga", 2391: "c_THAI_takua_pa",
    598: "c_MAL_pahang", 599: "c_MAL_kelantan", 2393: "c_MAL_gelanggi", 4814: "c_MAL_semantan",
    597: "c_MAL_johor", 2686: "c_riau", 4815: "c_MAL_johor", 594: "c_MAL_patani",
    2394: "c_MAL_kedah", 4812: "c_MAL_gangganegara", 4813: "c_MAL_kedah",
    595: "c_MAL_gangganegara", 596: "c_MAL_johor", 2392: "c_MAL_gangganegara",
    591: "c_THAI_tenasserim", 2404: "c_THAI_tenasserim", 592: "c_THAI_phetchaburi",
    2387: "c_THAI_phetchaburi", 4835: "c_THAI_phetchaburi",
    574: "c_andamans", 1248: "c_maldives", 1101: "c_maldives", 1998: "c_JAV_sunda", 1999: "c_JAV_sunda",
    # Borneo
    638: "c_BOR_martapura", 2710: "c_BOR_berau", 2711: "c_BOR_kutai_utara", 2712: "c_BOR_martapura",
    4799: "c_BOR_kutai_utara", 636: "c_BOR_brunei", 2704: "c_BOR_rajang", 2705: "c_BOR_iban",
    4805: "c_BOR_rajang", 4806: "c_BOR_iban", 640: "c_BOR_sukadana", 2706: "c_BOR_sukadana",
    4802: "c_BOR_sukadana", 4803: "c_BOR_sintang", 4804: "c_BOR_santubong", 639: "c_BOR_banjar",
    2707: "c_BOR_taiao", 2708: "c_BOR_sampit", 4800: "c_BOR_banjar", 4801: "c_BOR_banjar",
    637: "c_BOR_kudat", 2703: "c_BOR_lahad_datu", 2709: "c_BOR_berau",
    # Java and the Lesser Sundas
    627: "c_JAV_lumajang", 2691: "c_JAV_janggala", 4794: "c_JAV_janggala", 626: "c_JAV_mataram",
    2689: "c_JAV_kalingga", 2690: "c_JAV_mataram", 4792: "c_JAV_kalingga", 625: "c_JAV_galuh",
    2688: "c_JAV_cimanuk", 4791: "c_JAV_cimanuk", 631: "c_IDO_bali", 632: "c_IDO_lombok_and_sumbawa",
    634: "c_IDO_humba", 2693: "c_IDO_lombok_and_sumbawa", 628: "c_JAV_janggala",
    629: "c_JAV_kalingga", 2692: "c_JAV_madura", 4793: "c_JAV_mataram", 624: "c_JAV_sunda",
    630: "c_JAV_sunda", 2687: "c_JAV_sunda", 4790: "c_JAV_sunda",
    # Sulawesi and the Moluccas
    645: "c_SuMa_buru-sula", 646: "c_SuMa_seram", 647: "c_SuMa_seram", 2717: "c_SuMa_buru-sula",
    643: "c_SuMa_mori", 644: "c_SuMa_wenang", 2713: "c_SuMa_gorontalo", 2714: "c_SuMa_banawa",
    4845: "c_SuMa_sampaga", 642: "c_SuMa_konawe", 2715: "c_SuMa_luwu", 2716: "c_SuMa_butun",
    4796: "c_SuMa_moronene", 641: "c_SuMa_siang", 4795: "c_SuMa_ajatappareng",
    4797: "c_SuMa_ajatappareng", 4798: "c_SuMa_ajatappareng", 648: "c_SuMa_bacan",
    649: "c_SuMa_ternate", 650: "c_SuMa_tidore",
    # the Philippines
    657: "c_PHI_samtoy", 658: "c_PHI_cagayan_valley", 2698: "c_PHI_pangasinan", 4348: "c_PHI_igorot",
    656: "c_PHI_tondo", 2697: "c_PHI_tondo", 2699: "c_PHI_ibalong", 4349: "c_PHI_kalilayan",
    4350: "c_PHI_ma-i", 2701: "c_PHI_mandaya", 2702: "c_PHI_butuan", 4355: "c_PHI_calagan",
    652: "c_PHI_maguindanao", 653: "c_PHI_lanao", 4354: "c_PHI_zamboanga", 654: "c_PHI_samar",
    2700: "c_PHI_panay", 4351: "c_PHI_buglas", 4352: "c_PHI_bool_and_cebu", 4353: "c_PHI_tandaya",
    651: "c_PHI_sulu", 655: "c_PHI_south_palawan", 4356: "c_PHI_taytay",
    # New Guinea and the eastern islands
    1237: "c_papua_selatan", 2719: "c_sran", 2720: "c_sran", 2721: "c_papua_selatan",
    2722: "c_papua_selatan", 1245: "c_kepala_burung", 2718: "c_kepala_burung",
    2723: "c_papua_selatan", 2724: "c_papua_selatan", 633: "c_IDO_galiyao",
    635: "c_IDO_sonba_i", 2695: "c_IDO_wehale", 2696: "c_IDO_barat_daya", 2725: "c_aru",
})

# The Sahel and West Africa (Darfur and Kordofan to Senegambia and the Guinea coast), by name where CK3
# has the place (Kano, Oyo, Gao, Jenne, Kong, Futa Jalon ...) and else by the county of the same
# river, oasis or people (Zamfara is Sokoto's country, Gwiriko the Dyula of Bobo, the Aoukar is Wagadu).
PROVINCE_COUNTY.update({
    # Darfur, Kordofan and the Nile-side of Sudan
    774: "c_masalit", 1219: "c_kordofan", 2801: "c_el_fasher", 2802: "c_dar_al-said",
    2932: "c_east_darfur", 1216: "c_south_kordofan", 1221: "c_south_kordofan", 2800: "c_gezira",
    # Lake Chad: Kanem, Bagirmi and Bornu
    1158: "c_kanem", 1159: "c_baguirmi", 2286: "c_kera", 2287: "c_kotoko", 2288: "c_kotoko",
    1157: "c_bornu", 1160: "c_wandala", 2282: "c_munio", 2283: "c_kagha", 2284: "c_yau",
    # the central Sahara and the Air
    1156: "c_tahoua", 2272: "c_air", 2273: "c_tahoua", 2274: "c_air", 2276: "c_takkeda",
    1127: "c_tessalit", 1128: "c_walata", 1129: "c_tessalit", 1130: "c_tadmekka",
    2271: "c_tadmekka", 2275: "c_bilma", 2277: "c_bilma", 2475: "c_djado",
    # the Niger bend, Songhay and the Dendi
    1142: "c_dendi", 2268: "c_dyamare", 2269: "c_zarma", 2270: "c_zarma", 1132: "c_tirakka",
    1133: "c_gao", 2260: "c_mema", 2262: "c_kouga", 2264: "c_gondo",
    # Ghana, Tekrur and Senegambia
    2243: "c_tichitt", 2245: "c_awkar", 2246: "c_awkar", 2247: "c_hodh", 1115: "c_dhraina",
    2237: "c_takrur", 2240: "c_galam", 2244: "c_tagant", 1112: "c_dhraina", 1113: "c_kayor",
    1116: "c_jolof", 2239: "c_saalum", 1111: "c_dhraina", 1096: "c_baol", 1114: "c_kaabu",
    1117: "c_futa_jalon", 2238: "c_wuli", 1118: "c_temne", 1119: "c_bassa", 2241: "c_geba",
    2242: "c_kasa",
    # Mali, the Jenne country and the Dyula states
    1120: "c_bambuk", 1121: "c_bure", 1124: "c_sikasso", 2248: "c_dakajalan", 1123: "c_bindugu",
    1131: "c_massina", 2249: "c_sibi_mali", 2250: "c_bindugu", 1134: "c_jenne", 2259: "c_kurmina",
    2261: "c_dodugu", 2263: "c_bandiagara", 1122: "c_worodugu", 1125: "c_kong", 2252: "c_lobi",
    2253: "c_dyulaso",
    # the Volta basin: the Mossi, Gurma, Dagomba and the Akan
    1135: "c_yatenga", 1136: "c_gurma", 1137: "c_wagadugu", 2265: "c_oudalan",
    2266: "c_upper_gurma", 2292: "c_po", 2295: "c_pendjari", 2256: "c_dagomba",
    2267: "c_kuisugu", 2255: "c_bonduku", 1138: "c_kumasi", 2254: "c_bono",
    2257: "c_adanse", 1139: "c_fante", 2258: "c_fante", 1126: "c_dabou",
    # Hausaland and the middle Niger
    1155: "c_kano", 2280: "c_rano", 2281: "c_rano", 1148: "c_gobir", 1149: "c_katsina",
    2279: "c_daura", 1150: "c_sokoto", 1154: "c_zaria", 2278: "c_kebbi", 2293: "c_yauri",
    1144: "c_oyo", 1145: "c_nupe", 1146: "c_ife", 1152: "c_igala", 1153: "c_kwararafa",
    1161: "c_bauchi", 1162: "c_kwararafa", 1249: "c_garoua", 2285: "c_diamare",
    # Borgu, Yorubaland, the Bight of Benin and the Niger delta
    1143: "c_nikki", 1140: "c_abomey", 2291: "c_ketu", 1141: "c_ifonyin", 1147: "c_benin",
    2289: "c_owu", 2290: "c_ijebu", 2294: "c_edo", 1151: "c_ijaw", 1163: "c_ibibo",
})

# The Swahili coast and the Jubba, west Siberia and the last Mongolian, Horn and Russian provinces,
# by name (Lamu, Pate, Zanzibar, Tanga, Mombasa, Malindi, Taveta, Yeniseysk, Chuna, Komi is Perm) and
# otherwise by the county of the same river, coast or people.
PROVINCE_COUNTY.update({
    1204: "c_lamu", 2774: "c_jilib", 2796: "c_pate", 1196: "c_mrima", 1197: "c_mrima",
    1198: "c_mrima", 1199: "c_mrima", 1201: "c_zanzibar", 1200: "c_tanga", 1202: "c_mombasa",
    1203: "c_malindi", 2777: "c_jubba", 4051: "c_ewaso_ngiro", 4052: "c_el_waak",
    1273: "c_taveta", 1925: "c_mto_tana", 4053: "c_marsabit", 4054: "c_kilimanjaro",
    4060: "c_kirinyaga", 4055: "c_tanga", 4058: "c_mrima", 2794: "c_mareeg",
    1067: "c_narim", 1070: "c_koda", 2430: "c_yenisei", 1061: "c_yenisei", 2431: "c_yenisei",
    2436: "c_chuna", 1069: "c_sosva", 1072: "c_kazym", 2445: "c_kazym",
    2117: "c_sharga", 2187: "c_SW_zhongcheziguo", 4202: "c_SW_dongcheziguo",
    4674: "c_SW_hulunbuir", 4256: "c_ustyug", 1780: "c_perm",
})

# Independent CK3 states that had no province because a neighbour took several: one of the
# neighbour's spare provinces goes to each (Sambas, Tanah Taman, Tabalung, Raja Ampat, Baydhabo,
# Lag Dera, Naga, Munda, Nandana, Tsugaru, Tamna ...), where the EU4 province lies in or beside
# the county. Smaller states with no province of their own are lost, as the map is coarser.
PROVINCE_COUNTY.update({
    640: "c_BOR_sambas", 4806: "c_BOR_tanah_taman", 4801: "c_BOR_tabalung",
    2718: "c_SuMa_raja_ampat", 4816: "c_SUM_dharmasraya", 2679: "c_SUM_east_sumatra",
    591: "c_thanbyuzayat", 2385: "c_muang_fa_daet", 2373: "c_ma_linh", 2781: "c_baydhabo",
    4052: "c_lag_dera", 2801: "c_dar-al-rih", 2800: "c_naga", 1139: "c_ewe",
    2257: "c_wassa", 4470: "c_munda", 2078: "c_nandana", 4131: "c_tsugaru",
})

# Manchuria, by name where CK3 has the place (Hulunbuir, Birija, Jixi, Ningguta's Ningzhou,
# Shenyang) and otherwise by the county of the same river or valley: the Amur and Shiwei counties
# follow the tag that already held each province, Balhae's own counties are paired by their Chinese,
# Manchu or Korean names (Huncun is Longyuan, Hulan the Huligai, Girin Changchun, Hetu Ala Xiande).
PROVINCE_COUNTY.update({
    724: "c_SW_hulunbuir", 1053: "c_SW_hongxingan", 2102: "c_SW_heilonghean", 4664: "c_SW_damoguo", 4674: "c_SW_lingxiguo",
    727: "c_SW_suihua", 728: "c_SW_suihua", 2185: "c_SW_puyuzhou", 1048: "c_eman_tudali",
    1049: "c_eman_turma", 1050: "c_eman_heishuiyang", 2103: "c_eman_yam_alin",
    2104: "c_eman_birija", 2105: "c_eman_boli", 4214: "c_eman_molihewen", 4215: "c_eman_mohean",
    4216: "c_eman_yerenhe", 4659: "c_eman_urehokto", 4662: "c_eman_nimen", 4660: "c_BAL_delizhen",
    729: "c_BAL_ningzhou",
    730: "c_BAL_changchun", 2110: "c_BAL_fuzhou", 2111: "c_BAL_west_hyeondeok",
    4201: "c_BAL_east_hyeondeok", 2188: "c_BAL_makhil", 4217: "c_BAL_west_makhil",
    4200: "c_BAL_huligai", 4663: "c_BAL_jixi", 2108: "c_BAL_southyongwon",
    4653: "c_BAL_northyongwon", 4654: "c_BAL_yongcheon", 4661: "c_BAL_dongju",
    1850: "c_BAL_namhae", 2106: "c_BAL_east_jangryeong", 2186: "c_BAL_west_jangryeong",
    4655: "c_BAL_sokju", 4656: "c_BAL_xinzhou", 2112: "c_LIAO_yinzhou", 2113: "c_LIAO_zhenzhou",
    4652: "c_LIAO_diezhou",
})

# Balhae's Korean side, by Balhae's own prefectures: Nyeongbyeon and Taecheon (Taeju), Ganggye on the
# upper Yalu (West Amnok), Hamhung is Balhae's Nanhai, Kyongwon the Fengzhou/Longyuan country, and
# Boduna the Boduo clan's seat at Makhil. Yaran joins Shilimian in the Sokju (Chenzhou) country.
PROVINCE_COUNTY.update({
    2744: "c_taeju", 4232: "c_BAL_west_amnok", 732: "c_BAL_namhae", 2742: "c_BAL_fengzhou",
    2743: "c_BAL_northyongwon", 2109: "c_BAL_west_makhil", 1850: "c_BAL_sokju",
})

# The Kirghiz Khaganate's 30 provinces, by name where CK3 has the place (Kulunda, Tomsk, Yenisei, Uliastai,
# Karakorum, Chulym, Barnaul, Om, Khar Us for Kobdo, Narym) and else by the nearest county of the same
# river or range; the Naiman west, Tuva, Dzungaria and Sibir parts are the lands the fall of the Khaganate frees.
PROVINCE_COUNTY.update({
    480: "c_kulunda", 1064: "c_tomsk", 1061: "c_yenisei", 1065: "c_kuzbas", 1066: "c_terektai",
    2430: "c_kiia", 2431: "c_taskyl", 2432: "c_chulym", 2434: "c_barnaul", 4688: "c_sartlan",
    2436: "c_chuna", 719: "c_uliastai", 2117: "c_sharga", 2189: "c_tarvagatai", 2190:
    "c_karakorum", 2193: "c_ongi", 4668: "c_telmen", 4679: "c_tomorbulag", 4680: "c_zarman", 718:
    "c_khar_us", 4681: "c_tsambagarau", 4682: "c_ikh_bogd", 4222: "c_ulaangom", 716:
    "c_central_tannu", 714: "c_tengerge", 4683: "c_burqin", 4684: "c_altay", 2355: "c_narym_DZU",
    4689: "c_omsk", 4687: "c_pavlodar", 4686: "c_kainsk",
})

UNMAPPED_INDIA = {}

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
    # no barony carries a rite (CK3 leaves some holdingless counties bare): the
    # county holder's own rite at 867 stands in
    import ck3
    import rites
    import state867

    h = state867.holder(county)
    body = ck3.load_chars().get(h) if h else None
    return rites.rite_at(body) if body else None


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
