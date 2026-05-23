"""Card and character-class models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bab.models.base import Effect
from bab.models.types import CardClass, CardRarity, CardType


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
