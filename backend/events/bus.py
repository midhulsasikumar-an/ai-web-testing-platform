from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import AsyncIterator, DefaultDict, Dict, List, Optional

from backend.events.schemas import ExecutionEvent


class ExecutionEventBus:
    """Async-safe event bus with replay persistence for live execution streaming."""

    def __init__(self, persistence_root: str = "artifacts/timeline") -> None:
        self._lock = asyncio.Lock()
        self._subscribers: DefaultDict[str, List[asyncio.Queue[ExecutionEvent]]] = defaultdict(list)
        self._events: DefaultDict[str, List[ExecutionEvent]] = defaultdict(list)
        self.persistence_root = Path(persistence_root)

    async def publish(self, event: ExecutionEvent) -> None:
        async with self._lock:
            self._events[event.run_id].append(event)
            queues = list(self._subscribers.get(event.run_id, []))
        await self._persist_event(event)
        for queue in queues:
            await queue.put(event)

    async def subscribe(self, run_id: str) -> asyncio.Queue[ExecutionEvent]:
        queue: asyncio.Queue[ExecutionEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers[run_id].append(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[ExecutionEvent]) -> None:
        async with self._lock:
            subscribers = self._subscribers.get(run_id, [])
            if queue in subscribers:
                subscribers.remove(queue)
            if not subscribers and run_id in self._subscribers:
                self._subscribers.pop(run_id, None)

    async def replay(self, run_id: str) -> AsyncIterator[ExecutionEvent]:
        for event in await self.get_events(run_id):
            yield event

    async def get_events(self, run_id: str) -> List[ExecutionEvent]:
        async with self._lock:
            cached = list(self._events.get(run_id, []))
        if cached:
            return cached
        path = self._timeline_path(run_id)
        if not path.exists():
            return []
        events: List[ExecutionEvent] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            events.append(ExecutionEvent.model_validate_json(line))
        async with self._lock:
            self._events[run_id] = list(events)
        return events

    async def _persist_event(self, event: ExecutionEvent) -> None:
        path = self._timeline_path(event.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json() + "\n")

    def _timeline_path(self, run_id: str) -> Path:
        return self.persistence_root / run_id / "events.jsonl"
