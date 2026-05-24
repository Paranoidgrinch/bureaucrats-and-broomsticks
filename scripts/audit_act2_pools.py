from __future__ import annotations

from collections import Counter, defaultdict

from bab.content.catalog import load_content_catalog_from_act_manifest
from bab.systems.rewards import build_card_reward_pool, choose_epic_card_rewards
from bab.systems.shop import eligible_shop_cards, eligible_shop_relics
from random import Random


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


def rarity_counts(cards_or_relics):
    return dict(Counter(item.rarity for item in cards_or_relics))


def tag_count(items, tag: str) -> int:
    return sum(1 for item in items if tag in item.tags)


def main() -> None:
    act1 = load_content_catalog_from_act_manifest("data/acts/act_1_city.json")
    act2 = load_content_catalog_from_act_manifest("data/acts/act_2_archives.json")

    print("# Pool Audit")
    print()

    print("## Epic transition pool by character")
    for character_id in CHARACTER_IDS:
        epic_cards = [
            card
            for card in act1.card_database.values()
            if card.class_ == character_id and card.rarity == "epic"
        ]

        sample = choose_epic_card_rewards(
            act1.card_database,
            Random(100),
            count=3,
            card_class=character_id,
        )

        print(
            f"{character_id}: "
            f"epic_pool={len(epic_cards)}, "
            f"sample={[card.id for card in sample]}"
        )

    print()
    print("## Act-2 reward pool by character")
    for character_id in CHARACTER_IDS:
        reward_pool = build_card_reward_pool(
            act2.card_database,
            card_class=character_id,
        )

        act2_cards = [
            card
            for card in reward_pool
            if "act_2" in card.tags
        ]

        archive_reward_cards = [
            card
            for card in reward_pool
            if "archive_reward" in card.tags
        ]

        print(
            f"{character_id}: "
            f"normal_reward_pool={len(reward_pool)}, "
            f"rarities={rarity_counts(reward_pool)}, "
            f"act2_cards={len(act2_cards)}, "
            f"archive_reward_cards={len(archive_reward_cards)}"
        )
        print(f"  act2_ids={[card.id for card in act2_cards]}")

    print()
    print("## Act-2 shop card pool by character")
    for character_id in CHARACTER_IDS:
        shop_cards = eligible_shop_cards(
            act2.card_database,
            card_class=character_id,
            act=2,
            fight_number=4,
        )

        act2_shop_cards = [
            card
            for card in shop_cards
            if "act_2" in card.tags
        ]

        epic_shop_cards = [
            card
            for card in shop_cards
            if card.rarity == "epic" or "epic" in card.tags
        ]

        print(
            f"{character_id}: "
            f"shop_cards={len(shop_cards)}, "
            f"rarities={rarity_counts(shop_cards)}, "
            f"act2_shop_cards={len(act2_shop_cards)}, "
            f"epic_shop_cards={len(epic_shop_cards)}"
        )
        print(f"  act2_shop_ids={[card.id for card in act2_shop_cards]}")

    print()
    print("## Act-2 relic pool")
    act2_relics = [
        relic
        for relic in act2.relic_database.values()
        if "act_2" in relic.tags
    ]

    archive_relics = [
        relic
        for relic in act2_relics
        if "archive" in relic.tags
    ]

    shop_relics = eligible_shop_relics(
        act2.relic_database,
        owned_relics=[],
        act=2,
        fight_number=4,
    )

    act2_shop_relics = [
        relic
        for relic in shop_relics
        if "act_2" in relic.tags
    ]

    print(
        f"act2_relics={len(act2_relics)}, "
        f"archive_relics={len(archive_relics)}, "
        f"rarities={rarity_counts(act2_relics)}"
    )
    print(f"act2_relic_ids={[relic.id for relic in act2_relics]}")
    print()
    print(
        f"shop_relics={len(shop_relics)}, "
        f"act2_shop_relics={len(act2_shop_relics)}, "
        f"shop_rarities={rarity_counts(shop_relics)}"
    )
    print(f"act2_shop_relic_ids={[relic.id for relic in act2_shop_relics]}")

    print()
    print("## Sanity checks")
    problems: list[str] = []

    for character_id in CHARACTER_IDS:
        epic_count = sum(
            1
            for card in act1.card_database.values()
            if card.class_ == character_id and card.rarity == "epic"
        )
        if epic_count < 6:
            problems.append(f"{character_id}: epic pool below target: {epic_count} < 6")

        act2_reward_count = sum(
            1
            for card in act2.card_database.values()
            if card.class_ == character_id and "act_2" in card.tags
        )
        if act2_reward_count < 4:
            problems.append(
                f"{character_id}: Act-2 reward cards below target: {act2_reward_count} < 4"
            )

    if len(act2_relics) < 16:
        problems.append(f"Act-2 relic pool below target: {len(act2_relics)} < 16")

    if problems:
        print("Needs expansion:")
        for problem in problems:
            print(f"- {problem}")
    else:
        print("All target pool sizes met.")


if __name__ == "__main__":
    main()
