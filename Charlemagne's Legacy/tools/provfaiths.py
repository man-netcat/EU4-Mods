#!/usr/bin/env python3
"""Province religions that track CK3's counties (curated, region by region).

A province's religion is the religion lifting the CK3 faith of the county it
corresponds to: the county's capital barony carries a `rite` in CK3's
history/provinces, the rite belongs to a faith (rite_types), and
the faith is the province's religion, under CK3's own key. The EU4
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

# Old World provinces paired with the CK3 county or barony of the same name (exact
# name, unique in CK3, and in the de jure kingdom of the other provinces of its EU4
# area): Europe, the Middle East, Central Asia and the rest of the Old World that no
# earlier region table covered. Provinces whose names differ are paired by hand below.
PROVINCE_COUNTY.update({
    1: "c_upland", 2: "c_ostergotland", 3: "c_more", 9: "c_halsingland", 12: "c_sjaelland",
    13: "c_slesvig", 14: "c_fyn", 25: "c_gutland", 26: "c_halland", 27: "c_finland",
    28: "c_nyland", 30: "c_viborg", 38: "c_vidzeme", 40: "c_memel", 42: "c_wormditt",
    44: "c_hamburg", 45: "c_lubeck", 46: "c_rostock", 47: "c_rugen", 50: "c_berlin",
    51: "c_ruppin", 52: "c_magdeburg", 53: "c_luneburg", 54: "c_stade", 55: "c_oldenburg",
    56: "c_osnabruck", 57: "c_brunswick", 59: "c_wittenberg", 61: "c_dresden", 62: "c_mersenburg",
    65: "c_munchen", 66: "c_bamberg", 67: "c_nurnberg", 68: "c_kempten", 69: "c_dortmund",
    70: "c_wurttemberg", 71: "c_ansbach", 72: "c_breisgau", 74: "c_baden", 76: "c_salzburg",
    77: "c_speyer", 78: "c_mainz", 79: "c_wurzburg", 80: "c_trier", 82: "c_lippe", 83: "c_nassau",
    84: "c_bergh", 86: "c_munster", 87: "c_guines", 90: "c_brugge", 91: "c_hainaut",
    92: "c_brabant", 93: "c_liege", 95: "c_antwerpen", 96: "c_zeeland", 97: "c_holland",
    98: "c_nedersticht", 101: "c_genoa", 102: "c_nice", 105: "c_parma", 106: "c_modena",
    107: "c_brescia", 108: "c_verona", 109: "c_mantua", 110: "c_trent", 111: "c_friuli",
    112: "c_venezia", 113: "c_ferrara", 114: "c_ravenna", 115: "c_pisa", 116: "c_firenze",
    117: "c_siena", 118: "c_roma", 119: "c_ancona", 120: "c_abruzzi", 121: "c_napoli",
    122: "c_apulia", 124: "c_messina", 125: "c_palermo", 126: "c_malta", 127: "c_logudoro",
    128: "c_karnten", 133: "c_linz", 134: "c_vienna", 135: "c_sopron", 136: "c_cetina",
    137: "c_ragusa", 141: "c_beograd", 142: "c_buthrotum", 146: "c_attica", 148: "c_thessalonika",
    150: "c_lower_dniepr", 151: "c_byzantion", 153: "c_visegrad", 154: "c_hont", 155: "c_bekes",
    156: "c_temes", 157: "c_bihar", 162: "c_zemplen", 164: "c_naxos", 165: "c_bern",
    166: "c_zurich", 168: "c_bayeux", 173: "c_labourd", 174: "c_bordeaux", 175: "c_armagnac",
    176: "c_bearn", 177: "c_maine", 178: "c_anjou", 179: "c_berry", 181: "c_rethel",
    183: "c_ile_de_france", 185: "c_brie_francaise", 186: "c_reims", 188: "c_metz",
    190: "c_bourbon", 191: "c_nevers", 194: "c_perigord", 195: "c_limousin", 196: "c_toulouse",
    198: "c_rouergue", 199: "c_auvergne", 200: "c_montpellier", 201: "c_provence",
    202: "c_venaissin", 205: "c_savoie", 209: "c_viscaya", 210: "c_navarra", 211: "c_huesca",
    212: "c_girona", 213: "c_barcelona", 214: "c_zaragoza", 215: "c_valladolid",
    216: "c_salamanca", 217: "c_madrid", 218: "c_badajoz", 219: "c_toledo", 220: "c_valencia",
    221: "c_murcia", 222: "c_almeria", 223: "c_granada", 224: "c_sevilla", 225: "c_cordoba",
    227: "c_lisboa", 228: "c_castelo_branco", 229: "c_beja", 231: "c_porto", 232: "c_braganza",
    233: "c_cornwall", 234: "c_hampton", 236: "c_middlesex", 237: "c_oxfordshire", 238: "c_essex",
    239: "c_gloucestershire", 240: "c_shropshire", 243: "c_lincolnshire", 244: "c_lancashire",
    245: "c_north_riding", 246: "c_northumberland", 248: "c_lothian", 249: "c_ayrshire",
    251: "c_mearns", 252: "c_inverness", 253: "c_outer_hebrides", 254: "c_poznanska",
    255: "c_kaliska", 257: "c_czerska", 258: "c_sieradzka", 259: "c_sandomierska",
    260: "c_lubelska", 262: "c_krakowska", 263: "c_ratibor", 264: "c_breslau", 265: "c_brno",
    266: "c_praha", 267: "c_plzen", 268: "c_suceava", 270: "c_trakai", 274: "c_pskov",
    275: "c_polotsk", 276: "c_minsk", 277: "c_french_leon", 278: "c_pinsk", 285: "c_kaffa",
    287: "c_tmutarakan", 289: "c_chernigov", 290: "c_hradyzk", 293: "c_smolensk", 294: "c_tver",
    295: "c_moskva", 298: "c_kursk", 299: "c_voronezh", 300: "c_tula", 301: "c_ryazan",
    302: "c_tambov", 304: "c_penza", 305: "c_perm", 307: "c_vladimir", 308: "c_yaroslavl",
    310: "c_novgorod", 312: "c_beloozero", 314: "c_vologda", 327: "c_cilicia", 330: "c_trebizond",
    332: "c_marash", 333: "c_mallorca", 334: "c_tangiers", 335: "c_melilla", 336: "c_tlemcen",
    337: "c_orania", 339: "c_bejaia", 340: "c_constantine", 341: "c_tunis", 342: "c_gharb",
    347: "c_ifni", 349: "c_figuig", 351: "c_biskra", 353: "c_gabes", 368: "c_madeira",
    369: "c_orkney", 370: "c_vestisland", 374: "c_leinster", 377: "c_aleppo", 379: "c_jerusalem",
    382: "c_damascus", 383: "c_tabuk", 384: "c_medina", 385: "c_mecca", 386: "c_asir",
    388: "c_mandab", 389: "c_mahra", 391: "c_najran", 392: "c_al-arid", 394: "c_qatif",
    397: "c_tiberias", 399: "c_batina", 400: "c_muscat", 402: "c_mahra", 403: "c_nizwa",
    408: "c_basra", 409: "c_karbala", 410: "c_baghdad", 411: "c_mosul", 412: "c_ahvaz",
    414: "c_hamadan", 415: "c_kirkuk", 416: "c_tabriz", 419: "c_hayk", 420: "c_aran",
    421: "c_shirvan", 423: "c_tbilisi", 424: "c_ardabil", 426: "c_amol", 429: "c_isfahan",
    433: "c_yazd", 435: "c_zaranj", 436: "c_qain", 439: "c_mangyshlak", 441: "c_khiva",
    442: "c_bukhara", 445: "c_merv", 446: "c_herat", 450: "c_balkh", 451: "c_kabul",
    452: "c_badakhshan", 454: "c_samarkand", 459: "c_taraz", 461: "c_almaty", 462: "c_odishi",
    464: "c_astrakhan", 468: "c_azov", 469: "c_saqsin", 565: "c_paro", 576: "c_kalat",
    662: "c_dali", 677: "c_lhasa", 707: "c_yumen", 708: "c_ganzhou", 739: "c_kashgar",
    771: "c_vitebsk", 1055: "c_baigaluuls", 1068: "c_tomsk", 1071: "c_tara", 1074: "c_sibir",
    1075: "c_tyumen", 1076: "c_kurgan", 1077: "c_ural", 1078: "c_man", 1080: "c_pelym",
    1081: "c_ashli", 1082: "c_kazan", 1083: "c_martyuba", 1099: "c_socotra", 1110: "c_agadir",
    1318: "c_spis", 1742: "c_frankfurt", 1743: "c_cambray", 1744: "c_antwerpen", 1746: "c_burgos",
    1747: "c_caceres", 1748: "c_andujar", 1749: "c_cadiz", 1750: "c_alicante", 1751: "c_ceuta",
    1753: "c_manturovo", 1755: "c_ustyug", 1758: "c_hannover", 1759: "c_brandenburg",
    1760: "c_koblenz", 1762: "c_kassel", 1764: "c_burgas", 1768: "c_lienz", 1772: "c_poszony",
    1774: "c_treviso", 1826: "c_lika", 1827: "c_rashka", 1828: "c_donjikraji", 1842: "c_narva",
    1849: "c_hama", 1851: "c_coimbra", 1853: "c_ohrid", 1856: "c_abkhazia", 1859: "c_torun",
    1860: "c_norfolk", 1861: "c_derby", 1862: "c_cremona", 1863: "c_graz", 1864: "c_somogy",
    1866: "c_namur", 1867: "c_breisgau", 1868: "c_augsburg", 1869: "c_zurich", 1872: "c_ulm",
    1873: "c_grisons", 1874: "c_bremen", 1876: "c_frankfurt", 1878: "c_aachen", 1879: "c_alencon",
    1880: "c_sundgau", 1882: "c_annaba", 1930: "c_aland", 1933: "c_bari", 1935: "c_zemigalians",
    1937: "c_grodno", 1938: "c_lomzynska", 1940: "c_belz", 1941: "c_turov", 1942: "c_zhytomyr",
    1945: "c_novgorod_seversky", 1951: "c_hunyad", 1953: "c_szabolcs", 1955: "c_kholmogory",
    1956: "c_suzdal", 1958: "c_kargopol", 1959: "c_valdai", 1961: "c_novgorod", 1965: "c_samar_VB",
    1978: "c_shetland", 1981: "c_bornholm", 1982: "c_blekinge", 2068: "c_siwistan",
    2118: "c_kokpekty", 2119: "c_chuguchak", 2124: "c_yarkand", 2128: "c_tsaparang",
    2130: "c_nyingchi", 2131: "c_qamdo", 2132: "c_markam", 2133: "c_dege", 2134: "c_rebgong",
    2135: "c_garze", 2182: "c_liangzhou", 2184: "c_xining", 2192: "c_karashar", 2196: "c_guria",
    2203: "c_kakheti", 2204: "c_vanand", 2208: "c_terek_pass", 2209: "c_ilam", 2212: "c_zanjan",
    2213: "c_qom", 2215: "c_qazwin", 2218: "c_shiraz", 2220: "c_bam", 2235: "c_sabzevar",
    2309: "c_sinjar", 2312: "c_wasit", 2313: "c_antiocheia", 2314: "c_rahba", 2327: "c_maan",
    2328: "c_khaybar", 2329: "c_yanbu", 2338: "c_samman", 2339: "c_yabrin", 2348: "c_chios",
    2362: "c_gurganj", 2364: "c_quriltay", 2412: "c_tumar", 2416: "c_besinada", 2418: "c_ukek",
    2423: "c_cheboksary", 2424: "c_peremyshl", 2450: "c_ghadames", 2453: "c_sfax",
    2454: "c_kairwan", 2458: "c_hodna", 2460: "c_saoura", 2466: "c_draa", 2467: "c_meknes",
    2468: "c_tadla", 2746: "c_vidin", 2749: "c_tikhvin", 2751: "c_cuenca", 2752: "c_sogn",
    2753: "c_carcassonne", 2755: "c_soria", 2954: "c_djerba", 2955: "c_ingolstadt",
    2957: "c_regensburg", 2959: "c_tarnowska", 2965: "c_vogtland", 2967: "c_hewes",
    2971: "c_minden", 2972: "c_paderborn", 2973: "c_tecklenburg", 2976: "c_orvieto",
    2977: "c_urbino", 2978: "c_arezzo", 2979: "c_novara", 2980: "c_lucca", 2983: "c_salerno",
    2984: "c_cosenza", 2986: "c_cagliari", 2987: "c_urgell", 2988: "c_tarragona", 2990: "c_teruel",
    2994: "c_wolgast", 2996: "c_mecklenburg", 2998: "c_buzau", 2999: "c_hormuz", 3001: "c_skopje",
    3002: "c_rama", 3003: "c_euboea", 4110: "c_sutherland", 4111: "c_saintonge", 4112: "c_quercy",
    4115: "c_korosten", 4116: "c_phrygia", 4118: "c_desmond", 4119: "c_mayo", 4120: "c_dublin",
    4121: "c_ulster", 4122: "c_shenkursk", 4125: "c_hewes", 4126: "c_bacs", 4130: "c_somerset",
    4141: "c_ditmarschen", 4142: "c_aarhus", 4147: "c_yaroslavl", 4148: "c_luki",
    4149: "c_vorbasse", 4150: "c_beja", 4151: "c_inari", 4152: "c_kainuu", 4164: "c_dal",
    4165: "c_skane", 4171: "c_shahre-babak", 4175: "c_arbanon", 4176: "c_branicevo",
    4207: "c_kara_khoja", 4236: "c_trenscen", 4237: "c_olomouc", 4243: "c_toropets",
    4244: "c_starodub", 4245: "c_smolensk", 4248: "c_tver", 4250: "c_yaroslavl", 4252: "c_moskva",
    4254: "c_starodub", 4255: "c_tula", 4259: "c_velsk", 4260: "c_valdai", 4262: "c_totma",
    4268: "c_al_aqabah", 4269: "c_wajh", 4272: "c_al_jawf", 4277: "c_taif", 4279: "c_zabid",
    4286: "c_muscat", 4292: "c_upper_khabur", 4297: "c_homs", 4301: "c_kartli", 4305: "c_shaki",
    4325: "c_sarakhs", 4326: "c_nishapur", 4327: "c_jabal_kufs", 4332: "c_irahistan",
    4334: "c_tun", 4339: "c_rasht", 4343: "c_chaghaniyan", 4362: "c_annandale", 4363: "c_argyll",
    4364: "c_inner_hebrides", 4368: "c_north_riding", 4370: "c_cambridgeshire", 4371: "c_sussex",
    4372: "c_warwickshire", 4373: "c_devon", 4374: "c_dorset", 4375: "c_cheshire",
    4376: "c_leicestershire", 4377: "c_ormond", 4378: "c_desmond", 4380: "c_ailech",
    4381: "c_oversticht", 4382: "c_groningen", 4384: "c_rennes", 4387: "c_angouleme",
    4388: "c_chartres", 4389: "c_tourraine", 4390: "c_troyes", 4481: "c_punakha",
    4515: "c_gyirong", 4516: "c_purang", 4519: "c_damxung", 4520: "c_rutog", 4524: "c_dobrzynska",
    4525: "c_gostyninska", 4526: "c_gnieznienska", 4527: "c_sandomierska", 4528: "c_kujawy",
    4529: "c_iasi", 4531: "c_giurgiu", 4532: "c_severin", 4533: "c_wielunska", 4536: "c_grodno",
    4543: "c_kursk", 4546: "c_malaga", 4548: "c_niebla", 4550: "c_castellon", 4551: "c_avila",
    4552: "c_burgos", 4553: "c_zamora", 4554: "c_astorga", 4555: "c_tui", 4556: "c_aveiro",
    4559: "c_menorca", 4560: "c_iviza", 4564: "c_tamasna", 4566: "c_kairwan", 4567: "c_germa",
    4690: "c_ishim", 4692: "c_turgay", 4693: "c_keriya", 4694: "c_foix", 4695: "c_carcassonne",
    4696: "c_provence", 4697: "c_la_marche", 4698: "c_cephalonia", 4699: "c_nicopolis",
    4700: "c_lesbos", 4701: "c_korinthos", 4708: "c_rothenburg", 4709: "c_passau",
    4710: "c_ravensburg", 4712: "c_sankt_gallen", 4716: "c_coburg", 4717: "c_leuchtenburg",
    4719: "c_geneva", 4720: "c_geneva", 4723: "c_opole", 4727: "c_cuneo", 4728: "c_pavia",
    4730: "c_bologna", 4731: "c_spoleto", 4732: "c_tivoli", 4735: "c_arborea", 4736: "c_palermo",
    4737: "c_agrigento", 4738: "c_aquileia", 4739: "c_brescia", 4740: "c_como",
    4741: "c_mersenburg", 4742: "c_gottingen", 4745: "c_rugen", 4746: "c_landsberg",
    4748: "c_brandenburg", 4749: "c_landsberg", 4750: "c_arbanon", 4751: "c_kranj",
    4752: "c_gacka", 4753: "c_zadar", 4754: "c_pomorje", 4755: "c_podrinje", 4764: "c_dole",
    4765: "c_sundgau", 4766: "c_bar", 4767: "c_saarbrucken", 4769: "c_lille", 4771: "c_bremen",
    4772: "c_luneburg", 4774: "c_fulda", 4776: "c_blois", 4777: "c_forez", 4780: "c_ohrid",
    4788: "c_plasencia", 4789: "c_cuellar",
})

# Scandinavia and Finland: the EU4 province names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    4: "c_dalabergslagen", 5: "c_varmland", 6: "c_skane", 7: "c_skara", 8: "c_dalarna",
    11: "c_angermanland", 15: "c_ringkobing", 16: "c_raniriki", 18: "c_pite", 19: "c_pedersore",
    29: "c_tavasts", 31: "c_olavinlinna", 315: "c_karasjohka", 371: "c_nordrland", 1777: "c_ter",
    1979: "c_faereyar", 1983: "c_lolland_falster", 1984: "c_aalborg", 1985: "c_narke",
    4113: "c_oulu", 4114: "c_julevadno", 4123: "c_messukyla", 4163: "c_vastergotland",
    4166: "c_finnveden",
})

# Baltic, Poland and the Low Countries: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    35: "c_osel", 36: "c_reval", 37: "c_vidzeme", 39: "c_grobin", 41: "c_konigsberg",
    43: "c_danzig", 94: "c_luxembourg", 99: "c_guelders", 100: "c_westfriesland", 256: "c_plocka",
    261: "c_halych", 271: "c_raseiniai", 272: "c_kernave", 273: "c_jersika", 767: "c_allenstein",
    770: "c_braslau", 1834: "c_dorpat", 1841: "c_malbork", 1865: "c_brugge",
    1931: "c_ostfriesland", 1936: "c_trakai", 1939: "c_leczycka", 2958: "c_osterode",
    2960: "c_sacz", 2961: "c_lviv", 2963: "c_krajna", 2966: "c_legnica", 2974: "c_maastricht",
    2997: "c_danzig", 4238: "c_legnica", 4241: "c_talava", 4383: "c_holland", 4523: "c_kujawy",
    4534: "c_siauliai", 4535: "c_kernave", 4541: "c_lviv", 4770: "c_brabant",
})

# France, Iberia and the British Isles: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    88: "c_boulogne", 89: "c_amiens", 167: "c_eu", 169: "c_penthievre", 170: "c_cornouaille",
    171: "c_vannes", 172: "c_nantes", 180: "c_poitiers", 182: "c_vermandois", 184: "c_orleans",
    187: "c_vaucouleurs", 189: "c_nancy", 192: "c_dijon", 193: "c_besancon", 197: "c_rossello",
    203: "c_lyon", 204: "c_viennois", 206: "c_santiago", 207: "c_asturias_de_oviedo",
    208: "c_leon", 226: "c_algeciras", 230: "c_faro", 235: "c_kent", 241: "c_glamorgan",
    242: "c_caernarfonshire", 247: "c_cumberland", 250: "c_strathearn", 372: "c_oriel",
    373: "c_athlone", 375: "c_thomond", 376: "c_connacht", 1745: "c_asturias_de_santillana",
    1877: "c_chalon", 2754: "c_calatrava", 2991: "c_provence", 4361: "c_dunbar",
    4365: "c_isle_of_man", 4366: "c_maldwyn", 4367: "c_east_riding", 4369: "c_carmarthenshire",
    4379: "c_ossory", 4385: "c_avranches", 4386: "c_montaigu", 4391: "c_viviers",
    4392: "c_auxerre", 4547: "c_alcaraz", 4549: "c_valencia", 4557: "c_lleida",
    4558: "c_monterrei", 4785: "c_west_riding", 4787: "c_lisboa",
})

# The German lands, Austria, Bohemia and Switzerland: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    48: "c_cammin", 49: "c_soldin", 58: "c_dessau", 60: "c_cottbus", 63: "c_gleichenstein",
    64: "c_frontenhausen", 73: "c_innsbruck", 75: "c_strassburg", 81: "c_marburg", 85: "c_cologne",
    129: "c_ljubljana", 130: "c_pula", 132: "c_liebnitz", 1757: "c_parsberg",
    1761: "c_kaiserslautern", 1763: "c_cottbus", 1769: "c_gorz", 1770: "c_vienna", 1771: "c_zatec",
    1775: "c_slesvig", 1857: "c_dannenberg", 1858: "c_stettin", 1870: "c_sankt_gallen",
    1871: "c_aosta", 2956: "c_hohenau", 2964: "c_stendal", 2968: "c_doudleby", 2969: "c_soldin",
    2970: "c_hradec", 2975: "c_cleves", 2993: "c_prenzlau", 2995: "c_slupsk",
    4707: "c_falkenstein", 4711: "c_nordlingen", 4713: "c_zollern", 4714: "c_baden",
    4715: "c_hohenlohe", 4718: "c_erbach", 4721: "c_neuchatel", 4722: "c_grisons",
    4724: "c_caslav", 4725: "c_jihlava", 4726: "c_opava", 4743: "c_orlamunde", 4744: "c_osterland",
    4747: "c_pila", 4758: "c_brixen", 4759: "c_villach", 4760: "c_passau", 4761: "c_linz",
    4762: "c_sankt_polten", 4768: "c_cologne", 4773: "c_hildesheim", 4775: "c_osnabruck",
    4778: "c_gorlitz", 4786: "c_havelberg",
})

# Italy, the Balkans and the Carpathians: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    103: "c_canavese", 104: "c_lombardia", 123: "c_reggio_calabria", 131: "c_zagorje",
    138: "c_duklja", 139: "c_zachlumia", 140: "c_vhrbosna", 143: "c_avlonas", 144: "c_epeiros",
    145: "c_laconia", 147: "c_thessalonika", 149: "c_adrianopolis", 152: "c_zagorje",
    158: "c_szekelyfold", 159: "c_dorostorum", 160: "c_craiova", 161: "c_campulung",
    163: "c_chandax", 1247: "c_bastia", 1756: "c_cetatea_alba", 1765: "c_naissus",
    1766: "c_hvosno", 1767: "c_pozega", 1773: "c_achaia", 1831: "c_travunia", 1875: "c_turin",
    1934: "c_rossano", 1952: "c_marmaros", 1954: "c_csanad", 2405: "c_tigheci",
    2750: "c_philippopolis", 2981: "c_monferrato", 2982: "c_siracusa", 2985: "c_foggia",
    2992: "c_tortona", 3000: "c_naissus", 4127: "c_torda", 4128: "c_fogaras", 4173: "c_szerem",
    4174: "c_dyrrachion", 4239: "c_beograd", 4240: "c_feher", 4530: "c_barlad", 4702: "c_serres",
    4703: "c_velbazhd", 4704: "c_turnovo", 4705: "c_mosynopolis", 4706: "c_constanta",
    4729: "c_padua", 4733: "c_benevento", 4734: "c_benevento", 4756: "c_zagorje", 4757: "c_macva",
    4779: "c_kalliopolis",
})

# Anatolia, the Caucasus, the Pontic steppe and Ruthenia: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    269: "c_volkovysk", 279: "c_volodymyr", 280: "c_kiev", 281: "c_terebovl", 282: "c_odessa",
    283: "c_khortytsia", 284: "c_perekop", 286: "c_tana", 288: "c_millerovo", 291: "c_oskol",
    292: "c_orsha", 297: "c_karachev", 316: "c_bithynia", 317: "c_prusa", 318: "c_caria",
    319: "c_caria", 320: "c_rhodos", 321: "c_nicosia", 322: "c_pacatiana", 323: "c_lycaonia",
    324: "c_isauria", 325: "c_pompeiopolis", 326: "c_galatia", 328: "c_sinope", 329: "c_sebasteia",
    331: "c_theodosiopolis", 418: "c_mesopotamia", 422: "c_odishi", 425: "c_derbent",
    463: "c_zichia", 466: "c_astrakhanka", 467: "c_balachev", 1846: "c_euchaita",
    1848: "c_pisidia", 1943: "c_ushytsia", 1944: "c_korsun", 1971: "c_petrovsk", 1974: "c_kherson",
    2195: "c_zichia", 2197: "c_cabardinia", 2198: "c_samiran", 2199: "c_anket", 2201: "c_maghas",
    2202: "c_khachen", 2205: "c_suenik", 2296: "c_abydos", 2297: "c_lydia", 2298: "c_pamphylia",
    2299: "c_honorias", 2300: "c_charsianon", 2301: "c_kaisereia", 2302: "c_seleucia",
    2303: "c_melitene", 2304: "c_helenopontus", 2305: "c_satala", 2306: "c_turuberan",
    2307: "c_vaspurakan", 2308: "c_edessa", 2406: "c_kherson", 2407: "c_pereyaslavl",
    2408: "c_khopyor", 2409: "c_bakhmut", 2410: "c_kalos_limen", 2411: "c_oleshye", 2413: "c_tana",
    2414: "c_tana", 2417: "c_maghas", 2447: "c_kerch", 2962: "c_peresopnytsia", 4242: "c_orsha",
    4246: "c_roslavl", 4247: "c_chornobyl", 4295: "c_mesopotamia", 4296: "c_apahunik",
    4299: "c_shirvan", 4302: "c_bagrewand", 4303: "c_tao", 4306: "c_khumar", 4307: "c_cappadocia",
    4308: "c_chonae", 4309: "c_ionia", 4310: "c_sebasteia", 4311: "c_philomelium",
    4312: "c_galatia_salutaris", 4313: "c_hadrianopolis", 4314: "c_lower_galatia", 4315: "c_zela",
    4340: "c_talish", 4537: "c_novogrudok", 4538: "c_cherven", 4539: "c_zaslavl",
    4540: "c_ushytsia", 4542: "c_romen", 4544: "c_babruysk", 4545: "c_slutsk",
})

# Russia, the Urals and Siberia: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    33: "c_vodi", 34: "c_vyangi", 296: "c_kozelsk", 303: "c_saratov", 306: "c_nizhny_novgorod",
    311: "c_rusa", 313: "c_povenets", 473: "c_karatayak", 475: "c_belebey", 479: "c_petropavolsk",
    1056: "c_kotokel", 1057: "c_ulan_ude", 1058: "c_chikoy", 1059: "c_bratsk", 1060: "c_irkutsk",
    1062: "c_krasnoyarsk", 1063: "c_tagul", 1073: "c_kharam-vosh", 1079: "c_kolyn", 1752: "c_tver",
    1754: "c_novosil", 1776: "c_povenets", 1778: "c_murom", 1957: "c_plyos", 1960: "c_sebezh",
    1962: "c_kargadan", 1963: "c_kumych", 1964: "c_sebur", 1966: "c_kumertau", 1972: "c_glazov",
    2354: "c_tobol", 2357: "c_bardak", 2369: "c_dolgujar", 2415: "c_kozlov", 2419: "c_atkarsk",
    2420: "c_salavat", 2421: "c_cykma", 2422: "c_cykma", 2427: "c_tabary", 2428: "c_konda_ob",
    2429: "c_ob", 2433: "c_vasyugan", 2441: "c_belebey", 2442: "c_lena", 2443: "c_kansk",
    2444: "c_bugurslan", 2446: "c_muya", 4117: "c_tver", 4129: "c_lysva", 4249: "c_tver",
    4251: "c_mozhaysk", 4253: "c_vladimir", 4257: "c_kevrola", 4258: "c_onega_BJA",
    4261: "c_bezichi", 4263: "c_lyubim", 4264: "c_mamadych", 4265: "c_elabuga", 4266: "c_votkinsk",
    4267: "c_bolghar", 4691: "c_laia",
})

# Persia, Khorasan and Central Asia: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    413: "c_luristan", 417: "c_gilan", 427: "c_damghan", 428: "c_rayy", 431: "c_sif-i-umara",
    432: "c_kirman", 434: "c_nih", 437: "c_terekli", 438: "c_kara-mugai", 440: "c_aralkizil",
    443: "c_qyzylustyurt", 444: "c_kalif", 447: "c_rukhaj", 448: "c_ghazna", 449: "c_ghur",
    453: "c_nakhshab", 455: "c_aral_karakum", 456: "c_shavgar", 457: "c_chah", 458: "c_ferghana",
    460: "c_uzgend", 465: "c_itil", 470: "c_uzen", 471: "c_jambalar", 472: "c_jitikul",
    474: "c_yaitsk", 476: "c_astana", 477: "c_torangy_kul", 478: "c_kabtag", 575: "c_panjgur",
    577: "c_sibi", 578: "c_bannu", 710: "c_khotan", 711: "c_charkliq", 712: "c_aksu",
    1967: "c_khojand", 1968: "c_khuttal", 1969: "c_cherik", 1970: "c_sighnaq",
    1973: "c_zamakhshar", 2121: "c_kucha", 2123: "c_charkliq", 2125: "c_uchkul", 2126: "c_suyab",
    2127: "c_karghalik", 2206: "c_urmiya", 2207: "c_maragha", 2210: "c_kermanshah",
    2211: "c_hulwan", 2214: "c_gurgan", 2216: "c_damghan", 2217: "c_behabad", 2221: "c_tus",
    2222: "c_ardestan", 2224: "c_farah", 2225: "c_bamian", 2226: "c_purushapura",
    2227: "c_west-tokharestan", 2228: "c_guzgan", 2229: "c_bost", 2230: "c_zamindawar",
    2231: "c_turan", 2232: "c_kiz", 2233: "c_bampur", 2234: "c_kirman", 2236: "c_juwain",
    2349: "c_churuk", 2350: "c_marvarrud", 2351: "c_shchuchinsk", 2352: "c_otrar",
    2353: "c_ulytau", 2356: "c_sutkend", 2358: "c_ulytau", 2359: "c_astana",
    2360: "c_kara_asirgan", 2361: "c_mushun", 2363: "c_jend", 2365: "c_atyrau", 2366: "c_basagha",
    2367: "c_qyzylyaitsk", 2368: "c_balashagun", 2370: "c_kath", 4209: "c_maralbeshi",
    4210: "c_karghalik", 4289: "c_tustar", 4290: "c_dawraq", 4293: "c_irbil", 4294: "c_hulwan",
    4300: "c_maragha", 4304: "c_urmiya", 4324: "c_badghis", 4329: "c_darabjerd",
    4330: "c_darabjerd", 4331: "c_istakhr", 4335: "c_ardestan", 4336: "c_tus", 4337: "c_rayy",
    4338: "c_zanjan", 4341: "c_mazandaran", 4342: "c_ramhurmuz", 4344: "c_kishsh",
    4345: "c_sirjan", 4685: "c_kaerji",
})

# Arabia, the Maghreb, the Levant and Egypt: EU4 names that differ from CK3's, paired by place.
PROVINCE_COUNTY.update({
    338: "c_algier", 343: "c_fes", 344: "c_marrakesh", 345: "c_asfi", 346: "c_ziz", 348: "c_sous",
    350: "c_bilizma", 352: "c_qashtiliya", 354: "c_tripolitana", 355: "c_syrte", 364: "c_ghazza",
    366: "c_canarias", 378: "c_tripoli", 380: "c_kerak", 381: "c_irbid",
    387: "c_tihamat-al-yamani", 390: "c_sanaa", 393: "c_hail", 395: "c_uqayr", 396: "c_al-hasa",
    398: "c_julfar", 401: "c_dhofar", 404: "c_dhafra", 405: "c_palmyra", 406: "c_iskaf",
    407: "c_raqqa", 1854: "c_jaffa", 1855: "c_beirut", 2310: "c_takrit", 2311: "c_qadisiya",
    2323: "c_kalabsha", 2330: "c_harrat_rahat", 2331: "c_tihama", 2332: "c_aqiq",
    2333: "c_al-hasa", 2335: "c_yamama", 2336: "c_falaj", 2337: "c_qasim", 2340: "c_uqayr",
    2341: "c_duqm", 2342: "c_duqm", 2343: "c_hadramawt", 2344: "c_jawf-al-yamani", 2345: "c_wabar",
    2346: "c_tihama", 2347: "c_al-hasa", 2448: "c_murzuk", 2449: "c_waddan", 2451: "c_tripolitana",
    2452: "c_jafara", 2455: "c_medjerda", 2456: "c_souf", 2457: "c_ghardaia", 2459: "c_ashir",
    2461: "c_tanas", 2462: "c_tanas", 2463: "c_tahert", 2464: "c_tudgha", 2465: "c_wajda",
    2469: "c_asfi", 2470: "c_sous", 2472: "c_wargla", 2473: "c_mahdiya", 2474: "c_ghat",
    4270: "c_sirhan", 4271: "c_hauran", 4273: "c_qasim", 4274: "c_subay", 4275: "c_yamama",
    4278: "c_tihama", 4280: "c_taizz", 4281: "c_al-asa", 4282: "c_tihama", 4283: "c_hadramawt",
    4284: "c_dhofar", 4285: "c_az-dhahira", 4287: "c_falaj", 4288: "c_ubulla", 4291: "c_samarra",
    4298: "c_aintab", 4561: "c_fes", 4562: "c_hunyan", 4563: "c_fes", 4565: "c_canarias",
    4568: "c_tinmallal",
})

# Mongolia, Tibet, Dzungaria, Nubia and the remaining Old World provinces with no CK3 namesake: paired by place.
PROVINCE_COUNTY.update({
    10: "c_jamtfir", 17: "c_vingulmork", 20: "c_trandheim", 21: "c_vastvag", 22: "c_hedmork",
    23: "c_hordalandi", 24: "c_agdeside", 32: "c_kakisalmi", 309: "c_onega", 430: "c_mandestan",
    660: "c_chiang_rung", 661: "c_dali", 663: "c_weiyuan", 675: "c_qianzhou_1", 676: "c_xigaze",
    678: "c_lhagang", 699: "c_lanzhou_1", 705: "c_gyegumdo", 706: "c_madoi", 713: "c_beshbalik",
    715: "c_jimsar", 717: "c_EM_kizilkhentii", 720: "c_gobi_dorngovi", 721: "c_EM_tsetsen",
    722: "c_em_gobidada", 723: "c_em_dadaels", 725: "c_em_akhulun", 1220: "c_abwab",
    1225: "c_kassala", 2114: "c_gobi_ulaan_nuur", 2115: "c_em_karakopi", 2116: "c_ulaanbaatar",
    2120: "c_ghulja", 2122: "c_chamil", 2165: "c_puzhou", 2166: "c_shanchan", 2167: "c_jianchuan",
    2170: "c_sungqu", 2191: "c_heihe", 2219: "c_lar", 2223: "c_lar", 2748: "c_jianchang_1",
    2989: "c_najera", 4033: "c_gumuz", 4124: "c_viipuri", 4143: "c_vingulmork", 4144: "c_telemark",
    4145: "c_nedenes", 4203: "c_em_khartereg", 4204: "c_minzhou", 4205: "c_nagchu",
    4206: "c_barkul", 4208: "c_burgasutai", 4218: "c_em_kherulendada", 4219: "c_gobi_abga",
    4220: "c_naushki", 4221: "c_gobi_ulaan_govi", 4482: "c_chungthang", 4514: "c_sagya",
    4517: "c_zetang", 4518: "c_lhunzhub", 4665: "c_em_dutulun", 4666: "c_EM_yujuelu",
    4667: "c_EM_ononum", 4669: "c_gobi_sonkhot", 4671: "c_gobi_abakhai", 4672: "c_em_hepung",
    4673: "c_gobi_ongi_gol", 4675: "c_em_zhen", 4676: "c_tengger", 4677: "c_gobi_maominggan",
    4678: "c_karabalgasun",
})

# The last Old World provinces: the Tugur coast and the Liaoning shore.
PROVINCE_COUNTY.update({
    704: "c_LIAO_jinzhou", 1047: "c_eman_tugur",
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


def _province_cultures():
    """{CK3 province id: culture at 867} from CK3's history/provinces (the latest dated
    entry up to 867, else the undated one)."""
    if "pc" in _cache:
        return _cache["pc"]
    pc = {}
    hroot = os.path.join(CK3_GAME, "history", "provinces")
    for f in os.listdir(hroot):
        t = open(os.path.join(hroot, f), encoding="utf-8-sig", errors="replace").read()
        for m in re.finditer(r"(?m)^(\d+)\s*=\s*\{(.*?)^\}", t, re.S):
            body, best = m.group(2), None
            c0 = re.search(r"(?m)^\s*culture\s*=\s*(\w+)", body)
            if c0:
                best = c0.group(1)
            for d in re.finditer(r"(?m)^\s*(\d+)\.\d+\.\d+\s*=\s*\{(.*?)^\s*\}", body, re.S):
                if int(d.group(1)) <= 867:
                    cc = re.search(r"culture\s*=\s*(\w+)", d.group(2))
                    if cc:
                        best = cc.group(1)
            if best:
                pc[int(m.group(1))] = best
    _cache["pc"] = pc
    return pc


def county_culture(county):
    """The CK3 culture of a county at 867: its first barony that carries one, else the
    county holder's own culture."""
    cnty, bprov, _rite = _county_data()
    pc = _province_cultures()
    for b in cnty.get(county, []):
        c = pc.get(bprov[b])
        if c:
            return c
    import culturelift
    import state867

    h = state867.holder(county)
    return culturelift.holder_culture(county)[1] if h else None


def expected_culture(pid):
    """(EU4 culture key, CK3 culture) for a table province; the key is None when CK3's
    culture has no EU4 key (the province keeps what it has)."""
    cc = county_culture(PROVINCE_COUNTY[pid])
    return cc, cc


# Provinces CK3 has no county for (the Azores are not in CK3's world): left as they are.
NO_COUNTY = {367: "The Azores"}


def expected(pid):
    """(EU4 religion, CK3 rite, CK3 faith) for a table province, else Nones."""
    from faiths import ck3_rites, known_faiths

    rite = county_rite(PROVINCE_COUNTY[pid])
    faith = ck3_rites().get(rite)
    return (faith if faith in known_faiths() else None), rite, faith


def db_cultures():
    c = sqlite3.connect(DB)
    out = {p: r for p, r in c.execute("select pid, culture from provinces")}
    c.close()
    return out


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
    con = sqlite3.connect(DB)
    owned = {r[0] for r in con.execute("select distinct pid from tag_provinces")}
    con.close()
    unpaired = sorted(p for p in owned if p not in PROVINCE_COUNTY and p not in NO_COUNTY)
    if unpaired:
        err.append(f"{len(unpaired)} owned provinces are paired with no CK3 county (their culture and religion are not "
                   f"CK3's): {unpaired[:15]}")
    have_c = db_cultures()
    for pid, county in sorted(PROVINCE_COUNTY.items()):
        key, cc = expected_culture(pid)
        if key and have_c.get(pid) != key:
            err.append(f"province {pid}: culture '{have_c.get(pid)}' but CK3 county {county} is {cc} -> '{key}'")
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
    k = 0
    for pid in PROVINCE_COUNTY:
        key = expected_culture(pid)[0]
        if key and c.execute("update provinces set culture=? where pid=? and culture is not ?", (key, pid, key)).rowcount:
            k += 1
    c.commit()
    c.close()
    print(f"{n} province religions and {k} province cultures rewritten in tags.db")


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
