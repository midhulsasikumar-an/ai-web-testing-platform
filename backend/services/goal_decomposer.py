import json

from backend.ai.groq_client import ask_groq


SYSTEM_PROMPT = """
You are an autonomous AI QA planner.

Your task:
Convert user testing instructions into
ordered executable goals.

Rules:
- Return ONLY valid JSON
- Goals must be short
- Goals must be actionable
- Preserve execution order
- Avoid duplicates

Output format:

{
  "goals": [
    {
      "goal": "login",
      "priority": 1
    }
  ]
}
"""


async def decompose_goal(
    user_prompt: str
):

    prompt = f"""
USER REQUEST:
{user_prompt}

Generate execution goals.
"""

    response = await ask_groq(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt
    )

    cleaned = clean_json_response(response)

    return json.loads(cleaned)


def clean_json_response(text: str):

    text = text.strip()

    if "```json" in text:
        text = text.split("```json")[1]

    if "```" in text:
        text = text.split("```")[0]

    return text.strip()