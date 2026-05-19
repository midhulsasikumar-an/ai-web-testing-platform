from __future__ import annotations

"""
Agent orchestrator — multi-agent coordination, task delegation,
workflow supervision, and agent lifecycle management.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("orchestrator")


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentInstance(BaseModel):
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    status: AgentStatus = AgentStatus.IDLE
    goal: str = ""
    url: str = ""
    current_step: int = 0
    max_steps: int = 30
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parent_id: Optional[str] = None  # For sub-agent delegation


class WorkflowStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    agent_id: Optional[str] = None
    goal: str = ""
    url: str = ""
    status: str = "pending"
    depends_on: List[str] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None


class Workflow(BaseModel):
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str
    steps: List[WorkflowStep] = Field(default_factory=list)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExecutionSupervisor:
    """Monitors and supervises agent execution with escalation."""

    def __init__(self, max_failures: int = 5) -> None:
        self._max_failures = max_failures
        self._failure_counts: Dict[str, int] = {}
        self._escalations: List[Dict[str, Any]] = []

    def record_result(self, agent_id: str, success: bool) -> Optional[str]:
        if success:
            self._failure_counts[agent_id] = 0
            return None
        self._failure_counts[agent_id] = self._failure_counts.get(agent_id, 0) + 1
        if self._failure_counts[agent_id] >= self._max_failures:
            escalation = {
                "agent_id": agent_id,
                "failure_count": self._failure_counts[agent_id],
                "action": "terminate",
                "timestamp": datetime.utcnow().isoformat(),
            }
            self._escalations.append(escalation)
            return "terminate"
        if self._failure_counts[agent_id] >= self._max_failures // 2:
            return "reset_workflow"
        return "continue"

    def should_terminate(self, agent_id: str) -> bool:
        return self._failure_counts.get(agent_id, 0) >= self._max_failures


class AgentOrchestrator:
    """
    Multi-agent orchestrator managing agent lifecycle,
    task delegation, and workflow coordination.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, AgentInstance] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._supervisor = ExecutionSupervisor()

    def create_agent(self, name: str, goal: str, url: str,
                     max_steps: int = 30, parent_id: Optional[str] = None) -> AgentInstance:
        agent = AgentInstance(
            name=name, goal=goal, url=url,
            max_steps=max_steps, parent_id=parent_id,
        )
        self._agents[agent.agent_id] = agent
        logger.info("agent_created", extra={"agent_id": agent.agent_id, "goal": goal})
        return agent

    def start_agent(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if not agent or agent.status != AgentStatus.IDLE:
            return False
        agent.status = AgentStatus.RUNNING
        agent.started_at = datetime.utcnow()
        return True

    def complete_agent(self, agent_id: str, result: Dict[str, Any], success: bool = True) -> None:
        agent = self._agents.get(agent_id)
        if agent:
            agent.status = AgentStatus.COMPLETED if success else AgentStatus.FAILED
            agent.completed_at = datetime.utcnow()
            agent.result = result
            self._supervisor.record_result(agent_id, success)

    def cancel_agent(self, agent_id: str) -> None:
        agent = self._agents.get(agent_id)
        if agent and agent.status == AgentStatus.RUNNING:
            agent.status = AgentStatus.CANCELLED
            agent.completed_at = datetime.utcnow()

    def delegate_subtask(self, parent_id: str, sub_goal: str, url: str) -> AgentInstance:
        """Create a sub-agent for task delegation."""
        return self.create_agent(
            name=f"sub_{sub_goal[:20]}", goal=sub_goal,
            url=url, parent_id=parent_id,
        )

    def create_workflow(self, name: str, steps: List[Dict[str, str]]) -> Workflow:
        workflow = Workflow(name=name)
        for step_def in steps:
            workflow.steps.append(WorkflowStep(
                name=step_def.get("name", ""),
                goal=step_def.get("goal", ""),
                url=step_def.get("url", ""),
                depends_on=step_def.get("depends_on", []),
            ))
        self._workflows[workflow.workflow_id] = workflow
        return workflow

    def get_next_workflow_step(self, workflow_id: str) -> Optional[WorkflowStep]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        completed_ids = {s.step_id for s in workflow.steps if s.status == "completed"}
        for step in workflow.steps:
            if step.status == "pending" and all(d in completed_ids for d in step.depends_on):
                return step
        return None

    def get_agent(self, agent_id: str) -> Optional[AgentInstance]:
        return self._agents.get(agent_id)

    def get_active_agents(self) -> List[AgentInstance]:
        return [a for a in self._agents.values() if a.status == AgentStatus.RUNNING]

    def get_stats(self) -> Dict[str, Any]:
        statuses = {}
        for agent in self._agents.values():
            statuses[agent.status.value] = statuses.get(agent.status.value, 0) + 1
        return {
            "total_agents": len(self._agents),
            "statuses": statuses,
            "workflows": len(self._workflows),
            "active": len(self.get_active_agents()),
        }
