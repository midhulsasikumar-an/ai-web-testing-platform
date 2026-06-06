from __future__ import annotations

"""
Trajectory engine — scores, optimizes, and analyzes agent execution
trajectories through the world graph for RL-ready data generation.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.agent.world_model.world_graph import WorldGraph


class TrajectoryStep(BaseModel):
    step_index: int
    node_id: str
    edge_id: Optional[str] = None
    action_type: str = ""
    action_target: Optional[str] = None
    success: bool = True
    reward: float = 0.0
    cumulative_reward: float = 0.0
    state_value: float = 0.0
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Trajectory(BaseModel):
    trajectory_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:16])
    session_id: str = ""
    objective: str = ""
    steps: List[TrajectoryStep] = Field(default_factory=list)
    total_reward: float = 0.0
    total_duration_ms: int = 0
    success: bool = False
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrajectoryEngine:
    """Scores, records, and analyzes agent trajectories through the world graph."""

    REWARD_WEIGHTS = {
        "new_state_discovered": 1.0,
        "successful_action": 0.5,
        "failed_action": -0.5,
        "revisit_penalty": -0.3,
        "goal_progress": 2.0,
        "stagnation_penalty": -1.0,
        "dead_end_penalty": -0.8,
        "recovery_penalty": -0.2,
        "efficiency_bonus": 0.3,
    }

    def __init__(self) -> None:
        self._trajectories: List[Trajectory] = []
        self._active_trajectory: Optional[Trajectory] = None

    def start_trajectory(self, session_id: str, objective: str) -> Trajectory:
        trajectory = Trajectory(session_id=session_id, objective=objective)
        self._active_trajectory = trajectory
        return trajectory

    def record_step(
        self,
        graph: WorldGraph,
        node_id: str,
        edge_id: Optional[str] = None,
        action_type: str = "",
        action_target: Optional[str] = None,
        success: bool = True,
        duration_ms: int = 0,
        is_new_state: bool = False,
        is_goal_progress: bool = False,
        is_recovery: bool = False,
    ) -> TrajectoryStep:
        if not self._active_trajectory:
            raise RuntimeError("No active trajectory. Call start_trajectory first.")

        node = graph.get_node(node_id)
        reward = self._calculate_reward(
            node=node,
            success=success,
            is_new_state=is_new_state,
            is_goal_progress=is_goal_progress,
            is_recovery=is_recovery,
        )

        cumulative = (
            self._active_trajectory.steps[-1].cumulative_reward if self._active_trajectory.steps else 0.0
        ) + reward

        step = TrajectoryStep(
            step_index=len(self._active_trajectory.steps),
            node_id=node_id,
            edge_id=edge_id,
            action_type=action_type,
            action_target=action_target,
            success=success,
            reward=reward,
            cumulative_reward=cumulative,
            duration_ms=duration_ms,
        )
        self._active_trajectory.steps.append(step)
        self._active_trajectory.total_reward = cumulative
        self._active_trajectory.total_duration_ms += duration_ms
        return step

    def end_trajectory(self, success: bool = False) -> Trajectory:
        if not self._active_trajectory:
            raise RuntimeError("No active trajectory.")
        self._active_trajectory.success = success
        self._active_trajectory.completed_at = datetime.utcnow()
        if success:
            self._active_trajectory.total_reward += self.REWARD_WEIGHTS["efficiency_bonus"] * max(
                10 - len(self._active_trajectory.steps), 0
            )
        self._trajectories.append(self._active_trajectory)
        completed = self._active_trajectory
        self._active_trajectory = None
        return completed

    def _calculate_reward(
        self,
        node: Any,
        success: bool,
        is_new_state: bool,
        is_goal_progress: bool,
        is_recovery: bool,
    ) -> float:
        reward = 0.0
        if is_new_state:
            reward += self.REWARD_WEIGHTS["new_state_discovered"]
        if success:
            reward += self.REWARD_WEIGHTS["successful_action"]
        else:
            reward += self.REWARD_WEIGHTS["failed_action"]
        if is_goal_progress:
            reward += self.REWARD_WEIGHTS["goal_progress"]
        if is_recovery:
            reward += self.REWARD_WEIGHTS["recovery_penalty"]
        if node and node.revisitation_score > 3.0:
            reward += self.REWARD_WEIGHTS["stagnation_penalty"]
        elif node and node.visit_count > 1:
            reward += self.REWARD_WEIGHTS["revisit_penalty"]
        return reward

    def get_best_trajectory(self, objective: Optional[str] = None) -> Optional[Trajectory]:
        candidates = self._trajectories
        if objective:
            candidates = [t for t in candidates if t.objective == objective]
        successful = [t for t in candidates if t.success]
        if not successful:
            return max(candidates, key=lambda t: t.total_reward) if candidates else None
        return min(successful, key=lambda t: len(t.steps))

    def export_for_rl(self) -> List[Dict[str, Any]]:
        """Export all trajectories in RL-ready format."""
        return [
            {
                "trajectory_id": t.trajectory_id,
                "objective": t.objective,
                "success": t.success,
                "total_reward": t.total_reward,
                "steps": [
                    {
                        "state": s.node_id,
                        "action": s.action_type,
                        "target": s.action_target,
                        "reward": s.reward,
                        "next_state": t.steps[s.step_index + 1].node_id
                        if s.step_index + 1 < len(t.steps) else None,
                        "done": s.step_index == len(t.steps) - 1,
                    }
                    for s in t.steps
                ],
            }
            for t in self._trajectories
        ]
