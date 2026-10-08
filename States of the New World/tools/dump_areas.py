import json, os
d = json.load(open(f"{os.path.dirname(os.path.abspath(__file__))}/america.json"))
hours = "abcdefghijklmnopqrstuvwxyz"
areas = d["areas"]; provs = d["provs"]
for a in sorted(areas):
    names = []
    for pid in sorted(areas[a]):
        p = provs[str(pid)]
        names.append("%d:%s" % (pid, p["name"].replace(" ", "_")))
    print("%-35s %s" % (a, " ".join(names)))