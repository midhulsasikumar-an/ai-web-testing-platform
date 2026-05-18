from __future__ import annotations

from typing import List

from backend.events.bus import ExecutionEventBus
from backend.events.schemas import ExecutionEvent


class TimelineReplayEngine:
    def __init__(self, bus: ExecutionEventBus | None = None) -> None:
        self.bus = bus or ExecutionEventBus()

    async def load(self, run_id: str) -> List[ExecutionEvent]:
        return await self.bus.get_events(run_id)

    async def replay(self, run_id: str) -> List[ExecutionEvent]:
        return await self.bus.get_events(run_id)
