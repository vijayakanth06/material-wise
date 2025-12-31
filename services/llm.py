import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))



def llm_reasoning(data):
    prompt = f"""
You are an AI analyst. You must justify every conclusion.

Respond STRICTLY in this format:

DECISION:
<BUY / WAIT / BULK BUY>

EVIDENCE USED:
1. Historical trend from Government Wholesale Price Index (MOSPI)
2. Live market signal from IndiaMART listings
3. Climate risk from Open-Meteo rainfall anomaly API

ANALYSIS:
- Bullet points (max 4) explaining how the above evidence supports the decision

RISKS & LIMITATIONS:
- Bullet points (max 3)

DATA NOTES:
- If market price is unavailable, explicitly state why.

Context:
Product: {data['product']}
Trend: {data['trend']}
Confidence: {data['confidence']}
Climate Risk: {data['climate']}
Market Status: {data['market_status']}
Market Price: {data['market_text']}
"""

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        reasoning_effort="medium",
        max_completion_tokens=500,
        stream=True
    )

    chunks = []
    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta:
            if chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)

    return "".join(chunks).strip()
