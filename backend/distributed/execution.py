from __future__ import annotations

"""
Distributed execution architecture — browser pool, task queue,
worker management, session orchestration, and heartbeat monitoring.
"""

import asyncio
import logging
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger("distributed")


class TaskPriority(int, Enum):
    CRITICAL = 1
    HIGH = 3
    NORMAL = 5
    LOW = 7
    BACKGROUND = 9


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


@dataclass
class TaskItem:
    task_id: str
    goal: str
    url: str
    priority: int = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.QUEUED
    credentials: Optional[Dict[str, str]] = None
    max_steps: int = 30
    retry_count: int = 0
    max_retries: int = 3
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    worker_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tags: List[str] = field(default_factory=list)


class TaskQueue:
    """Priority-based async task queue with retry support."""

    def __init__(self, max_size: int = 1000) -> None:
        self._tasks: Dict[str, TaskItem] = {}
        self._queue: List[TaskItem] = []
        self._max_size = max_size

    def enqueue(self, goal: str, url: str, priority: int = TaskPriority.NORMAL,
                credentials: Optional[Dict[str, str]] = None, max_steps: int = 30,
                tags: Optional[List[str]] = None) -> TaskItem:
        task = TaskItem(
            task_id=str(uuid.uuid4())[:12], goal=goal, url=url,
            priority=priority, credentials=credentials,
            max_steps=max_steps, tags=tags or [],
        )
        self._tasks[task.task_id] = task
        self._queue.append(task)
        self._queue.sort(key=lambda t: (t.priority, t.created_at))
        return task

    def dequeue(self) -> Optional[TaskItem]:
        for task in self._queue:
            if task.status == TaskStatus.QUEUED:
                task.status = TaskStatus.RUNNING
                task.started_at = time.time()
                return task
        return None

    def complete(self, task_id: str, result: Dict[str, Any]) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = result

    def fail(self, task_id: str, error: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.QUEUED
            task.error = error
            return True
        task.status = TaskStatus.FAILED
        task.error = error
        task.completed_at = time.time()
        return False

    def get_task(self, task_id: str) -> Optional[TaskItem]:
        return self._tasks.get(task_id)

    @property
    def pending_count(self) -> int:
        return sum(1 for t in self._queue if t.status == TaskStatus.QUEUED)

    @property
    def running_count(self) -> int:
        return sum(1 for t in self._queue if t.status == TaskStatus.RUNNING)


@dataclass
class WorkerState:
    worker_id: str
    status: str = "idle"  # idle, busy, crashed, draining
    current_task_id: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    started_at: float = field(default_factory=time.time)


class WorkerManager:
    """Manages distributed browser workers."""

    def __init__(self, max_workers: int = 5, heartbeat_timeout: int = 60) -> None:
        self._workers: Dict[str, WorkerState] = {}
        self._max_workers = max_workers
        self._heartbeat_timeout = heartbeat_timeout

    def register_worker(self, worker_id: Optional[str] = None) -> WorkerState:
        wid = worker_id or str(uuid.uuid4())[:8]
        worker = WorkerState(worker_id=wid)
        self._workers[wid] = worker
        logger.info("worker_registered", extra={"worker_id": wid})
        return worker

    def assign_task(self, worker_id: str, task_id: str) -> bool:
        worker = self._workers.get(worker_id)
        if not worker or worker.status != "idle":
            return False
        worker.status = "busy"
        worker.current_task_id = task_id
        return True

    def complete_task(self, worker_id: str, success: bool = True) -> None:
        worker = self._workers.get(worker_id)
        if worker:
            worker.status = "idle"
            worker.current_task_id = None
            if success:
                worker.tasks_completed += 1
            else:
                worker.tasks_failed += 1

    def heartbeat(self, worker_id: str) -> None:
        worker = self._workers.get(worker_id)
        if worker:
            worker.last_heartbeat = time.time()

    def get_idle_workers(self) -> List[WorkerState]:
        return [w for w in self._workers.values() if w.status == "idle"]

    def detect_crashed(self) -> List[WorkerState]:
        now = time.time()
        crashed = []
        for worker in self._workers.values():
            if worker.status == "busy" and (now - worker.last_heartbeat) > self._heartbeat_timeout:
                worker.status = "crashed"
                crashed.append(worker)
        return crashed

    @property
    def active_count(self) -> int:
        return sum(1 for w in self._workers.values() if w.status in {"idle", "busy"})

    @property
    def can_accept_work(self) -> bool:
        return len(self.get_idle_workers()) > 0


class SessionOrchestrator:
    """Orchestrates task execution across distributed workers."""

    def __init__(self, max_workers: int = 5) -> None:
        self.queue = TaskQueue()
        self.workers = WorkerManager(max_workers=max_workers)
        self._running = False

    async def submit(self, goal: str, url: str, **kwargs) -> TaskItem:
        return self.queue.enqueue(goal=goal, url=url, **kwargs)

    async def dispatch_next(self) -> Optional[tuple[WorkerState, TaskItem]]:
        idle = self.workers.get_idle_workers()
        if not idle:
            return None
        task = self.queue.dequeue()
        if not task:
            return None
        worker = idle[0]
        self.workers.assign_task(worker.worker_id, task.task_id)
        task.worker_id = worker.worker_id
        return worker, task

    async def check_health(self) -> Dict[str, Any]:
        crashed = self.workers.detect_crashed()
        for worker in crashed:
            if worker.current_task_id:
                self.queue.fail(worker.current_task_id, "Worker crashed")
            logger.warning("worker_crashed", extra={"worker_id": worker.worker_id})
        return {
            "active_workers": self.workers.active_count,
            "pending_tasks": self.queue.pending_count,
            "running_tasks": self.queue.running_count,
            "crashed_workers": len(crashed),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "workers": {
                wid: {"status": w.status, "completed": w.tasks_completed, "failed": w.tasks_failed}
                for wid, w in self.workers._workers.items()
            },
            "queue": {
                "pending": self.queue.pending_count,
                "running": self.queue.running_count,
            },
        }
