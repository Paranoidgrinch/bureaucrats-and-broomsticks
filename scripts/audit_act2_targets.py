from __future__ import annotations

from math import ceil
from collections import Counter

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool
from bab.systems.shop import eligible_shop_cards, eligible_shop_relics


CHARACTER_IDS = [
    "bureaucrat",
    "failed_wizard",
    "guild_assassin_apprentice",
    "hedge_witch",
    "mortuary_apprentice",
    "night_watch_recruit",
    "sewer_diplomat",
    "shroomancer",
    "witch_clerk",
]


def rarity_counts(items):
    return dict(Counter(item.rarity for item in items))


def encounter_count_by_difficulty(catalog, act: int) -> dict[str, int]:
    counts = Counter()
    for encounter in catalog.encounter_database.values():
        if encounter.act == act:
            counts[encounter.difficulty] += 1
    return dict(counts)


def enemy_count_by_tag(catalog, tag: str) -> int:
    return sum(1 for enemy in catalog.enemy_database.values() if tag in enemy.tags)


def main() -> None:
    act1 = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")
    act2 = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    print("# Act 2 Target Audit")
    print()

    print("## Character reward card targets")
    for character_id in CHARACTER_IDS:
        act1_rewards = [
            card
            for card in build_card_reward_pool(act1.card_database, card_class=character_id)
            if card.rarity in {"common", "uncommon", "rare"}
            and "act_2" not in card.tags
        ]

        act2_specific_rewards = [
            card
            for card in act2.card_database.values()
            if card.class_ == character_id
            and "act_2" in card.tags
            and card.rarity in {"common", "uncommon", "rare"}
        ]

        epic_cards = [
            card
            for card in act1.card_database.values()
            if card.class_ == character_id and card.rarity == "epic"
        ]

        print(f"{character_id}:")
        print(f"  act1_reward_cards={len(act1_rewards)} rarities={rarity_counts(act1_rewards)}")
        print(f"  act2_specific_reward_cards={len(act2_specific_rewards)} / target={len(act1_rewards)}")
        print(f"  epic_cards={len(epic_cards)} / target=9")
        print(f"  missing_act2_rewards={max(0, len(act1_rewards) - len(act2_specific_rewards))}")
        print(f"  missing_epics={max(0, 9 - len(epic_cards))}")

    print()
    print("## Shop pool check")
    for character_id in CHARACTER_IDS:
        shop_cards = eligible_shop_cards(
            act2.card_database,
            card_class=character_id,
            act=2,
            fight_number=4,
        )
        act2_shop_cards = [card for card in shop_cards if "act_2" in card.tags]
        epic_shop_cards = [
            card
            for card in shop_cards
            if card.rarity == "epic" or "epic" in card.tags
        ]

        print(
            f"{character_id}: shop_cards={len(shop_cards)}, "
            f"act2_shop_cards={len(act2_shop_cards)}, "
            f"epic_shop_cards={len(epic_shop_cards)}, "
            f"rarities={rarity_counts(shop_cards)}"
        )

    print()
    print("## Relic targets")
    act1_relics = [
        relic
        for relic in act1.relic_database.values()
        if "act_2" not in relic.tags
    ]
    act2_relics = [
        relic
        for relic in act2.relic_database.values()
        if "act_2" in relic.tags
    ]
    act2_shop_relics = [
        relic
        for relic in eligible_shop_relics(
            act2.relic_database,
            owned_relics=[],
            act=2,
            fight_number=4,
        )
        if "act_2" in relic.tags
    ]

    print(f"act1_relics={len(act1_relics)} rarities={rarity_counts(act1_relics)}")
    print(f"act2_relics={len(act2_relics)} / target~{len(act1_relics)} rarities={rarity_counts(act2_relics)}")
    print(f"act2_shop_relics={len(act2_shop_relics)}")

    print()
    print("## Encounter/enemy +30% targets")
    act1_encounters = encounter_count_by_difficulty(act1, 1)
    act2_encounters = encounter_count_by_difficulty(act2, 2)

    for difficulty in ["easy", "normal", "elite", "boss"]:
        act1_count = act1_encounters.get(difficulty, 0)
        act2_count = act2_encounters.get(difficulty, 0)
        target = ceil(act1_count * 1.3)
        print(
            f"{difficulty}: act1_encounters={act1_count}, "
            f"act2_encounters={act2_count}, target={target}, "
            f"missing={max(0, target - act2_count)}"
        )

    print()
    print("Enemy tag counts:")
    for tag in ["normal", "elite", "boss", "mimic"]:
        act1_count = enemy_count_by_tag(act1, tag)
        act2_count = enemy_count_by_tag(act2, tag)
        target = ceil(act1_count * 1.3)
        print(
            f"{tag}: act1_enemies={act1_count}, "
            f"act2_enemies={act2_count}, target={target}, "
            f"missing={max(0, target - act2_count)}"
        )


if __name__ == "__main__":
    main()

