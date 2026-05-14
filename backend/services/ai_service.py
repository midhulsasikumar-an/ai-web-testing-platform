import os

from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

env_path = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(dotenv_path=env_path)

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


async def get_ai_response(message: str):

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are an AI software testing assistant.

                    Help users:
                    - test websites
                    - analyze bugs
                    - generate test cases
                    - explain UI issues
                    - provide QA recommendations
                    """
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            temperature=0.4,
            max_tokens=500
        )

        return response.choices[0].message.content

    except Exception as e:
        print("GROQ ERROR:", e)

        return str(e)