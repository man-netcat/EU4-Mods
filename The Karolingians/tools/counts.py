import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
d=json.load(open(CACHE / "provdata.json"))
A=d["areas"]
def cnt(name, areas):
    land=0; sea=0
    for a in areas:
        for p in A.get(a,[]):
            pr=d["provs"].get(str(p))
            if pr is None: continue
            if pr["owner"]: land+=1
            else: sea+=1
    return land,sea
groups={
 "east_francia":["alsace_area","upper_rhineland_area","palatinate_area","hesse_area","lower_rhineland_area","north_rhine_area","westphalia_area","north_westphalia_area","weser_area","lower_saxony_area","braunschweig_area"],
 "bavaria":["lower_swabia_area","upper_swabia_area","franconia_area","upper_franconia_area","upper_bavaria_area","lower_bavaria_area","east_bavaria_area","tirol_area","austria_proper_area","inner_austria_area","carinthia_area"],
 "italy_n":["liguria_area","venetia_area","emilia_romagna_area","tuscany_area"],
 "lombardy_n":["piedmont_area","lombardy_area","po_valley_area"],
 "cisjurania":["provence_area","savoy_dauphine_area"],
}
for k,v in groups.items():
    print(f"{k:16} total={sum(len(A.get(a,[])) for a in v):3} {cnt(k,v)}   missing={[a for a in v if a not in A]}")
