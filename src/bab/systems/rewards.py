from random import Random

from bab.models import Card, CardClass, CardRarity


DEFAULT_REWARD_RARITIES: tuple[CardRarity, ...] = (
    "common",
    "uncommon",
    "rare",
)

EPIC_REWARD_RARITIES: tuple[CardRarity, ...] = ("epic",)

ACT_SPECIFIC_REWARD_WEIGHT = 4
BASE_REWARD_WEIGHT = 1


def build_card_reward_pool(
    card_database: dict[str, Card],
    *,
    card_class: CardClass = "bureaucrat",
    rarities: tuple[CardRarity, ...] = DEFAULT_REWARD_RARITIES,
) -> list[Card]:
    return [
        card
        for card in card_database.values()
        if card.class_ == card_class
        and card.rarity in rarities
        and "upgraded" not in card.tags
    ]


def card_progression_weight(card: Card, *, act: int | None = None) -> int:
    if act is None or act <= 1:
        return BASE_REWARD_WEIGHT

    if f"act_{act}" in card.tags:
        return ACT_SPECIFIC_REWARD_WEIGHT

    return BASE_REWARD_WEIGHT


def choose_weighted_card_rewards(
    reward_pool: list[Card],
    rng: Random,
    *,
    count: int,
    act: int | None = None,
) -> list[Card]:
    pool = list(reward_pool)
    selected: list[Card] = []

    while pool and len(selected) < count:
        total_weight = sum(
            max(0, card_progression_weight(card, act=act))
            for card in pool
        )

        if total_weight <= 0:
            selected.extend(pool[: count - len(selected)])
            break

        roll = rng.uniform(0, total_weight)
        cumulative = 0.0
        chosen_index = 0

        for index, card in enumerate(pool):
            cumulative += max(0, card_progression_weight(card, act=act))
            if roll <= cumulative:
                chosen_index = index
                break

        selected.append(pool.pop(chosen_index))

    return selected


def choose_card_rewards(
    card_database: dict[str, Card],
    rng: Random,
    *,
    count: int = 3,
    card_class: CardClass = "bureaucrat",
    rarities: tuple[CardRarity, ...] = DEFAULT_REWARD_RARITIES,
    act: int | None = None,
) -> list[Card]:
    if count <= 0:
        raise ValueError("Reward count must be greater than zero.")

    reward_pool = build_card_reward_pool(
        card_database,
        card_class=card_class,
        rarities=rarities,
    )

    if len(reward_pool) < count:
        raise ValueError(
            f"Not enough reward cards available. Needed {count}, "
            f"found {len(reward_pool)}."
        )

    return choose_weighted_card_rewards(
        reward_pool,
        rng,
        count=count,
        act=act,
    )


def choose_epic_card_rewards(
    card_database: dict[str, Card],
    rng: Random,
    *,
    count: int = 3,
    card_class: CardClass = "bureaucrat",
) -> list[Card]:
    return choose_card_rewards(
        card_database,
        rng,
        count=count,
        card_class=card_class,
        rarities=EPIC_REWARD_RARITIES,
        act=None,
    )


def add_card_reward_to_deck(deck: list[Card], card: Card) -> None:
    deck.append(card)
