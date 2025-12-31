import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
def llm_reasoning(data):
    prompt = f"""
You are an AI advisor for construction procurement.

Respond in the following structure ONLY:

DECISION:
BUY / WAIT / BULK BUY

WHY:
- Bullet points (max 4)

RISKS:
- Bullet points (max 3)

Context:
Product: {data['product']}
Trend: {data['trend']}
Confidence: {data['confidence']}
Climate Risk: {data['climate']}
Market Price Range: {data['min']} – {data['max']}
"""

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        reasoning_effort="medium",
        max_completion_tokens=350,
        stream=True
    )

    chunks = []
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta:
            if chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)

    return "".join(chunks).strip()
