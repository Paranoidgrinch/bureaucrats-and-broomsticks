"""Enemy models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bab.models.base import Effect
from bab.models.types import EnemyIntentType


class EnemyIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    intent_type: EnemyIntentType

    # Legacy fields. Still supported for existing content.
    damage: int | None = None
    block: int | None = None
    effects: list[Effect] = Field(default_factory=list)

    # Preferred field for new enemy content.
    # Actions are executed in order and may combine block, damage, debuffs, buffs, etc.
    actions: list[Effect] = Field(default_factory=list)

    weight: int | None = None


class EnemyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    max_hp: int = Field(gt=0)
    intent_pattern: Literal["cycle", "weighted_random"] = "cycle"
    intents: list[EnemyIntent]
    tags: list[str] = Field(default_factory=list)
