import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from groq import Groq

load_dotenv()

# Initialize Clients
GROQ_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

cerebras_client = OpenAI(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1"
) if os.getenv("CEREBRAS_API_KEY") else None

openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
) if os.getenv("OPENROUTER_API_KEY") else None


GEMINI_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None


def is_rate_limit(e: Exception) -> bool:
    """Detects if the error is a quota/rate limit to trigger an immediate failover."""
    txt = str(e).lower()
    return any(k in txt for k in ["429", "quota", "rate", "capacity", "limit", "too many", "503", "overloaded"])


def groq_call(sys_prompt, user_content):
    if not groq_client: raise RuntimeError("Groq missing")
    r = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.1
    )
    return r.choices[0].message.content


def cerebras_call(sys_prompt, user_content):
    if not cerebras_client: raise RuntimeError("Cerebras missing")
    r = cerebras_client.chat.completions.create(
        model="gpt-oss-120b",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.1
    )
    return r.choices[0].message.content


def openrouter_call(sys_prompt, user_content):
    if not openrouter_client: raise RuntimeError("OpenRouter missing")
    r = openrouter_client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_content}
        ],
        temperature=0.1,
        extra_headers={"HTTP-Referer": "https://deadhunt.app", "X-Title": "DeadHunt"}
    )
    return r.choices[0].message.content


def gemini_call(sys_prompt, user_content):
    if not gemini_client: raise RuntimeError("Gemini missing")
    r = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config={"system_instruction": sys_prompt, "temperature": 0.1}
    )
    return r.text


# The Priority Queue: Put your fastest/highest-limit models first.
ROUTING_QUEUE = [gemini_call, groq_call, cerebras_call, openrouter_call]

def generate_audit(system_prompt: str, json_payload: str) -> str:
    """
    Attempts to generate the audit report by cascading through available LLM providers.
    """
    last_error = None

    for provider in ROUTING_QUEUE:
        try:
            print(f"[Router] Attempting execution via {provider.__name__}...")
            return provider(system_prompt, json_payload)

        except Exception as e:
            last_error = e
            print(f"[Router] {provider.__name__} failed: {e}")

            if is_rate_limit(e):
                print(f"[Router] Rate limit detected. Failing over to next provider.")
                continue

            time.sleep(1)
            try:
                print(f"[Router] Retrying {provider.__name__}...")
                return provider(system_prompt, json_payload)
            except Exception:
                continue

    raise RuntimeError(f"CRITICAL: All LLM providers exhausted. Last error: {last_error}")