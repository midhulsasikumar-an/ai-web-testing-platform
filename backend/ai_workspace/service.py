from __future__ import annotations

import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from backend.ai_workspace.intelligence import delete_memory_by_query, generate_instruction_template, resolve_memory_action, save_memory
from backend.ai_workspace.memory import memory_engine
from backend.ai_workspace.models import ActiveContext
from backend.ai_workspace.retrieval import retrieval_system

try:
    from openai import AsyncOpenAI
except Exception:  # pragma: no cover
    AsyncOpenAI = None

try:
    from groq import Groq
except Exception:  # pragma: no cover
    Groq = None


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _truncate_json(value: Any, limit: int = 2200) -> str:
    text = json.dumps(value, default=str, ensure_ascii=False)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _looks_placeholder_like(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in [
            "[insert",
            "insert date",
            "insert number",
            "placeholder",
            "sample",
            "example",
            "todo",
            "lorem ipsum",
        ]
    )


def _top_terms(items: List[Dict[str, Any]], keys: List[str], limit: int = 5) -> List[str]:
    counter: Counter[str] = Counter()
    for item in items:
        for key in keys:
            value = str(item.get(key) or "").lower()
            for token in value.replace("/", " ").replace("_", " ").replace("-", " ").split():
                if len(token) > 3:
                    counter[token] += 1
    return [term for term, _count in counter.most_common(limit)]


def _contains_any(text: str, words: List[str]) -> bool:
    return any(word in text for word in words)


class AIWorkspaceService:
    def __init__(self) -> None:
        self.system_prompt = (
            "You are the AI Workspace assistant for a web testing platform. "
            "You help analyze test runs, reports, bugs, screenshots, and user memory. "
            "Answer concisely, use the provided platform data, and avoid inventing details."
        )
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY")) if AsyncOpenAI and os.getenv("OPENAI_API_KEY") else None
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if Groq and os.getenv("GROQ_API_KEY") else None

    async def _generate_llm_response(self, messages: List[Dict[str, str]]) -> Optional[str]:
        if self.openai_client is not None:
            try:
                response = await self.openai_client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    messages=messages,
                    temperature=0.2,
                )
                return response.choices[0].message.content or ""
            except Exception:
                pass

        if self.groq_client is not None:
            try:
                response = self.groq_client.chat.completions.create(
                    model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                    messages=messages,
                    temperature=0.2,
                )
                return response.choices[0].message.content or ""
            except Exception:
                pass

        return None

    def _memory_context(self, user_id: str) -> str:
        memories = memory_engine.list_memories(user_id)
        if not memories:
            return ""
        lines = []
        for memory in memories[:8]:
            lines.append(f"- [{memory.get('memory_type', 'general')}] {memory.get('content', '')}")
        return "\n".join(lines)

    def _conversation_context(self, session_id: str, user_id: str) -> str:
        history = memory_engine.get_session_history(session_id, user_id, limit=10)
        if not history:
            return ""
        parts = []
        for item in history[-8:]:
            role = item.get("role", "user")
            content = _clean_text(item.get("content") or item.get("message") or "")
            if content:
                parts.append(f"{role}: {content}")
        return "\n".join(parts)

    def _fallback_chat_response(self, query: str, context: Dict[str, Any], memories: str, history: str) -> str:
        intent = context.get("intent", "general_chat")
        data = context.get("data", [])

        if intent == "report_analysis":
            if not data:
                return "I could not find a matching report. Try specifying a latest report, report id, or test run id."
            report = data[0]
            summary = str(report.get("summary") or report.get("report") or "").strip()
            title = str(report.get("title") or report.get("test_name") or "Report").strip()
            status = str(report.get("status") or "unknown").strip()
            report_type = str(report.get("report_type") or "legacy").strip()
            return (
                f"Report analysis for {title}:\n"
                f"- Type: {report_type}\n"
                f"- Status: {status}\n"
                f"- Summary: {summary or 'No summary available.'}\n"
                f"- Suggested next step: inspect the latest failures and related bugs."
            )

        if intent == "query_bugs":
            if not data:
                return "I could not find matching bugs. Try keywords like authentication, critical, flaky, or resolved."
            top_terms = _top_terms(data, ["bug_name", "bug_description", "status", "severity"])
            return (
                f"Bug analysis for {len(data)} matching bug(s):\n"
                f"- Common themes: {', '.join(top_terms) if top_terms else 'not enough data to cluster'}\n"
                f"- Highest priority items should be the critical and unresolved bugs in this set."
            )

        if intent == "screenshot_analysis":
            if not data:
                return "No screenshots are available for this report or test run."
            return (
                f"I found {len(data)} screenshot artifact(s).\n"
                f"- Review each artifact for the bug linked to the selected report or test run.\n"
                f"- Use the screenshot path or URL to inspect layout, errors, and visible failures."
            )

        if intent == "test_run_analysis":
            if not data:
                return "I could not find a matching test run. Try asking for the latest test run or a specific run id."
            run = data[0]
            return (
                f"Test run analysis:\n"
                f"- Name: {run.get('test_name') or run.get('project') or 'Untitled run'}\n"
                f"- Status: {run.get('status') or 'unknown'}\n"
                f"- Goal: {run.get('goal') or run.get('instruction') or 'No goal recorded.'}\n"
                f"- Use the report and bugs panels to inspect the linked evidence."
            )

        if memories:
            lowered_query = query.lower()
            if _contains_any(lowered_query, ["what platform", "working on", "which project", "what project"]):
                memory_lines = [line for line in memories.splitlines() if line.strip().startswith("-")]
                if memory_lines:
                    first = memory_lines[0].split("]", 1)[-1].strip()
                    return f"You previously shared: {first}"
            return (
                "I used your saved memory and platform context to answer this. "
                "Try asking for the latest report, bugs, screenshots, or a specific test run."
            )

        return "I am ready to analyze your test runs, reports, bugs, screenshots, and saved memory."

    def _extract_memory_command(self, user_id: str, query: str) -> Optional[Dict[str, Any]]:
        command = resolve_memory_action(user_id, query)
        return command if command.get("action") else None

    # ------------------------------------------------------------------ #
    #  Instruction-intent classifier                                       #
    # ------------------------------------------------------------------ #

    # Action tokens that signal "the user wants me to produce something".
    _ACTION_TOKENS = frozenset([
        "generate", "create", "write", "build", "make", "draft",
        "give", "produce", "compose",
    ])

    # Artifact tokens that narrow the intent to instruction/plan/prompt.
    _ARTIFACT_TOKENS = frozenset([
        "instruction", "instructions", "plan", "plans",
        "scenario", "scenarios", "prompt", "prompts",
        "template", "objective", "objectives", "test-plan", "testplan",
    ])

    # Exact legacy phrases kept for backwards-compatibility.
    _LEGACY_INSTRUCTION_PHRASES = (
        "generate instruction",
        "generate instructions",
        "create instruction",
        "test objective",
    )

    def _is_instruction_request(self, query: str) -> bool:
        """Return True when the user wants an instruction / test-plan generated.

        Uses token-aware matching so that:
          - word order does not matter
          - filler words ("me", "a", "an", "some", "AI", "testing") are ignored
          - any action + artifact combination is accepted

        Examples that must return True
        --------------------------------
        "Generate me an instruction"
        "Create test instructions"
        "Write testing instructions"
        "Build a test plan"
        "Generate a prompt"
        "Create test scenarios"
        "Generate instructions for SauceDemo"
        "Generate a Run Test prompt"
        "Create AI testing instructions"
        "Write test instructions for login flow"
        """
        lowered = query.lower()

        # Stage 1 – legacy exact-phrase match (zero regression risk).
        if any(phrase in lowered for phrase in self._LEGACY_INSTRUCTION_PHRASES):
            return True

        # Stage 2 – token-aware match.
        tokens = set(re.split(r"[\s\-_/]+", lowered))
        has_action = bool(tokens & self._ACTION_TOKENS)
        has_artifact = bool(tokens & self._ARTIFACT_TOKENS)
        return has_action and has_artifact

    def _instruction_topic_from_query(self, query: str) -> str:
        """Extract the testing topic from a natural-language instruction request.

        Strips leading action phrases ("generate instructions for",
        "create test instructions for", etc.) before returning the topic
        so that the template engine receives a clean noun phrase.
        """
        # Remove leading action + artifact words up to and including "for"/"about".
        cleaned = re.sub(
            r"^(?:" + r"|".join(self._ACTION_TOKENS) + r")[\s\w]*?"
            r"(?:" + r"|".join(self._ARTIFACT_TOKENS) + r")[\s\w]*?"
            r"(?:for|about|on|regarding|of)?\s*",
            "",
            query.strip(),
            flags=re.IGNORECASE,
        ).strip().rstrip(".?")

        if cleaned and len(cleaned) >= 2:
            return cleaned

        # Fallback: look for "for <topic>" or "about <topic>" anywhere.
        lowered = query.lower()
        for marker in ("for ", "about ", "on ", "regarding "):
            index = lowered.find(marker)
            if index >= 0:
                topic = query[index + len(marker):].strip().rstrip(".?")
                if topic:
                    return topic

        return _clean_text(query)

    def _format_run_summary(self, payload: Dict[str, Any]) -> str:
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        selected = details.get("selected") if isinstance(details.get("selected"), dict) else {}
        summary = payload.get("summary") or details.get("summary") or ""
        if not selected:
            return summary or "No matching run was found."
        return "\n".join(
            line
            for line in [
                summary,
                f"- Status: {selected.get('status') or 'unknown'}",
                f"- Health score: {selected.get('health_score', 0)}",
                f"- Bugs: {selected.get('bug_count', 0)}",
                f"- Failures: {selected.get('failure_count', 0)}",
            ]
            if line
        )

    def _format_bug_summary(self, payload: Dict[str, Any]) -> str:
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        selected = details.get("selected") if isinstance(details.get("selected"), dict) else {}
        summary = payload.get("summary") or details.get("summary") or ""
        if not selected:
            return summary or "No matching bug was found."
        return "\n".join(
            line
            for line in [
                summary,
                f"- Severity: {selected.get('severity') or 'unknown'}",
                f"- Status: {selected.get('status') or 'unknown'}",
                f"- Root cause: {selected.get('root_cause') or 'unknown'}",
            ]
            if line
        )

    def _format_screenshot_summary(self, payload: Dict[str, Any]) -> str:
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        selected = details.get("selected")
        summary = payload.get("summary") or details.get("summary") or ""
        if isinstance(selected, list):
            return f"{summary}\n- Screenshots: {len(selected)}".strip()
        if not isinstance(selected, dict):
            return summary or "No matching screenshot was found."
        return "\n".join(
            line
            for line in [
                summary,
                f"- Path: {selected.get('path') or 'unknown'}",
                f"- Stage: {selected.get('stage') or 'unknown'}",
            ]
            if line
        )

    def _format_compare_summary(self, payload: Dict[str, Any]) -> str:
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        comparison = details.get("comparison_result") if isinstance(details.get("comparison_result"), dict) else {}
        summary = payload.get("summary") or details.get("summary") or ""
        if not comparison:
            return summary or "Unable to resolve both runs for comparison."
        bug_delta = comparison.get("bug_delta", {}) if isinstance(comparison.get("bug_delta"), dict) else {}
        metrics_delta = comparison.get("metrics_delta", {}) if isinstance(comparison.get("metrics_delta"), dict) else {}
        return "\n".join(
            line
            for line in [
                summary,
                f"- Verdict: {comparison.get('verdict', 'unknown')}",
                f"- New bugs: {bug_delta.get('new_bugs', 0)}",
                f"- Resolved bugs: {bug_delta.get('resolved_bugs', 0)}",
                f"- Health delta: {metrics_delta.get('website_health_score', {}).get('delta', 0)}",
            ]
            if line
        )

    def _format_analytics_summary(self, payload: Dict[str, Any]) -> str:
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        summary = details.get("summary") or payload.get("summary") or ""
        if not details:
            return summary or "No analytics data was available."
        highlights = []
        for key in ("most_bugs_run", "most_failures_run", "authentication_run", "api_failures_run", "best_run", "worst_run"):
            item = details.get(key)
            if isinstance(item, dict) and item.get("label"):
                highlights.append(f"- {key.replace('_', ' ').title()}: {item.get('label')}")
        return "\n".join([summary, *highlights]).strip()

    async def generate_response(self, user_id: str, session_id: str, query: str, active_context: ActiveContext) -> Dict[str, Any]:
        clean_query = _clean_text(query)

        memory_command = self._extract_memory_command(user_id, clean_query)
        if memory_command:
            if memory_command.get("action") == "save":
                saved = save_memory(user_id, memory_command["memory_type"], memory_command["content"], importance=80)
                ai_message = f"Saved to memory: {memory_command['content']}"
                assistant_payload = {"memory": saved}
                intent = "memory_update"
            elif memory_command.get("action") == "delete":
                deleted = delete_memory_by_query(user_id, memory_command.get("target", ""))
                ai_message = f"Removed memory: {deleted.get('content') if deleted else memory_command.get('target') or 'latest memory item'}"
                assistant_payload = {"memory": deleted or {}}
                intent = "memory_delete"
            elif memory_command.get("action") == "list":
                memories = memory_command.get("items") or []
                ai_message = "Your memories:\n" + "\n".join(f"- [{item.get('memory_type', 'general')}] {item.get('content', '')}" for item in memories) if memories else "You have no saved memories."
                assistant_payload = {"memories": memories}
                intent = "memory_list"
            else:
                ai_message = "I could not process that memory request."
                assistant_payload = {}
                intent = "memory_error"
            memory_engine.save_message(session_id=session_id, role="user", content=query, user_id=user_id)
            memory_engine.save_message(session_id=session_id, role="assistant", content=ai_message, user_id=user_id, retrieved_data=[])
            return {
                "session_id": session_id,
                "response": ai_message,
                "intent": intent,
                "retrieved_count": 0,
                "retrieved_data": [],
                "assistant_payload": assistant_payload,
            }

        if self._is_instruction_request(clean_query):
            topic = self._instruction_topic_from_query(clean_query)
            generated = await self.generate_instruction(topic)
            ai_message = generated["instructions"]
            memory_engine.save_message(session_id=session_id, role="user", content=query, user_id=user_id)
            memory_engine.save_message(session_id=session_id, role="assistant", content=ai_message, user_id=user_id, retrieved_data=[])
            return {
                "session_id": session_id,
                "response": ai_message,
                "intent": "instruction_generation",
                "retrieved_count": 0,
                "retrieved_data": [],
                "assistant_payload": generated,
            }

        retrieved_context = retrieval_system.get_context(user_id, query, report_id=active_context.report, test_run_id=active_context.test_run_id)
        context_details = retrieved_context.get("details") if isinstance(retrieved_context.get("details"), dict) else {}
        history_text = self._conversation_context(session_id, user_id)
        memory_text = self._memory_context(user_id)

        ai_message = ""
        if retrieved_context.get("intent") == "compare_runs":
            ai_message = self._format_compare_summary(retrieved_context)
        elif retrieved_context.get("intent") == "historical_analytics":
            ai_message = self._format_analytics_summary(retrieved_context)
        elif retrieved_context.get("intent") == "query_bugs":
            ai_message = self._format_bug_summary(retrieved_context)
        elif retrieved_context.get("intent") == "screenshot_analysis":
            ai_message = self._format_screenshot_summary(retrieved_context)
        elif retrieved_context.get("intent") == "test_run_analysis":
            ai_message = self._format_run_summary(retrieved_context)

        messages = [{"role": "system", "content": self.system_prompt}]
        if memory_text:
            messages.append({"role": "system", "content": f"Saved user memory:\n{memory_text}"})
        if history_text:
            messages.append({"role": "system", "content": f"Conversation history:\n{history_text}"})
        if retrieved_context.get("data"):
            messages.append({"role": "system", "content": f"Relevant platform data:\n{_truncate_json(retrieved_context['data'])}"})
        messages.append({"role": "user", "content": query})

        use_llm = bool(retrieved_context.get("data")) or bool(memory_text) or bool(history_text)
        if not ai_message:
            ai_message = await self._generate_llm_response(messages) if use_llm else None
        if not ai_message or _looks_placeholder_like(ai_message):
            ai_message = self._fallback_chat_response(query, retrieved_context, memory_text, history_text)

        memory_engine.save_message(session_id=session_id, role="user", content=query, user_id=user_id)
        memory_engine.save_message(
            session_id=session_id,
            role="assistant",
            content=ai_message,
            user_id=user_id,
            retrieved_data=retrieved_context.get("data", []),
        )

        return {
            "session_id": session_id,
            "response": ai_message,
            "intent": retrieved_context.get("intent", "general_chat"),
            "retrieved_count": len(retrieved_context.get("data", [])),
            "retrieved_data": retrieved_context.get("data", []),
            "assistant_payload": {},
        }

    async def analyze_report(self, user_id: str, query: str = "", report_id: Optional[str] = None) -> Dict[str, Any]:
        summary = retrieval_system.summarize_reports(user_id, query=query, report_id=report_id)
        selected = summary.get("selected_report") or {}
        insight_lines = []
        if summary.get("critical_count"):
            insight_lines.append(f"{summary['critical_count']} report(s) show critical or failed status.")
        if summary.get("flaky_count"):
            insight_lines.append(f"{summary['flaky_count']} report(s) mention flaky behavior.")
        if summary.get("by_type"):
            insight_lines.append("Report types seen: " + ", ".join(f"{k} ({v})" for k, v in summary["by_type"].items()))
        if not insight_lines:
            insight_lines.append("No high-signal report trends were found from the selected data.")
        return {
            "report": selected,
            "summary": {
                "total": summary.get("count", 0),
                "insights": insight_lines,
                "critical_count": summary.get("critical_count", 0),
                "flaky_count": summary.get("flaky_count", 0),
                "by_type": summary.get("by_type", {}),
            },
            "reports": summary.get("reports", []),
        }

    async def analyze_bugs(self, user_id: str, query: str = "") -> Dict[str, Any]:
        summary = retrieval_system.summarize_bugs(user_id, query=query)
        recommendations = []
        if summary.get("by_severity", {}).get("critical"):
            recommendations.append("Prioritize critical bugs first.")
        if summary.get("by_status", {}).get("open"):
            recommendations.append("Focus on open bugs and reproduce them with evidence.")
        recommendations.append("Review duplicate bug groups and consolidate evidence.")
        return {
            "summary": summary,
            "recommendations": recommendations,
        }

    async def analyze_screenshots(self, user_id: str, report_id: Optional[str] = None, test_run_id: Optional[str] = None) -> Dict[str, Any]:
        return retrieval_system.summarize_screenshots(user_id, report_id=report_id, test_run_id=test_run_id)

    def _instruction_template(self, topic: str) -> Dict[str, List[str]]:
        topic_text = topic.lower()
        focus = ["Login validation", "Session persistence", "Navigation testing"]
        requirements = ["Visit all pages", "Capture screenshots for bugs", "Generate bug reports with evidence"]
        if any(word in topic_text for word in ["auth", "authentication", "login", "bank", "security"]):
            focus = ["Login validation", "Invalid login handling", "Session persistence", "Logout flow", "Security testing"]
            requirements = ["Visit every page after login", "Capture screenshots for every bug", "Store bug evidence", "Generate final report"]
        elif any(word in topic_text for word in ["ecommerce", "shop", "checkout"]):
            focus = ["Login validation", "Signup validation", "Checkout flow", "Session persistence", "Navigation testing"]
            requirements = ["Visit all major pages", "Capture bugs with evidence", "Validate checkout and cart flows"]
        elif any(word in topic_text for word in ["stock", "market", "trading", "finance"]):
            focus = ["Login validation", "Signup validation", "Market data validation", "API validation", "Session persistence"]
            requirements = ["Visit every page after login", "Capture screenshots for every bug", "Store bug evidence", "Generate final report"]
        return {"focus": focus, "requirements": requirements}

    async def generate_instruction(self, topic: str) -> Dict[str, str]:
        return generate_instruction_template(topic)

    async def get_recommendations(self, user_id: str) -> List[str]:
        memory_count = len(memory_engine.list_memories(user_id))
        reports = retrieval_system.retrieve_reports(user_id, "latest", limit=3)
        bugs = retrieval_system.retrieve_bugs(user_id, "open", limit=5)
        recommendations = [
            "Review the latest report and focus on unresolved failures.",
            "Keep authentication flows in the first pass of testing.",
        ]
        if reports:
            recommendations.append(f"You have {len(reports)} recent report(s) available for analysis.")
        if bugs:
            recommendations.append(f"There are {len(bugs)} bug record(s) available for triage.")
        if memory_count:
            recommendations.append(f"{memory_count} memory item(s) are available and will be included in chat prompts.")
        return recommendations


workspace_service = AIWorkspaceService()
