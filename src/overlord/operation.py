# SPDX-License-Identifier: Apache-2.0
"""Factual replay of operation progress; no timer-driven interventions or inferred arrival."""

from typing import Any

from overlord.models import Observation


def progression(events: list[Observation]) -> dict[str, Any]:
    stage = "briefing"
    recon = False
    engaged = False
    evidence: list[str] = []
    ignored: list[str] = []
    for event in events:
        if event.event_type == "checkpoint_attacked":
            engaged = True
        if event.event_type != "operation_progress":
            continue
        milestone = event.payload.milestone
        accepted = False
        if milestone == "briefing_complete" and stage == "briefing":
            stage = "recon"
            accepted = True
        elif milestone == "recon_reported" and stage == "recon":
            stage = "extraction"
            recon = True
            accepted = True
        elif milestone == "extracted" and stage == "extraction":
            stage = "succeeded"
            accepted = True
        elif (milestone == "operator_killed" and stage not in ("succeeded", "failed")) or (
            milestone == "aborted" and stage in ("recon", "extraction")
        ):
            stage = "failed"
            accepted = True
        (evidence if accepted else ignored).append(str(event.event_id))
    return dict(
        stage=stage,
        reconnaissance_reported=recon,
        engagement_recorded=engaged,
        outcome=stage if stage in ("succeeded", "failed") else "in_progress",
        accepted_progress_events=evidence,
        ignored_progress_events=ignored,
    )


def debrief(events: list[Observation], responses: list[dict[str, Any]]) -> dict[str, Any]:
    return dict(
        **progression(events),
        responses=responses,
        faction_reports=[
            dict(
                event_id=str(e.event_id),
                source="guard_radio",
                fact="checkpoint harm reported",
                location=e.payload.checkpoint_id,
                occurred_at=e.timestamp.isoformat(),
                confidence="reported by surviving guard; not independently verified",
                player_position="not supplied",
            )
            for e in events
            if e.event_type == "checkpoint_attacked" and e.payload.report_channel == "guard_radio"
        ],
        reserve_arrival="not tracked; execution acknowledges movement order assignment only",
        source="director persisted events and acknowledgements; missing events are unknown",
    )
