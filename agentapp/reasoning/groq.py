import os
import requests
from typing import Dict, Optional

try:
    from groq import Groq  # optional
    GROQ_AVAILABLE = True
except Exception:
    GROQ_AVAILABLE = False


def _build_human_summary(decision: str, payload: Dict) -> str:
    product = payload.get('product')
    market = payload.get('market', {})
    median = market.get('median') if market.get('status') == 'available' else None
    prob = payload.get('trend_prob', 0)
    conf = payload.get('confidence_label', 'Low')
    climate = payload.get('climate_label', 'Unknown')

    lines = []
    lines.append(f"Recommendation: {decision}.")
    if median:
        lines.append(f"Observed market median price: ₹{median} — the central price across scraped sources.")
    else:
        lines.append("Live market prices are unavailable or insufficient to show a reliable median price.")

    lines.append(f"Reason: model indicates '{payload.get('trend')}' trend with probability {(prob*100):.0f}% and confidence '{conf}'.")
    lines.append(f"Climate risk: '{climate}'.")

    if decision == 'BUY':
        lines.append("Next step: request quotations from suppliers and confirm lead times.")
    elif decision == 'WAIT':
        lines.append("Next step: monitor prices and re-check in a short period before purchasing.")
    else:
        lines.append("Next step: consider bulk ordering only after confirming supplier discounts and logistics.")

    return " \n".join(lines)


def _call_ollama(prompt: str, model: str, ollama_url: str) -> Optional[str]:
    """Call an Ollama-compatible local HTTP endpoint. Returns text or None.
    The Ollama server must be running and reachable at `ollama_url` (e.g. http://localhost:11434).
    """
    try:
        resp = requests.post(
            f"{ollama_url.rstrip('/')}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        resp.raise_for_status()
        j = resp.json()
        # try common response keys
        if isinstance(j, dict):
            if 'response' in j:
                return j['response']
            if 'choices' in j and isinstance(j['choices'], list) and j['choices']:
                c = j['choices'][0]
                if isinstance(c, dict) and 'message' in c and 'content' in c['message']:
                    return c['message']['content']
                if 'text' in c:
                    return c['text']
        return None
    except Exception:
        return None


def groq_reasoning(payload: Dict) -> Dict[str, str]:
    """Multi-backend LLM reasoning wrapper.
    Supported backends (controlled by env `LLM_BACKEND`):
      - groq: uses Groq client (requires GROQ_API_KEY)
      - ollama: calls an Ollama-compatible HTTP endpoint (set OLLAMA_URL)

    If no backend is available, returns deterministic, auditable reasoning.
    Returns: {'structured': str, 'summary': str}
    """
    prompt = f"""
You are an evidence-driven procurement assistant. Use ONLY the evidence provided below. Do NOT invent prices.
Respond STRICTLY in the format below.

DECISION:
<BUY / WAIT / BULK BUY>

EVIDENCE USED:
{payload.get('evidence_list','')}

ANALYSIS:
- (max 4 bullets)

RISKS & LIMITATIONS:
- (max 3 bullets)

DATA NOTES:
- (explicit about missing data)

Context:
Product: {payload.get('product')}
Trend: {payload.get('trend')}
Trend Probability: {payload.get('trend_prob')}
Confidence: {payload.get('confidence_label')}
Climate Risk: {payload.get('climate_label')}
Market Summary: {payload.get('market_summary')}
"""

    backend = os.getenv('LLM_BACKEND', 'groq').lower()

    # 1) Try Groq if selected and configured
    if backend == 'groq' and GROQ_AVAILABLE and os.getenv('GROQ_API_KEY'):
        try:
            client = Groq(api_key=os.getenv('GROQ_API_KEY'))
            completion = client.chat.completions.create(
                model=os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b'),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                reasoning_effort='medium',
                max_completion_tokens=100,
                stream=False
            )
            text = completion.choices[0].message.content.strip()
            decision = 'WAIT'
            for ln in text.splitlines():
                if ln.strip().upper().startswith('DECISION:'):
                    decision = ln.split(':',1)[1].strip() or decision
                    break
            return {'structured': text, 'summary': _build_human_summary(decision, payload)}
        except Exception:
            pass

    # 2) Try Ollama (useful for local models like llama-3.3-70b-versatile)
    ollama_url = os.getenv('OLLAMA_URL')
    ollama_model = os.getenv('OLLAMA_MODEL', 'llama-3.3-70b-versatile')
    if backend == 'ollama' and ollama_url:
        text = _call_ollama(prompt, ollama_model, ollama_url)
        if text:
            decision = 'WAIT'
            for ln in text.splitlines():
                if ln.strip().upper().startswith('DECISION:'):
                    decision = ln.split(':',1)[1].strip() or decision
                    break
            return {'structured': text, 'summary': _build_human_summary(decision, payload)}

    # 3) Groq or Ollama not available or failed — return deterministic reasoning
    evidence = payload.get('evidence', [])
    evidence_lines = [f"{i+1}. {e.get('label')} - {e.get('source_url')}" for i, e in enumerate(evidence)]

    trend = payload.get('trend')
    prob = payload.get('trend_prob', 0)
    conf_label = payload.get('confidence_label', 'Low')
    market = payload.get('market')

    # Rule-based decision logic (transparent and auditable)
    if trend == 'UP' and prob > 0.6:
        decision = 'WAIT'
    elif trend == 'DOWN' and prob > 0.55:
        decision = 'BUY'
    elif trend == 'STABLE' and conf_label == 'High':
        decision = 'BULK BUY'
    else:
        decision = 'WAIT'

    analysis = []
    if market and market.get('status') == 'available':
        analysis.append(f"Live market median: {market.get('median')} {market.get('unit')}")
    else:
        analysis.append("Live market prices unavailable or insufficient to form market signal.")

    analysis.append(f"Historical trend: {trend} (prob {prob})")
    analysis.append(f"Climate risk level: {payload.get('climate_label')}")

    risks = ["Market scraping may miss JS-rendered prices.", "Model may be unavailable; fallback used."]
    data_notes = []
    if market and market.get('status') != 'available':
        data_notes.append(market.get('reason'))
    data_notes.append("LLM backend not configured or failed; returned deterministic reasoning.")

    parts = []
    parts.append(f"DECISION:\n{decision}\n\nEVIDENCE USED:\n")
    for ln in evidence_lines:
        parts.append(ln + "\n")
    parts.append("\nANALYSIS:\n")
    for a in analysis[:4]:
        parts.append(f"- {a}\n")
    parts.append("\nRISKS & LIMITATIONS:\n")
    for r in risks[:3]:
        parts.append(f"- {r}\n")
    parts.append("\nDATA NOTES:\n")
    for d in data_notes[:3]:
        parts.append(f"- {d}\n")

    structured = "".join(parts)
    summary = _build_human_summary(decision, payload)
    return {'structured': structured, 'summary': summary}
