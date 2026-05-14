import json
from groq import Groq


client = Groq()


async def analyze_test_results(test_results: dict):

    # LOAD PROMPT TEMPLATE
    with open("backend/ai/prompts/judgment_prompt.txt", "r", encoding="utf-8") as f:
        prompt_template = f.read()

    # INSERT RESULTS
    prompt = prompt_template.format(
        test_results=json.dumps(test_results, indent=2)
    )

    # CALL LLM
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {
                "role": "system",
                "content": "You are a strict AI QA analysis engine."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    raw_output = response.choices[0].message.content

    # CLEAN JSON BLOCKS
    raw_output = raw_output.replace("```json", "").replace("```", "").strip()

    # SAFE PARSE
    try:
        parsed = json.loads(raw_output)
        return parsed

    except Exception:
        return {
            "error": "Invalid AI judgment JSON",
            "raw": raw_output
        }