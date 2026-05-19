# Multi-Agent Architecture

## Overview

The multi-agent layer is a thin orchestration tier on top of the existing deterministic autonomous browser runtime. It does not replace the single-agent loop; it coordinates it.

## Core Components

- `backend.multi_agent.orchestrator.MultiAgentOrchestrator`
- `backend.multi_agent.shared_memory.SharedAgentMemory`
- `backend.multi_agent.navigation_graph.NavigationGraphEngine`
- `backend.multi_agent.coverage.WorkflowCoverageEngine`
- `backend.multi_agent.consensus.ConsensusValidationEngine`
- `backend.multi_agent.reporting.build_unified_report`
- Specialized agents in `backend.multi_agent.agents.*`

## Execution Model

1. Authentication agent runs first when session sharing is needed.
2. The shared browser state is captured and reused.
3. Specialized agents execute in parallel where safe.
4. Results are fused into a unified report.
5. Consensus validation produces root-cause candidates.

## Eventing

All agents publish into the shared `ExecutionEventBus`. Events include the agent identity so the frontend can group live activity by agent.
