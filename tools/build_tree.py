"""Compact passive-tree table from GGG's official export
(https://github.com/grindinggear/skilltree-export, tag = game version).
Usage: python3 tools/build_tree.py <data.json> <version>   ->  poe1/tree/<version>.json
Kinds: k keystone, n notable, a ascendancy notable, s small, m mastery, j jewel socket, x ascendancy small/start,
c class start (not a point).
links: flat pairs [a, b, a, b, ...] of connected non-ascendancy nodes, for the take order (masteries link only to
their notables). starts: class name -> its start node."""
import json, sys
src, version = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))
nodes = {}
for nid, v in d["nodes"].items():
    if nid == "root" or "name" not in v:
        continue
    if "classStartIndex" in v:
        kind = "c"
    elif v.get("isMastery"):
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
regular = {nid for nid, e in nodes.items() if e[1] not in "ax"}
links = set()
for nid in regular:
    for other in d["nodes"][nid].get("out", []) + d["nodes"][nid].get("in", []):
        if other in regular and other != nid:
            links.add((min(int(nid), int(other)), max(int(nid), int(other))))
starts = {d["classes"][v["classStartIndex"]]["name"]: nid for nid, v in d["nodes"].items() if "classStartIndex" in v}
out = {
    "version": version,
    "source": f"https://github.com/grindinggear/skilltree-export/tree/{version}",
    "nodes": nodes,
    "starts": starts,
    "links": [n for pair in sorted(links) for n in pair],
}
path = f"poe1/tree/{version.replace('.', '_')}.json"
json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(path, len(nodes), "nodes")
