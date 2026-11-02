"""Import zone tips from a research table (docs/research/pro-tips.md in the app repo)
into poe1/campaign.json -> zoneTips. Keeps tips we wrote ourselves.
Usage: python3 tools/import_tips.py <pro-tips.md>"""
import json, re, sys

STYLE = {"race": "race", "safe": "safe", "new": "new", "all": "all"}
KEYS = ["EL", "HV", "MXC", "MXB", "PV", "PVB", "TYT", "F26"]

rows = [l for l in open(sys.argv[1], encoding="utf-8") if l.startswith("| ")]
data = json.load(open("poe1/campaign.json", encoding="utf-8"))
areas = json.load(open("poe1/data/areas.json", encoding="utf-8"))

tips = {}
for area, old in data.get("zoneTips", {}).items():
    items = old if isinstance(old, list) else [old]
    tips[area] = [dict(t, sources=t.get("sources", []), confidence=t.get("confidence", "low"), style=t.get("style", "all")) for t in items]

added = 0
for r in rows:
    cols = [c.strip() for c in r.strip().strip("|").split("|")]
    if len(cols) < 8 or not re.match(r"^\d+$", cols[0]):
        continue
    act, zone, tip, style, creator, source, patch, conf = cols[:8]
    conf = conf.lower()
    if conf not in ("high", "med", "medium"):
        continue
    ids = [i for i in re.findall(r"\b\d_\d+_[0-9a-z_]+\b", zone) if i in areas]
    if not ids:
        continue
    area = ids[-1]  # "A → B": the tip is about the destination
    styles = sorted({STYLE[s] for s in re.split(r"[/ ,]+", style.lower()) if s in STYLE}) or ["all"]
    srcs = [k for k in KEYS if re.search(rf"\b{k}\b", source)]
    entry = {"text": tip, "style": "all" if "all" in styles else "/".join(styles), "sources": srcs,
             "confidence": "high" if conf == "high" else "med", "verified": False}
    if not any(t["text"] == tip for t in tips.get(area, [])):
        tips.setdefault(area, []).append(entry)
        added += 1

data["zoneTips"] = tips
json.dump(data, open("poe1/campaign.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
open("poe1/campaign.json", "a").write("\n")
print(f"added {added} tips; zones with tips: {len(tips)}")
