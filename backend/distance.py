"""Distance-provider boundary for assessment pricing.

No route provider is assumed. Production can supply a provider without changing
pricing or checkout code; the safe default returns a manual-review result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class DistanceResult:
    miles: float | None
    provider: str
    pricing_rule_note: str


class DistanceProvider(Protocol):
    async def route_distance(self, project_address: str) -> DistanceResult: ...


class ManualReviewDistanceProvider:
    async def route_distance(self, project_address: str) -> DistanceResult:
        return DistanceResult(
            miles=None,
            provider="manual_review",
            pricing_rule_note="No geocoding/routing provider is configured; distance was not invented.",
        )


distance_provider: DistanceProvider = ManualReviewDistanceProvider()
