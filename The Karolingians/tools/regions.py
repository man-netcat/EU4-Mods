import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"
d = json.load(open(CACHE / "provdata.json"))
provs, roa = d["provs"], d["region_of_area"]
REGS=["france_region","north_german_region","south_german_region","italy_region"]
for r in REGS:
    print(f"\n##### {r}")
    for a in sorted([a for a,v in roa.items() if v==r]):
        ids = d["areas"][a]
        own={}
        for p in ids:
            o=provs.get(str(p),{}).get("owner")
            if o: own.setdefault(o,[]).append(p)
        tot=sum(len(v) for v in own.values())
        print(f"  {a:26} n={len(ids):3} land={tot:3} " + " ".join(f"{k}:{len(v)}" for k,v in sorted(own.items(), key=lambda x:-len(x[1]))))
