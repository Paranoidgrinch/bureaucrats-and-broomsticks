"""Act manifest models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ActMapConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    steps_before_boss: int = Field(gt=0)
    width: int = Field(gt=0)
    first_elite_depth: int = Field(default=6, ge=1)
    elite_weight_multiplier: float = Field(default=1.0, gt=0)


class ActTreasureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mimic_chance: float = Field(ge=0.0, le=1.0)
    mimic_encounter_id: str


class ActWaitingRoomConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    heal_percent: int = Field(ge=0)


class ActRewardConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_choices: int = Field(default=3, gt=0)
    card_reward_chance: float = Field(default=1.0, ge=0.0, le=1.0)


class ActManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    act: int = Field(ge=1)
    name: str
    character_class_files: list[str] = Field(min_length=1)
    default_character_class_id: str
    card_files: list[str] = Field(min_length=1)
    enemy_files: list[str] = Field(min_length=1)
    encounter_files: list[str] = Field(min_length=1)
    status_files: list[str] = Field(min_length=1)
    event_files: list[str] = Field(min_length=1)
    relic_files: list[str] = Field(min_length=1)
    map: ActMapConfig
    treasure: ActTreasureConfig
    waiting_room: ActWaitingRoomConfig
    rewards: ActRewardConfig = Field(default_factory=ActRewardConfig)
