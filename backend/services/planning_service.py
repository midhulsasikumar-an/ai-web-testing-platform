import os
import re
from groq import Groq
import json

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def load_prompt():
    with open("backend/ai/prompts/test_plan_prompt.txt", "r") as f:
        return f.read()
    
def extract_json(text: str):
    # remove ```json ... ``` wrappers
    cleaned = re.sub(r"```json|```", "", text).strip()
    return json.loads(cleaned)

async def generate_test_plan(url: str, dom: dict):

    prompt_template = load_prompt()

    prompt = prompt_template.format(
        url=url,
        dom=json.dumps(dom, indent=2)
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    content = response.choices[0].message.content

    try:
        return extract_json(content)
    except Exception as e:
        return {
            "error": "Invalid JSON from model",
            "raw": content,
            "exception": str(e)
        }