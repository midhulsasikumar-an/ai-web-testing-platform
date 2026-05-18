"""
Enterprise configuration layer with environment-based config,
feature flags, and tuning parameters for all agent subsystems.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class BrowserConfig(BaseModel):
    """Browser automation configuration."""
    headless: bool = True
    viewport_width: int = 1365
    viewport_height: int = 900
    default_timeout_ms: int = 10000
    navigation_timeout_ms: int = 15000
    network_idle_timeout_ms: int = 3000
    max_browser_contexts: int = 10
    ignore_https_errors: bool = True
    user_agent: Optional[str] = None
    proxy: Optional[str] = None
    session_ttl_seconds: int = 3600
    crash_recovery_enabled: bool = True
    zombie_cleanup_interval_seconds: int = 300
    video_recording: bool = False
    trace_recording: bool = False
    artifacts_root: str = "screenshots"


class PlannerConfig(BaseModel):
    """Planner and reasoning configuration."""
    max_candidate_actions: int = 5
    min_confidence_threshold: float = 0.45
    low_confidence_replan: float = 0.65
    max_reasoning_depth: int = 10
    enable_skill_system: bool = True
    enable_llm_planning: bool = True
    llm_model: str = "llama-3.3-70b-versatile"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096
    deterministic_fallback: bool = True
    parallel_skill_evaluation: bool = True
    trajectory_scoring_enabled: bool = True


class RecoveryConfig(BaseModel):
    """Recovery engine configuration."""
    max_recovery_attempts: int = 3
    recovery_timeout_ms: int = 10000
    enable_workflow_restart: bool = True
    enable_skill_switching: bool = True
    escalation_threshold: int = 3
    modal_dismiss_labels: List[str] = Field(
        default_factory=lambda: [
            "Close", "Cancel", "No thanks", "Accept",
            "Got it", "Dismiss", "OK", "I understand",
        ]
    )


class MemoryConfig(BaseModel):
    """Memory system configuration."""
    max_episodic_records: int = 10000
    max_semantic_patterns: int = 5000
    max_procedural_chains: int = 1000
    embedding_dimension: int = 384
    similarity_threshold: float = 0.75
    memory_compression_enabled: bool = True
    compression_threshold: int = 100
    cross_session_learning: bool = True
    vector_store_backend: str = "in_memory"  # in_memory, redis, chromadb
    memory_persistence_path: str = "data/memory"


class SafetyConfig(BaseModel):
    """Safety and risk engine configuration."""
    same_origin_only: bool = True
    allow_private_hosts: bool = False
    max_risk_score_auto_execute: float = 0.3
    require_confirmation_threshold: float = 0.7
    block_threshold: float = 0.9
    dangerous_terms: List[str] = Field(
        default_factory=lambda: [
            "delete", "remove", "drop", "terminate", "shutdown",
            "purchase", "buy", "pay", "checkout", "wire", "transfer",
            "change password", "reset password", "logout all",
            "revoke", "disable", "deactivate",
        ]
    )
    allowed_domains: List[str] = Field(default_factory=list)
    blocked_domains: List[str] = Field(default_factory=list)


class DistributedConfig(BaseModel):
    """Distributed execution configuration."""
    redis_url: str = "redis://localhost:6379"
    max_concurrent_workers: int = 5
    task_queue_name: str = "agent_tasks"
    result_queue_name: str = "agent_results"
    heartbeat_interval_seconds: int = 30
    worker_timeout_seconds: int = 600
    task_retry_limit: int = 3
    task_priority_levels: int = 10
    enable_horizontal_scaling: bool = False


class ContextConfig(BaseModel):
    """Context window and token budget configuration."""
    max_token_budget: int = 8192
    observation_token_limit: int = 3000
    memory_token_limit: int = 2000
    reasoning_token_limit: int = 2000
    reserve_tokens: int = 1192
    dom_compression_max_elements: int = 80
    text_excerpt_max_chars: int = 4000
    history_summary_max_steps: int = 10


class VisionConfig(BaseModel):
    """Vision engine configuration."""
    enable_screenshot_analysis: bool = True
    enable_ocr: bool = True
    enable_visual_grounding: bool = True
    screenshot_max_width: int = 1365
    screenshot_max_height: int = 900
    visual_diff_threshold: float = 0.05
    ocr_confidence_threshold: float = 0.6
    ui_detection_model: str = "heuristic"  # heuristic, ml_model


class ObservabilityConfig(BaseModel):
    """Logging and observability configuration."""
    log_level: str = "INFO"
    structured_logging: bool = True
    log_format: str = "json"
    enable_metrics: bool = True
    enable_distributed_tracing: bool = True
    metrics_export_interval_seconds: int = 60
    trace_sample_rate: float = 1.0
    log_planner_decisions: bool = True
    log_reasoning_chains: bool = True
    log_execution_latency: bool = True


class FeatureFlags(BaseModel):
    """Feature flags for gradual rollout of new capabilities."""
    enable_world_model: bool = True
    enable_skill_engine: bool = True
    enable_objective_decomposition: bool = True
    enable_vision_engine: bool = True
    enable_advanced_memory: bool = True
    enable_risk_engine: bool = True
    enable_distributed_execution: bool = False
    enable_reasoning_traces: bool = True
    enable_loop_prevention: bool = True
    enable_benchmarks: bool = True
    enable_rl_data_pipeline: bool = True
    enable_multi_agent: bool = False


class AgentConfig(BaseSettings):
    """
    Root configuration for the entire agent platform.

    Loads from environment variables with AGENT_ prefix.
    """
    # Sub-configurations
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    planner: PlannerConfig = Field(default_factory=PlannerConfig)
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    distributed: DistributedConfig = Field(default_factory=DistributedConfig)
    context: ContextConfig = Field(default_factory=ContextConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)

    # Global settings
    environment: str = Field(default="development")
    debug: bool = Field(default=False)
    # Authentication/account creation safety toggle
    allow_account_creation: bool = Field(default=True)
    api_key: str = Field(default="")
    data_dir: str = Field(default="data")

    model_config = {
        "env_prefix": "AGENT_",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
    }


# Singleton configuration instance
_config: Optional[AgentConfig] = None


def get_config() -> AgentConfig:
    """Get or create the singleton configuration."""
    global _config
    if _config is None:
        _config = AgentConfig()
    return _config


def reset_config() -> None:
    """Reset the singleton configuration (useful for testing)."""
    global _config
    _config = None
