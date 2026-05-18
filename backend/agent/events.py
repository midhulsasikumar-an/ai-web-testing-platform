from dataclasses import dataclass, asdict
from typing import Any, Dict
from datetime import datetime


@dataclass
class ExecutionEvent:
    step: str
    status: str
    payload: Dict[str, Any]
    timestamp: str = datetime.utcnow().isoformat()

    def to_dict(self):
        return asdict(self)


def make_event(step: str, status: str, payload: Dict[str, Any]) -> ExecutionEvent:
    return ExecutionEvent(step=step, status=status, payload=payload)
