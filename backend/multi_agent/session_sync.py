from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from backend.agent.browser_session import BrowserSession


@dataclass
class BrowserStateSnapshot:
    storage_state_path: Optional[str] = None
    session_storage: Dict[str, Any] = field(default_factory=dict)
    source_agent: str = ""
    captured_at: datetime = field(default_factory=datetime.utcnow)


async def capture_browser_state(session: BrowserSession, artifact_root: str, run_id: str, agent_name: str) -> BrowserStateSnapshot:
    state_dir = Path(artifact_root) / run_id / "shared-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    storage_state_path = state_dir / f"{agent_name}.json"
    await session.context.storage_state(path=str(storage_state_path))
    try:
        session_storage = await session.page.evaluate("() => Object.fromEntries(Object.entries(sessionStorage))")
    except Exception:
        session_storage = {}
    return BrowserStateSnapshot(
        storage_state_path=str(storage_state_path),
        session_storage=session_storage,
        source_agent=agent_name,
    )


async def restore_session_storage(page, session_storage: Dict[str, Any]) -> None:
    if not session_storage:
        return
    script = """
    (items) => {
      for (const [key, value] of Object.entries(items || {})) {
        sessionStorage.setItem(key, String(value));
      }
    }
    """
    try:
        await page.evaluate(script, session_storage)
    except Exception:
        pass
