"""Shared literal model types."""

from __future__ import annotations

from typing import Literal

CardClass = Literal["bureaucrat"]

CardType = Literal[
    "action",
    "form",
    "argument",
    "spell",
    "footnote",
    "power",
    "curse",
]

CardRarity = Literal[
    "starter",
    "common",
    "uncommon",
    "rare",
    "boss",
]

EffectType = Literal[
    "deal_damage",
    "gain_block",
    "draw_cards",
    "discard_cards",
    "apply_status",
    "remove_status",
    "gain_resource",
    "conditional_damage",
    "conditional_draw",
    "damage_per_status",
    "modify_card_cost",
    "skip_action",
    "gain_strength",
]

TargetType = Literal[
    "self",
    "enemy",
    "all_enemies",
    "random_enemy",
    "owner",
    "player",
    "first_enemy",
]

EnemyIntentType = Literal[
    "attack",
    "block",
    "buff",
    "debuff",
    "special",
]

StatusStacking = Literal[
    "intensity",
    "duration",
]

StatusTrigger = Literal[
    "none",
    "player_turn_start",
    "enemy_turn_start",
    "enemy_turn_end",
    "before_owner_attack",
]

EncounterDifficulty = Literal[
    "easy",
    "normal",
    "elite",
    "boss",
]

EventType = Literal[
    "narrative",
    "risk_reward",
    "deck",
]

EventEffectType = Literal[
    "none",
    "gain_card_reward",
    "upgrade_card",
    "remove_card",
    "lose_percent_max_hp",
    "gain_max_hp",
]

RelicEffectType = Literal[
    "gain_block_at_combat_start",
    "apply_status_to_all_enemies_at_combat_start",
    "increase_max_energy",
    "heal_on_pickup",
    "increase_card_reward_count",
]
