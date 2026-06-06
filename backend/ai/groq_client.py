from __future__ import annotations

import asyncio
import os

from groq import Groq


client = Groq(api_key=os.getenv("GROQ_API_KEY"))


async def ask_groq(system_prompt: str, user_prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
    def _call() -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    return await asyncio.to_thread(_call)
