"""Relic models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from bab.models.types import RelicEffectType


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
