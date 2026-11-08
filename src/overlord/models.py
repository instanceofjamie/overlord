# SPDX-License-Identifier: Apache-2.0
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter

Identifier = Annotated[str, StringConstraints(min_length=1, max_length=64, pattern=r"^[\w.-]+$")]
Label = Annotated[str, StringConstraints(min_length=1, max_length=128)]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SessionCreate(Model):
    session_id: UUID
    mission_name: Label
    map_name: Label


class MissionStartedPayload(Model):
    player_count: Annotated[int, Field(strict=True, ge=0, le=256)]


class CheckpointAttackedPayload(Model):
    checkpoint_id: Identifier
    attacking_side: Literal["BLUFOR", "OPFOR", "INDEPENDENT", "UNKNOWN"]


class Envelope(Model):
    protocol_version: Literal["1.0"]
    session_id: UUID
    event_id: UUID
    timestamp: AwareDatetime


class MissionStarted(Envelope):
    event_type: Literal["mission_started"]
    payload: MissionStartedPayload


class CheckpointAttacked(Envelope):
    event_type: Literal["checkpoint_attacked"]
    payload: CheckpointAttackedPayload


Observation = Annotated[MissionStarted | CheckpointAttacked, Field(discriminator="event_type")]
observation_adapter: TypeAdapter[Observation] = TypeAdapter(Observation)


class IngestResult(Model):
    event_id: UUID
    status: Literal["recorded", "duplicate"]


class Decision(Model):
    action: Literal["no_action"] = "no_action"
    reason: Literal["observation_only"] = "observation_only"
