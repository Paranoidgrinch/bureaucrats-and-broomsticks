"""Status-effect models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from bab.models.types import StatusStacking, StatusTrigger


class StatusDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    stacking: StatusStacking
    trigger: StatusTrigger = "none"
    is_negative: bool = True
    tags: list[str] = Field(default_factory=list)
