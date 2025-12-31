import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def llm_reasoning(data):
    """
    Uses Groq streaming API to generate a procurement recommendation.
    Returns full text response.
    """

    prompt = f"""
You are an AI advisor for construction material procurement.

Product: {data['product']}
Historical Price Trend: {data['trend']}
Prediction Confidence: {data['confidence']}
Climate / Rainfall Risk: {data['climate']}
Market Price Range: ₹{data['min']} – ₹{data['max']}

Task:
- Recommend BUY / WAIT / BULK BUY
- Explain reasoning in 4–5 lines
- Mention risks and uncertainty clearly
"""

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.6,
        top_p=1,
        reasoning_effort="medium",
        max_completion_tokens=400,
        stream=True
    )

    final_response = []

    for chunk in completion:
        if chunk.choices and chunk.choices[0].delta:
            token = chunk.choices[0].delta.content
            if token:
                final_response.append(token)

    return "".join(final_response).strip()
