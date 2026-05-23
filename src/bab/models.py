from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal[
        "target_has_status",
        "card_has_tag",
        "card_type_is",
    ]
    status: str | None = None
    tag: str | None = None
    card_type: str | None = None


class Effect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EffectType
    target: TargetType | None = None
    amount: int | None = None
    amount_per_stack: int | None = None
    status: str | None = None
    resource: str | None = None
    condition: Condition | None = None


class Card(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    id: str
    name: str
    class_: CardClass = Field(alias="class")
    type: CardType
    cost: int = Field(ge=0)
    rarity: CardRarity
    text: str
    effects: list[Effect]
    tags: list[str]
    upgrades_to: str | None = None


class CharacterClass(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: CardClass
    name: str
    max_hp: int = Field(gt=0)
    starting_energy: int = Field(gt=0)
    starting_relic: str | None = None
    starting_deck: list[str]
    starting_resources: dict[str, int] = Field(default_factory=dict)


class EnemyIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    intent_type: EnemyIntentType
    damage: int | None = None
    block: int | None = None
    effects: list[Effect] = Field(default_factory=list)
    weight: int | None = None


class EnemyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    max_hp: int = Field(gt=0)
    intent_pattern: Literal["cycle", "weighted_random"] = "cycle"
    intents: list[EnemyIntent]
    tags: list[str] = Field(default_factory=list)


class StatusDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    stacking: StatusStacking
    trigger: StatusTrigger = "none"
    is_negative: bool = True
    tags: list[str] = Field(default_factory=list)


class EncounterDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    act: int = Field(ge=1)
    difficulty: EncounterDifficulty
    enemies: list[str]
    weight: int = Field(default=1, gt=0)


class EventEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EventEffectType
    amount: int | None = None
    card_id: str | None = None
    tag: str | None = None


class EventChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    result_text: str
    effects: list[EventEffect] = Field(default_factory=list)


class EventDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    act: int = Field(ge=1)
    event_type: EventType
    weight: int = Field(default=1, gt=0)
    text: str
    choices: list[EventChoice] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)



class RelicEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: RelicEffectType
    amount: int | None = None
    status: str | None = None


class RelicDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    rarity: Literal["common", "uncommon", "rare", "boss"] = "common"
    effects: list[RelicEffect]
    tags: list[str] = Field(default_factory=list)