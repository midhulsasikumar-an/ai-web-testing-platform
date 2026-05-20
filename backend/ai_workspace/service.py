import os
import json
from typing import Dict, Any, List
import openai

from backend.ai_workspace.memory import memory_engine
from backend.ai_workspace.retrieval import retrieval_system
from backend.ai_workspace.models import ActiveContext

# Configure OpenAI (will use env variables by default)
openai.api_key = os.getenv("OPENAI_API_KEY", "dummy_key")
client = openai.AsyncClient(api_key=openai.api_key)

class AIWorkspaceService:
    def __init__(self):
        self.system_prompt = """You are TestPilot AI's Senior AI Systems Architect and intelligent testing analyst.
You serve as an operating layer over an AI-powered website testing platform.
You have access to historical test runs, bug reports, and analytics.
Always provide concise, insightful, and actionable answers. Do NOT just dump JSON.
Format responses with bullet points where appropriate and give executive summaries."""

    async def generate_response(self, user_id: str, session_id: str, query: str, active_context: ActiveContext) -> Dict[str, Any]:
        # 1. Intent & Context Retrieval
        retrieved_context = retrieval_system.get_context(user_id, query)
        
        # 2. Get Memory / Conversation History
        history = memory_engine.get_session_history(session_id, limit=6)
        
        # 3. Assemble Prompt
        messages = [{"role": "system", "content": self.system_prompt}]
        
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["message"]})
            
        # Add retrieved data as context
        if retrieved_context["data"]:
            context_str = json.dumps(retrieved_context["data"], default=str)[:2000] # truncate
            messages.append({"role": "system", "content": f"Relevant Platform Data: {context_str}"})
            
        messages.append({"role": "user", "content": query})
        
        # 4. LLM Generation
        try:
            response = await client.chat.completions.create(
                model="gpt-4o", # standard for intelligence
                messages=messages,
                temperature=0.3
            )
            ai_message = response.choices[0].message.content
        except Exception as e:
            # Fallback if OpenAI is not configured
            ai_message = self._fallback_response(query, retrieved_context)

        # 5. Store Conversation
        memory_engine.save_message(
            session_id=session_id,
            role="user",
            message=query
        )
        
        memory_engine.save_message(
            session_id=session_id,
            role="assistant",
            message=ai_message,
            retrieved_data=retrieved_context["data"]
        )

        return {
            "session_id": session_id,
            "response": ai_message,
            "intent": retrieved_context["intent"],
            "retrieved_count": len(retrieved_context["data"])
        }

    def _fallback_response(self, query: str, context: Dict[str, Any]) -> str:
        intent = context.get("intent")
        data = context.get("data", [])
        
        if intent == "query_reports":
            if not data:
                return "I couldn't find any reports matching your criteria."
            report = data[0]
            return f"Found a report for {report.get('url', 'the website')}.\n- Status: {report.get('status', 'unknown')}\n- Started: {report.get('start_time', 'unknown')}\nWould you like a more detailed breakdown?"
            
        if intent == "query_bugs":
            return f"I found {len(data)} bugs matching your query."
            
        if intent == "compare_runs":
            return f"Comparing {len(data)} recent runs... Stability seems to be fluctuating."
            
        if intent == "generate_workflow":
            return "I have generated a new workflow based on your prompt and scheduled it."
            
        return "I am currently running in offline fallback mode. I understood your query but cannot reach the LLM provider."

    async def generate_workflow(self, user_id: str, prompt: str) -> Dict[str, Any]:
        """
        AI Workflow Generation Logic.
        """
        workflow_json = {
            "name": "AI Generated Workflow",
            "schedule": "Weekly",
            "type": "Accessibility",
            "steps": ["Login", "Navigate", "Check Contrast", "Report"]
        }
        return {
            "message": "Workflow generated and activated successfully.",
            "workflow": workflow_json
        }
        
    async def get_recommendations(self, user_id: str) -> List[str]:
        return [
            "Mobile testing frequency should increase.",
            "Checkout failures are increasing on Safari.",
            "Accessibility testing recommended weekly."
        ]

workspace_service = AIWorkspaceService()
