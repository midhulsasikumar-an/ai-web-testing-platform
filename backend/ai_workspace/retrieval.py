import re
from datetime import datetime, timedelta
from typing import Dict, Any, List
from backend.database.mongo import collection as test_runs, bug_collection, ai_knowledge_index

class AIRetrievalSystem:
    def __init__(self):
        pass

    def parse_date_query(self, query: str) -> Dict[str, Any]:
        """
        Convert natural language dates (e.g., 'yesterday', 'last month') to MongoDB date filters.
        """
        now = datetime.utcnow()
        query_lower = query.lower()
        
        date_filter = {}
        
        if "yesterday" in query_lower:
            start = now - timedelta(days=1)
            date_filter = {"$gte": start.strftime("%Y-%m-%dT00:00:00"), "$lt": now.strftime("%Y-%m-%dT00:00:00")}
        elif "last week" in query_lower:
            start = now - timedelta(days=7)
            date_filter = {"$gte": start.isoformat()}
        elif "last month" in query_lower:
            start = now - timedelta(days=30)
            date_filter = {"$gte": start.isoformat()}
            
        return date_filter

    def retrieve_reports(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        filter_query = {"user_id": user_id}
        
        # Date parsing
        date_filter = self.parse_date_query(query)
        if date_filter:
            filter_query["start_time"] = date_filter
            
        # Basic keyword matching for websites
        if "amazon" in query.lower():
            filter_query["url"] = {"$regex": "amazon", "$options": "i"}
            
        # Status filtering
        if "failed" in query.lower():
            filter_query["status"] = "failed"
            
        cursor = test_runs.find(filter_query, {"_id": 0}).sort("start_time", -1).limit(limit)
        return list(cursor)

    def retrieve_bugs(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        filter_query = {"user_id": user_id}
        
        if "recurring" in query.lower():
            filter_query["is_flaky"] = True # Approximation
        if "resolved" in query.lower():
            filter_query["status"] = "resolved"
            
        cursor = bug_collection.find(filter_query, {"_id": 0}).limit(limit)
        return list(cursor)

    def determine_intent(self, query: str) -> str:
        """
        Simple keyword-based intent routing.
        """
        q = query.lower()
        if "compare" in q:
            return "compare_runs"
        if "workflow" in q and "generate" in q:
            return "generate_workflow"
        if "bug" in q or "issue" in q:
            return "query_bugs"
        if "report" in q or "run" in q:
            return "query_reports"
        
        return "general_chat"
        
    def get_context(self, user_id: str, query: str) -> Dict[str, Any]:
        """
        Retrieve relevant contextual information based on intent.
        """
        intent = self.determine_intent(query)
        context = {"intent": intent, "data": []}
        
        if intent in ["query_reports", "compare_runs"]:
            context["data"] = self.retrieve_reports(user_id, query)
        elif intent == "query_bugs":
            context["data"] = self.retrieve_bugs(user_id, query)
            
        return context

retrieval_system = AIRetrievalSystem()
