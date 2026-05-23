"""Encounter models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bab.models.types import EncounterDifficulty


class EncounterDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    act: int = Field(ge=1)
    difficulty: EncounterDifficulty
    enemies: list[str]
    weight: int = Field(default=1, gt=0)
