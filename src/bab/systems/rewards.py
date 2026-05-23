from random import Random

from bab.models import Card, CardClass, CardRarity

DEFAULT_REWARD_RARITIES: tuple[CardRarity, ...] = (
    "common",
    "uncommon",
    "rare",
)


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


def choose_card_rewards(
    card_database: dict[str, Card],
    rng: Random,
    *,
    count: int = 3,
    card_class: CardClass = "bureaucrat",
    rarities: tuple[CardRarity, ...] = DEFAULT_REWARD_RARITIES,
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

    return rng.sample(reward_pool, k=count)


def add_card_reward_to_deck(deck: list[Card], card: Card) -> None:
    deck.append(card)