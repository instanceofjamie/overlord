# SPDX-License-Identifier: Apache-2.0
from typing import Protocol

from overlord.models import Decision, Observation


class Provider(Protocol):
    def deliberate(self, observation: Observation) -> Decision: ...


class MockProvider:
    """Pure, deterministic no-op; no network, credentials or paid inference."""

    def deliberate(self, observation: Observation) -> Decision:
        return Decision()
