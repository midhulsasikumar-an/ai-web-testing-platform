import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from backend.database.mongo import ai_chat_sessions, ai_chat_messages, ai_memory_collection
from backend.ai_workspace.models import ChatSession, ActiveContext

class AIMemoryEngine:
    def __init__(self):
        pass

    def get_or_create_session(self, session_id: Optional[str], user_id: str, context: Optional[ActiveContext] = None) -> ChatSession:
        if session_id:
            session_data = ai_chat_sessions.find_one({"session_id": session_id, "user_id": user_id})
            if session_data:
                if context:
                    # Update context
                    ai_chat_sessions.update_one(
                        {"session_id": session_id},
                        {"$set": {"active_context": context.dict(), "updated_at": datetime.utcnow()}}
                    )
                    session_data["active_context"] = context.dict()
                
                # Convert back to object
                session_data.pop("_id", None)
                return ChatSession(**session_data)

        # Create new session
        new_session_id = str(uuid.uuid4())
        new_session = ChatSession(
            session_id=new_session_id,
            user_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            active_context=context or ActiveContext()
        )
        
        ai_chat_sessions.insert_one(new_session.dict())
        return new_session

    def save_message(self, session_id: str, role: str, message: str, retrieved_data: List[Dict[str, Any]] = None, ai_summary: str = None):
        msg = {
            "session_id": session_id,
            "role": role,
            "message": message,
            "timestamp": datetime.utcnow(),
            "retrieved_data": retrieved_data or [],
            "ai_summary": ai_summary
        }
        ai_chat_messages.insert_one(msg)
        ai_chat_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )
        return msg

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        cursor = ai_chat_messages.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", -1).limit(limit)
        return list(cursor)[::-1]  # reverse to get chronological order

    def update_user_memory(self, user_id: str, topic: str, context_data: Dict[str, Any]):
        """
        Store long-term memory like recurring topics, preferences, frequently analyzed websites.
        """
        ai_memory_collection.update_one(
            {"user_id": user_id, "topic": topic},
            {"$set": {"context_data": context_data, "updated_at": datetime.utcnow()}},
            upsert=True
        )

    def get_user_memory(self, user_id: str) -> List[Dict[str, Any]]:
        return list(ai_memory_collection.find({"user_id": user_id}, {"_id": 0}))

memory_engine = AIMemoryEngine()
