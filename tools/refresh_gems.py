"""Add new gems and their quest/vendor rewards after a game patch.
Inputs: RePoE's gems.json (https://github.com/repoe-fork/repoe-fork.github.io, data/gems.json, MIT)
and the PoE wiki's vendor_rewards table (the source exile-leveling uses), dumped as JSON rows
{quest_id, item_id, classes, npc}.
Usage: python3 tools/refresh_gems.py <repoe gems.json> <wiki vendor rows.json>

Only adds or renames; never removes a gem (old Path of Building codes still name retired gems).
Quest rewards come from RePoE only for gems that are new here: RePoE repeats some class rows,
so existing quest rewards stay as they are."""
import json, sys

GEMS, QUESTS = "poe1/data/gems.json", "poe1/data/quests.json"
ATTRIBUTE = {"r": "strength", "g": "dexterity", "b": "intelligence", "w": "none"}
# Quests with two reward offers (same split as exile-leveling's seeder).
EGGS_SECOND = {"Metadata/Items/Gems/SkillGemSteelskin", "Metadata/Items/Gems/SkillGemFrostblink", "Metadata/Items/Gems/SkillGemDash"}
OFFER = {
    "a1q2": lambda item: "a1q2b" if "Support" in item else "a1q2",
    "a1q4": lambda item: "a1q4b" if item in EGGS_SECOND else "a1q4",
}
SKIP_QUESTS = {"a2q9"}  # the wiki is outdated for The Root of the Problem


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def main(repoe_path, wiki_path):
    repoe, wiki = load(repoe_path), load(wiki_path)
    gems, quests = load(GEMS), load(QUESTS)
    repoe_gems = repoe.values() if isinstance(repoe, dict) else repoe

    added = []
    for g in repoe_gems:
        base = g.get("base_item") or {}
        if base.get("release_state") != "released":
            continue
        level = ((g.get("per_level") or {}).get("1") or {}).get("required_level")
        if level is None:
            continue
        gem_id = base["id"]
        entry = {
            "id": gem_id,
            "name": base["display_name"],
            "primary_attribute": ATTRIBUTE.get(g.get("color"), "none"),
            "required_level": level,
            "is_support": bool(g.get("is_support")),
        }
        old = gems.get(gem_id)
        if old is None:
            added.append(gem_id)
            gems[gem_id] = entry
            reward = g.get("quest_reward")
            if reward:
                add_quest_reward(quests, gem_id, reward)
        elif old != entry:
            print(f"changed {gem_id}: {old} -> {entry}")
            gems[gem_id] = entry
    print(f"added {len(added)} gems:", ", ".join(gems[i]["name"] for i in added) or "none")

    vendor_added = 0
    for row in wiki:
        quest_id, item = row["quest_id"], row["item_id"]
        if quest_id in SKIP_QUESTS or quest_id not in quests or item not in gems:
            continue
        offer_id = OFFER.get(quest_id, lambda _: quest_id)(item)
        offer = quests[quest_id]["reward_offers"].get(offer_id)
        if offer is None or item in offer["vendor"]:
            continue
        classes = sorted(row["classes"].split(",")) if row.get("classes") else []
        offer["vendor"][item] = {"classes": classes, "npc": row["npc"]}
        vendor_added += 1
        print(f"vendor {quest_id} {gems[item]['name']} ({row['npc']}: {', '.join(classes) or 'every class'})")
    print(f"added {vendor_added} vendor rewards")

    save(GEMS, gems)
    save(QUESTS, quests)


def add_quest_reward(quests, gem_id, reward):
    matches = [q for q in quests.values() if q["name"] == reward["quest"] and q["act"] == str(reward["act"]) and q["reward_offers"]]
    if not matches:
        print(f"no quest '{reward['quest']}' for {gem_id}; add it by hand")
        return
    quest = matches[0]
    offer_id = OFFER.get(quest["id"], lambda _: quest["id"])(gem_id)
    offer = quest["reward_offers"][offer_id]
    offer["quest"][gem_id] = {"classes": sorted(set(reward["classes"]))}
    print(f"quest reward {quest['id']} {gem_id.split('/')[-1]} ({', '.join(sorted(set(reward['classes'])))})")


if __name__ == "__main__":
    main(*sys.argv[1:3])
