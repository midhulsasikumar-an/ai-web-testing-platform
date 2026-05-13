import os

from pathlib import Path
from dotenv import load_dotenv
from google import genai

env_path = Path(__file__).resolve().parent.parent / ".env"

load_dotenv(dotenv_path=env_path)

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

async def get_ai_response(message: str):

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""
            You are an AI software testing assistant.
            Help users:
            - test websites
            - analyze bugs
            - generate test cases
            - explain UI issues

            User message:
            {message}
            """
        )

        return response.text

    except Exception as e:
        print("GEMINI ERROR:", e)

        return str(e)