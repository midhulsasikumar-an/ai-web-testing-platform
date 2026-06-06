from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ExecutionSession:
    execution_id: str
    status: str
    current_step: int = 0
    current_goal: Optional[str] = None
    workflow_state: Optional[str] = None
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled: bool = False


class SessionManager:
    def __init__(self, persistence_root: str = "artifacts"):
        self._sessions: Dict[str, ExecutionSession] = {}
        self._lock = asyncio.Lock()
        self.root = Path(persistence_root)

    async def create(self, execution_id: str, goal: Optional[str] = None, workflow_state: Optional[str] = None) -> ExecutionSession:
        async with self._lock:
            now = datetime.utcnow()
            sess = ExecutionSession(
                execution_id=execution_id,
                status="QUEUED",
                current_step=0,
                current_goal=goal,
                workflow_state=workflow_state,
                started_at=now,
                updated_at=now,
            )
            self._sessions[execution_id] = sess
            self._persist(sess)
            return sess

    async def update(self, execution_id: str, **changes) -> Optional[ExecutionSession]:
        async with self._lock:
            sess = self._sessions.get(execution_id)
            if not sess:
                return None
            for k, v in changes.items():
                if hasattr(sess, k):
                    setattr(sess, k, v)
            sess.updated_at = datetime.utcnow()
            self._persist(sess)
            return sess

    async def get(self, execution_id: str) -> Optional[ExecutionSession]:
        async with self._lock:
            return self._sessions.get(execution_id)

    async def cancel(self, execution_id: str) -> bool:
        async with self._lock:
            sess = self._sessions.get(execution_id)
            if not sess:
                return False
            sess.cancelled = True
            sess.status = "CANCELLED"
            sess.completed_at = datetime.utcnow()
            sess.updated_at = datetime.utcnow()
            self._persist(sess)
            return True

    async def mark_completed(self, execution_id: str, status: str = "COMPLETED") -> None:
        async with self._lock:
            sess = self._sessions.get(execution_id)
            if not sess:
                return
            sess.status = status
            sess.completed_at = datetime.utcnow()
            sess.updated_at = datetime.utcnow()
            self._persist(sess)

    async def is_cancelled(self, execution_id: str) -> bool:
        async with self._lock:
            sess = self._sessions.get(execution_id)
            return bool(sess and sess.cancelled)

    def _persist(self, sess: ExecutionSession) -> None:
        try:
            path = self.root / sess.execution_id
            path.mkdir(parents=True, exist_ok=True)
            with (path / "session.json").open("w", encoding="utf-8") as fh:
                json.dump(self._to_serializable(sess), fh, default=str, indent=2)
        except Exception:
            pass

    @staticmethod
    def _to_serializable(sess: ExecutionSession) -> Dict:
        out = asdict(sess)
        for k, v in out.items():
            if isinstance(v, datetime):
                out[k] = v.isoformat()
        return out


session_manager = SessionManager()
