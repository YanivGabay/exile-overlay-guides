"""Compact passive-tree table from GGG's official export
(https://github.com/grindinggear/skilltree-export, tag = game version).
Usage: python3 tools/build_tree.py <data.json> <version>   ->  poe1/tree/<version>.json
Kinds: k keystone, n notable, a ascendancy notable, s small, m mastery, j jewel socket, x ascendancy small/start."""
import json, sys
src, version = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
nodes = {}
for nid, v in d["nodes"].items():
    if nid == "root" or "name" not in v:
        continue
    if v.get("isMastery"):
        kind = "m"
    elif v.get("ascendancyName"):
        kind = "a" if v.get("isNotable") else "x"
    elif v.get("isKeystone"):
        kind = "k"
    elif v.get("isNotable"):
        kind = "n"
    elif v.get("isJewelSocket"):
        kind = "j"
    else:
        kind = "s"
    entry = [v["name"], kind]
    if kind in "kna":
        entry.append(v.get("stats", [])[:4])
    if v.get("ascendancyName"):
        entry.append(v["ascendancyName"])
    nodes[nid] = entry
out = {"version": version, "source": f"https://github.com/grindinggear/skilltree-export/tree/{version}", "nodes": nodes}
path = f"poe1/tree/{version.replace('.', '_')}.json"
json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(path, len(nodes), "nodes")
