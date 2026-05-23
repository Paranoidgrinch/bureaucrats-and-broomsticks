"""Shared effect models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from bab.models.types import EffectType, TargetType


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
