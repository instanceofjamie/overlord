# SPDX-License-Identifier: Apache-2.0
from typing import Annotated, Any, Literal, cast
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
    report_channel: Literal["guard_radio", "none", "legacy_unverified"] = "legacy_unverified"
    reserve_available: Annotated[bool, Field(strict=True)] = True


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


class ProgressPayload(Model):
    milestone: Literal[
        "briefing_complete", "recon_reported", "extracted", "aborted", "operator_killed"
    ]


class OperationProgress(Envelope):
    event_type: Literal["operation_progress"]
    payload: ProgressPayload


Observation = Annotated[
    MissionStarted | CheckpointAttacked | OperationProgress, Field(discriminator="event_type")
]
observation_adapter: TypeAdapter[Observation] = TypeAdapter(cast(Any, Observation))


class IngestResult(Model):
    event_id: UUID
    status: Literal["recorded", "duplicate"]


class Decision(Model):
    action: Literal["no_action"] = "no_action"
    reason: Literal["observation_only"] = "observation_only"


class Approval(Model):
    command_id: UUID


class Control(Model):
    observation_only: Annotated[bool, Field(strict=True)] = False
    automatic: Annotated[bool, Field(strict=True)] = True
    enabled: Annotated[bool, Field(strict=True)] = False
    paused: Annotated[bool, Field(strict=True)] = False


class Command(Model):
    protocol_version: Literal["1.0"] = "1.0"
    session_id: UUID
    command_id: UUID
    idempotency_key: UUID
    triggering_event: UUID
    action: Literal["dispatch_reserve"] = "dispatch_reserve"
    asset: Literal["reserve_alpha"] = "reserve_alpha"
    location: Literal["response_alpha"] = "response_alpha"
    expires_at: AwareDatetime


class Acknowledgement(Model):
    protocol_version: Literal["1.0"]
    session_id: UUID
    command_id: UUID
    idempotency_key: UUID
    status: Literal["executed", "rejected", "expired", "failed"]
    result: Literal[
        "movement_order_assigned",
        "invalid_command",
        "execution_disabled",
        "paused",
        "reserve_ineligible",
        "invalid_location",
        "already_committed",
        "expired",
        "assignment_failed",
        "uncertain",
        "operation_complete",
    ]


class CommandPoll(Model):
    session_id: UUID
    include_report: Annotated[bool, Field(strict=True)] = False
