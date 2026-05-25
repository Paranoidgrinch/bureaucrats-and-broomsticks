"""Shop offer and pricing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import TypeVar

from bab.models import Card, RelicDefinition
from bab.systems.progression_weights import content_progression_weight


@dataclass(frozen=True)
class ShopCardOffer:
    card: Card
    price: int


@dataclass(frozen=True)
class ShopRelicOffer:
    relic: RelicDefinition
    price: int


CARD_BASE_PRICES: dict[str, int] = {
    "common": 55,
    "uncommon": 85,
    "rare": 130,
    "boss": 999,
}

RELIC_BASE_PRICES: dict[str, int] = {
    "common": 130,
    "uncommon": 190,
    "rare": 260,
    "boss": 400,
}

DEFAULT_SHOP_CARD_OFFER_COUNT = 5
DEFAULT_SHOP_RELIC_OFFER_COUNT = 3

CARD_RARITY_WEIGHTS_BY_TIER: tuple[dict[str, int], ...] = (
    {"common": 85, "uncommon": 15, "rare": 0},
    {"common": 55, "uncommon": 35, "rare": 10},
    {"common": 30, "uncommon": 45, "rare": 25},
    {"common": 20, "uncommon": 40, "rare": 40},
)

RELIC_RARITY_WEIGHTS_BY_TIER: tuple[dict[str, int], ...] = (
    {"common": 90, "uncommon": 10, "rare": 0},
    {"common": 60, "uncommon": 30, "rare": 10},
    {"common": 35, "uncommon": 45, "rare": 20},
    {"common": 25, "uncommon": 40, "rare": 35},
)

T = TypeVar("T")


def shop_tier(
    *,
    act: int,
    fight_number: int,
) -> int:
    """Return a coarse shop tier based on campaign progress."""

    progress_score = max(0, act - 1) * 4 + max(0, fight_number - 1) // 3

    if progress_score <= 1:
        return 0

    if progress_score <= 5:
        return 1

    if progress_score <= 10:
        return 2

    return 3


def shop_progression_price_bonus(
    *,
    act: int,
    fight_number: int,
) -> int:
    return max(0, act - 1) * 25 + max(0, fight_number - 1) * 3


def discounted_shop_price(
    price: int,
    discount_percent: int,
) -> int:
    clamped_discount = max(0, min(discount_percent, 75))
    discounted_price = round(price * (100 - clamped_discount) / 100)
    return max(0, round_price(discounted_price))


def round_price(price: int) -> int:
    return ((price + 4) // 5) * 5


def card_shop_price(
    card: Card,
    *,
    act: int,
    fight_number: int,
) -> int:
    base_price = CARD_BASE_PRICES.get(card.rarity, 85)
    price = base_price + shop_progression_price_bonus(
        act=act,
        fight_number=fight_number,
    )

    return round_price(price)


def relic_shop_price(
    relic: RelicDefinition,
    *,
    act: int,
    fight_number: int,
) -> int:
    base_price = RELIC_BASE_PRICES.get(relic.rarity, 180)
    price = base_price + shop_progression_price_bonus(
        act=act,
        fight_number=fight_number,
    )

    return round_price(price)


def card_removal_price(
    *,
    act: int,
    fight_number: int,
    removals_purchased: int = 0,
) -> int:
    price = 75 + shop_progression_price_bonus(
        act=act,
        fight_number=fight_number,
    ) + removals_purchased * 50

    return round_price(price)


def eligible_shop_cards(
    card_database: dict[str, Card],
    *,
    card_class: str,
    act: int,
    fight_number: int,
) -> list[Card]:
    tier = shop_tier(act=act, fight_number=fight_number)
    allowed_rarities = set(CARD_RARITY_WEIGHTS_BY_TIER[tier])

    all_eligible_cards = [
        card
        for card in card_database.values()
        if card.class_ == card_class
        and card.rarity not in {"starter", "boss", "epic"}
        and "upgraded" not in card.tags
    ]

    tier_eligible_cards = [
        card
        for card in all_eligible_cards
        if card.rarity in allowed_rarities
        and CARD_RARITY_WEIGHTS_BY_TIER[tier].get(card.rarity, 0) > 0
    ]

    return sorted(
        tier_eligible_cards or all_eligible_cards,
        key=lambda card: card.id,
    )


def eligible_shop_relics(
    relic_database: dict[str, RelicDefinition],
    owned_relics: list[RelicDefinition],
    *,
    act: int,
    fight_number: int,
    card_class: str | None = None,
) -> list[RelicDefinition]:
    tier = shop_tier(act=act, fight_number=fight_number)
    allowed_rarities = set(RELIC_RARITY_WEIGHTS_BY_TIER[tier])
    owned_relic_ids = {relic.id for relic in owned_relics}

    all_eligible_relics = [
        relic
        for relic in relic_database.values()
        if relic.id not in owned_relic_ids
        and relic.rarity != "boss"
        and (
            not relic.allowed_classes
            or card_class is None
            or card_class in relic.allowed_classes
        )
        and (
            not relic.allowed_classes
            or card_class is None
            or card_class in relic.allowed_classes
        )
    ]

    tier_eligible_relics = [
        relic
        for relic in all_eligible_relics
        if relic.rarity in allowed_rarities
        and RELIC_RARITY_WEIGHTS_BY_TIER[tier].get(relic.rarity, 0) > 0
    ]

    return sorted(
        tier_eligible_relics or all_eligible_relics,
        key=lambda relic: relic.id,
    )


def shop_progression_weight(item, *, act: int) -> int:
    return content_progression_weight(getattr(item, "tags", []), act=act)


def choose_shop_card_offers(
    card_database: dict[str, Card],
    rng: Random,
    *,
    card_class: str,
    act: int,
    fight_number: int,
    count: int = DEFAULT_SHOP_CARD_OFFER_COUNT,
) -> list[ShopCardOffer]:
    tier = shop_tier(act=act, fight_number=fight_number)
    cards = eligible_shop_cards(
        card_database,
        card_class=card_class,
        act=act,
        fight_number=fight_number,
    )
    selected_cards = choose_weighted_unique(
        cards,
        rng,
        count=count,
        weights=CARD_RARITY_WEIGHTS_BY_TIER[tier],
        rarity_getter=lambda card: card.rarity,
        item_weight_getter=lambda card: shop_progression_weight(card, act=act),
    )

    return [
        ShopCardOffer(
            card=card,
            price=card_shop_price(
                card,
                act=act,
                fight_number=fight_number,
            ),
        )
        for card in selected_cards
    ]


def choose_shop_relic_offers(
    relic_database: dict[str, RelicDefinition],
    owned_relics: list[RelicDefinition],
    rng: Random,
    *,
    act: int,
    fight_number: int,
    card_class: str | None = None,
    count: int = DEFAULT_SHOP_RELIC_OFFER_COUNT,
) -> list[ShopRelicOffer]:
    tier = shop_tier(act=act, fight_number=fight_number)
    relics = eligible_shop_relics(
        relic_database,
        owned_relics,
        act=act,
        fight_number=fight_number,
        card_class=card_class,
    )
    selected_relics = choose_weighted_unique(
        relics,
        rng,
        count=count,
        weights=RELIC_RARITY_WEIGHTS_BY_TIER[tier],
        rarity_getter=lambda relic: relic.rarity,
        item_weight_getter=lambda relic: shop_progression_weight(relic, act=act),
    )

    return [
        ShopRelicOffer(
            relic=relic,
            price=relic_shop_price(
                relic,
                act=act,
                fight_number=fight_number,
            ),
        )
        for relic in selected_relics
    ]


def choose_weighted_unique(
    items: list[T],
    rng: Random,
    *,
    count: int,
    weights: dict[str, int],
    rarity_getter,
    item_weight_getter=None,
) -> list[T]:
    pool = list(items)
    selected: list[T] = []

    while pool and len(selected) < count:
        total_weight = sum(
            max(0, weights.get(rarity_getter(item), 1))
            * max(0, item_weight_getter(item) if item_weight_getter else 1)
            for item in pool
        )

        if total_weight <= 0:
            selected.extend(pool[: count - len(selected)])
            break

        roll = rng.uniform(0, total_weight)
        cumulative = 0.0
        chosen_index = 0

        for index, item in enumerate(pool):
            cumulative += (
                max(0, weights.get(rarity_getter(item), 1))
                * max(0, item_weight_getter(item) if item_weight_getter else 1)
            )
            if roll <= cumulative:
                chosen_index = index
                break

        selected.append(pool.pop(chosen_index))

    return selected
