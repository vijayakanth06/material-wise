# AgentApp — Material Wise MCP Agent

This `agentapp` package provides a separate, modular implementation of the Material Cost Prediction (MCP) Agent.

Key features
- Multiple scrapers (BuildersMART, IndiaMART) that extract numeric prices only
- Feature engineering from existing `data/price_index.csv`
- Prediction engine that loads a trained model from `models/` if available; deterministic fallback otherwise
- Climate risk via Open-Meteo (reuses `services.climate`)
- Groq reasoning wrapper (uses `GROQ_API_KEY` if configured; otherwise returns deterministic, evidence-based output and documents missing LLM)
- FastAPI JSON API and minimal web UI at `/`

Run
----
Install dependencies:

```bash
pip install -r agentapp/requirements.txt
```

Start the app (from project root):

```bash
python -m agentapp.api.main
```

Open http://127.0.0.1:8000

Notes & limitations
- Scrapers attempt to extract server-rendered numeric prices only. Many marketplaces use JS and may not expose prices server-side; when that happens scrapers will mark data as unavailable and explain why.
- The Groq LLM is used only when `GROQ_API_KEY` is set; otherwise the system returns a deterministic, auditable reasoning text that does not invent prices.
- The prediction engine prefers a trained model located at `models/trend_model.pkl`. If missing, a transparent fallback rule is used (based on recent price change).

Ethics & transparency
- No fabricated prices — when live prices are missing the system states why and marks market as unavailable.
- All sources are cited with clickable links in responses.
- LLM outputs are constrained to evidence and the system documents when the LLM is not available.
