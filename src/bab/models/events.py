"""Event models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bab.models.types import EventEffectType, EventType


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
