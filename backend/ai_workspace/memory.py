from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pymongo import ReturnDocument

from backend.ai_workspace.models import ActiveContext, ChatSession
from backend.database.mongo import ai_chat_messages, ai_chat_sessions, ai_memory_collection


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_context(context: Optional[ActiveContext | Dict[str, Any]]) -> ActiveContext:
    if isinstance(context, ActiveContext):
        return context
    if isinstance(context, dict):
        return ActiveContext(**context)
    return ActiveContext()


def _session_title_from_context(context: ActiveContext, fallback: str = "New Chat") -> str:
    for candidate in [context.workflow, context.report, context.website, context.test_run_id, context.bug_id]:
        text = str(candidate or "").strip()
        if text:
            return text[:80]
    return fallback


class AIMemoryEngine:
    def get_or_create_session(
        self,
        session_id: Optional[str],
        user_id: str,
        context: Optional[ActiveContext | Dict[str, Any]] = None,
        title: Optional[str] = None,
    ) -> ChatSession:
        active_context = _normalize_context(context)

        if session_id:
            session_data = ai_chat_sessions.find_one({"session_id": session_id, "user_id": user_id}, {"_id": 0})
            if session_data:
                update_fields: Dict[str, Any] = {"updated_at": _now()}
                if context is not None:
                    update_fields["active_context"] = active_context.model_dump()
                if title and title.strip() and session_data.get("title") != title.strip():
                    update_fields["title"] = title.strip()
                ai_chat_sessions.update_one({"session_id": session_id, "user_id": user_id}, {"$set": update_fields})
                session_data.update(update_fields)
                session_data["active_context"] = _normalize_context(session_data.get("active_context")).model_dump()
                return ChatSession(**session_data)

        new_session = ChatSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            title=(title or _session_title_from_context(active_context)).strip() or "New Chat",
            created_at=_now(),
            updated_at=_now(),
            active_context=active_context,
        )
        ai_chat_sessions.insert_one(new_session.model_dump())
        return new_session

    def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        return list(ai_chat_sessions.find({"user_id": user_id}, {"_id": 0}).sort("updated_at", -1))

    def rename_session(self, session_id: str, user_id: str, title: str) -> Optional[Dict[str, Any]]:
        clean_title = title.strip()
        if not clean_title:
            return None
        return ai_chat_sessions.find_one_and_update(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {"title": clean_title, "updated_at": _now()}},
            return_document=ReturnDocument.AFTER,
        )

    def delete_session(self, session_id: str, user_id: str) -> bool:
        session_result = ai_chat_sessions.delete_one({"session_id": session_id, "user_id": user_id})
        ai_chat_messages.delete_many({"session_id": session_id, "user_id": user_id})
        return session_result.deleted_count > 0

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: str,
        retrieved_data: Optional[List[Dict[str, Any]]] = None,
        ai_summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        msg = {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": _now(),
            "retrieved_data": retrieved_data or [],
            "ai_summary": ai_summary,
        }
        ai_chat_messages.insert_one(msg)
        ai_chat_sessions.update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {"updated_at": _now()}},
        )
        return msg

    def get_session_history(self, session_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = ai_chat_messages.find({"session_id": session_id, "user_id": user_id}, {"_id": 0}).sort("timestamp", 1).limit(limit)
        return list(cursor)

    def upsert_memory(self, user_id: str, memory_type: str, content: str, importance: int = 50) -> Dict[str, Any]:
        payload = {
            "memory_id": str(uuid.uuid4()),
            "user_id": user_id,
            "memory_type": memory_type.strip(),
            "content": content.strip(),
            "importance": max(1, min(100, int(importance or 50))),
            "created_at": _now(),
            "updated_at": _now(),
        }
        ai_memory_collection.insert_one(payload)
        payload.pop("_id", None)
        return payload

    def update_memory(self, memory_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        set_fields: Dict[str, Any] = {"updated_at": _now()}
        for key in ["memory_type", "content", "importance"]:
            value = updates.get(key)
            if value is not None:
                set_fields[key] = value.strip() if isinstance(value, str) else value
        result = ai_memory_collection.find_one_and_update(
            {"memory_id": memory_id, "user_id": user_id},
            {"$set": set_fields},
            return_document=ReturnDocument.AFTER,
        )
        if result:
            result.pop("_id", None)
        return result

    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        return ai_memory_collection.delete_one({"memory_id": memory_id, "user_id": user_id}).deleted_count > 0

    def list_memories(self, user_id: str) -> List[Dict[str, Any]]:
        return list(ai_memory_collection.find({"user_id": user_id}, {"_id": 0}).sort([("importance", -1), ("created_at", -1)]))

    def get_user_memory(self, user_id: str) -> List[Dict[str, Any]]:
        return self.list_memories(user_id)


memory_engine = AIMemoryEngine()
