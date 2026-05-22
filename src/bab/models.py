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