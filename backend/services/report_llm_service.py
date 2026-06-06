from __future__ import annotations

import os
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger("services.report_llm")


@dataclass
class LLMConfig:
    groq_key: Optional[str] = None
    openai_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"
    openai_model: str = "gpt-4o-mini"


def _get_config() -> LLMConfig:
    return LLMConfig(
        groq_key=os.getenv("GROQ_API_KEY"),
        openai_key=os.getenv("OPENAI_API_KEY"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )


def enhance_narrative(prompt: str, timeout: int = 6) -> Optional[str]:
    """Attempt to call an LLM to enhance the narrative. Graceful fallback on any failure.

    This implementation supports Groq or OpenAI if keys are present. It will not raise on failure.
    """
    cfg = _get_config()
    try:
        if cfg.groq_key:
            # lightweight Groq client usage if available
            try:
                from groq import Groq

                client = Groq(api_key=cfg.groq_key)
                resp = client.chat.completions.create(model=cfg.groq_model, messages=[{"role":"user","content":prompt}], temperature=0.0)
                return resp.choices[0].message.content
            except Exception as e:
                message = str(e)
                if "model_not_found" in message or "404" in message:
                    logger.info("groq LLM unavailable; using deterministic report fallback")
                else:
                    logger.warning("groq LLM failed: %s", e)
        if cfg.openai_key:
            try:
                import openai

                openai.api_key = cfg.openai_key
                resp = openai.ChatCompletion.create(model=cfg.openai_model, messages=[{"role":"user","content":prompt}], temperature=0.0)
                return resp.choices[0].message.content
            except Exception as e:
                message = str(e)
                if "model_not_found" in message or "404" in message:
                    logger.info("openai LLM unavailable; using deterministic report fallback")
                else:
                    logger.warning("openai LLM failed: %s", e)
    except Exception as e:
        logger.exception("LLM enhancement error: %s", e)
    return None
