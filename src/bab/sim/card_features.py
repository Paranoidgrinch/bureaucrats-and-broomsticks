"""Effect-aware card feature extraction for agents.

This module turns structured card effects into compact features:
- role
- raw damage/block/draw/energy/scaling/status values
- efficiency per cost
- coarse quality score

These features are intentionally simple and framework-free. They are used by
tabular Q-learning to make state/action abstraction less dependent on card ids.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bab.content.catalog import load_default_content_catalog
from bab.models import Card


@dataclass(frozen=True)
class CardFeature:
    card_id: str
    role: str
    cost: int = 0
    damage: int = 0
    block: int = 0
    draw: int = 0
    energy: int = 0
    strength: int = 0
    status_applications: int = 0
    cost_reduction: int = 0
    damage_per_cost: float = 0.0
    block_per_cost: float = 0.0
    utility_score: float = 0.0
    quality_score: float = 0.0
    tags: tuple[str, ...] = field(default_factory=tuple)


class CardFeatureIndex:
    def __init__(self, features_by_id: dict[str, CardFeature]) -> None:
        self.features_by_id = features_by_id

    def feature_for(self, card_id: str) -> CardFeature:
        feature = self.features_by_id.get(card_id)
        if feature is not None:
            return feature
        return keyword_card_feature(card_id)

    def role_for(self, card_id: str) -> str:
        return self.feature_for(card_id).role

    def quality_for(self, card_id: str) -> float:
        return self.feature_for(card_id).quality_score


def build_card_feature_index(
    card_database: dict[str, Card],
) -> CardFeatureIndex:
    return CardFeatureIndex(
        {
            card_id: feature_from_card(card)
            for card_id, card in card_database.items()
        }
    )


def load_default_card_feature_index() -> CardFeatureIndex:
    catalog = load_default_content_catalog()
    return build_card_feature_index(catalog.card_database)


def safe_load_default_card_feature_index() -> CardFeatureIndex:
    try:
        return load_default_card_feature_index()
    except Exception:
        return CardFeatureIndex({})


def feature_from_card(card: Card) -> CardFeature:
    damage = 0
    block = 0
    draw = 0
    energy = 0
    strength = 0
    status_applications = 0
    cost_reduction = 0

    for effect in card.effects:
        amount = effect.amount or 0
        effect_type = effect.type

        if effect_type in {
            "deal_damage",
            "conditional_damage",
            "damage_per_status",
        }:
            damage += max(0, amount)

        elif effect_type == "gain_block":
            block += max(0, amount)

        elif effect_type in {"draw_cards", "conditional_draw"}:
            draw += max(0, amount)

        elif effect_type == "gain_resource":
            if effect.resource in {None, "energy"}:
                energy += max(0, amount)

        elif effect_type == "modify_card_cost":
            cost_reduction += max(0, amount)

        elif effect_type == "gain_strength":
            strength += max(0, amount)

        elif effect_type == "apply_status":
            status_applications += 1

    role = infer_role(
        card=card,
        damage=damage,
        block=block,
        draw=draw,
        energy=energy,
        strength=strength,
        status_applications=status_applications,
        cost_reduction=cost_reduction,
    )

    effective_cost = max(1, card.cost)
    damage_per_cost = damage / effective_cost
    block_per_cost = block / effective_cost

    utility_score = (
        draw * 2.0
        + energy * 2.5
        + strength * 2.5
        + status_applications * 1.5
        + cost_reduction * 1.5
    )

    quality_score = (
        damage * 0.35
        + block * 0.30
        + utility_score
        - card.cost * 0.50
    )

    if role == "bad":
        quality_score -= 10.0

    return CardFeature(
        card_id=card.id,
        role=role,
        cost=card.cost,
        damage=damage,
        block=block,
        draw=draw,
        energy=energy,
        strength=strength,
        status_applications=status_applications,
        cost_reduction=cost_reduction,
        damage_per_cost=damage_per_cost,
        block_per_cost=block_per_cost,
        utility_score=utility_score,
        quality_score=quality_score,
        tags=tuple(card.tags),
    )


def infer_role(
    *,
    card: Card,
    damage: int,
    block: int,
    draw: int,
    energy: int,
    strength: int,
    status_applications: int,
    cost_reduction: int,
) -> str:
    tags = {tag.lower() for tag in card.tags}

    if card.type == "curse" or "curse" in tags:
        return "bad"

    if damage > 0 and block > 0:
        return "attack_block"

    if damage > 0 and status_applications > 0:
        return "attack_debuff"

    if damage > 0:
        return "attack"

    if block > 0 and (draw > 0 or energy > 0 or cost_reduction > 0):
        return "block_utility"

    if block > 0:
        return "block"

    if strength > 0:
        return "scaling"

    if status_applications > 0:
        return "debuff"

    if energy > 0 or cost_reduction > 0:
        return "energy"

    if draw > 0:
        return "draw"

    if any(tag in tags for tag in {"power", "scaling", "setup"}):
        return "scaling"

    if any(tag in tags for tag in {"defense", "defence", "block"}):
        return "block"

    if any(tag in tags for tag in {"attack", "damage"}):
        return "attack"

    return keyword_card_feature(card.id).role


def keyword_card_feature(card_id: str) -> CardFeature:
    role = keyword_card_role(card_id)

    damage = 5 if role in {"attack", "attack_block", "attack_debuff"} else 0
    block = 5 if role in {"block", "block_utility", "attack_block"} else 0
    utility = 2.0 if role in {"draw", "energy", "debuff", "scaling"} else 0.0
    quality = damage * 0.35 + block * 0.30 + utility

    if role == "bad":
        quality -= 10.0

    return CardFeature(
        card_id=card_id,
        role=role,
        damage=damage,
        block=block,
        utility_score=utility,
        quality_score=quality,
    )


def keyword_card_role(card_id: str) -> str:
    text = card_id.lower()

    if any(word in text for word in ("curse", "wound", "junk", "clutter")):
        return "bad"
    if any(word in text for word in ("block", "defend", "guard", "shield", "ward", "barrier")):
        return "block"
    if any(word in text for word in ("strike", "attack", "damage", "stab", "blast", "bolt", "stamp", "bonk")):
        return "attack"
    if any(word in text for word in ("draw", "copy", "memo", "report", "archive", "file", "form")):
        return "draw"
    if any(word in text for word in ("energy", "coffee", "tea", "refund", "free")):
        return "energy"
    if any(word in text for word in ("heal", "mend", "restore")):
        return "heal"
    if any(word in text for word in ("weak", "frail", "vulnerable", "poison", "burn")):
        return "debuff"
    if any(word in text for word in ("strength", "focus", "ritual", "power")):
        return "scaling"

    return "other"
