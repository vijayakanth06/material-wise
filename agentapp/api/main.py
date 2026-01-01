import os
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict

# ensure project root imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agentapp.ingestion.scrapers import scrape_buildersmart, scrape_indiamart
from agentapp.features import build_latest_features
from agentapp.prediction import predict_trend
from agentapp.reasoning.groq import groq_reasoning
from services.climate import rainfall_risk_tn
from services.confidence import confidence_score
from agentapp.ingestion.scrapers import get_available_categories
app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..', 'web', 'static')), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'web', 'templates'))

import logging

# Suppress noisy 404 access logs from uvicorn/uvicorn.access while keeping other logs
class Ignore404Access(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        # uvicorn access logs look like: '"GET /path HTTP/1.1" 404 -'
        if '"' in msg and ' 404 ' in msg:
            return False
        return True

logging.getLogger('uvicorn.access').addFilter(Ignore404Access())
# Optionally suppress all access logs (including 404s). Set SUPPRESS_ACCESS_LOGS=0 to keep them.
if os.getenv('SUPPRESS_ACCESS_LOGS', '1') == '1':
    try:
        logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    except Exception:
        pass

@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    # load materials for dropdown from CSV
    import pandas as pd
    csv_path = os.path.join(ROOT, 'data', 'price_index.csv')
    df = pd.read_csv(csv_path)
    materials = sorted(df['comm_name'].unique())
    return templates.TemplateResponse('index.html', {'request': request, 'materials': materials})

@app.get('/api/categories')
async def categories():
    return get_available_categories()

@app.post('/api/predict')
async def predict(request: Request):
    payload = await request.json()
    product = payload.get('product')
    if not product:
        return JSONResponse({'error': 'product required'}, status_code=400)

    csv_path = os.path.join(ROOT, 'data', 'price_index.csv')

    # 1. features
    try:
        X_latest = build_latest_features(csv_path, product, ['price_index', 'lag_1', 'lag_3_mean'])
    except Exception as e:
        return JSONResponse({'error': f'Feature error: {str(e)}'}, status_code=400)

    # 2. predict
    try:
        trend, prob, model_status = predict_trend(X_latest)
    except Exception as e:
        trend, prob, model_status = 'STABLE', 0.5, 'error'

    # 3. climate
    climate_score, climate_label = rainfall_risk_tn()

    # 4. scrape multiple sources
    sources = []
    b = scrape_buildersmart(product)
    sources.append(b)
    im = scrape_indiamart(product)
    sources.append(im)

    # aggregate market prices across sources
    all_prices = []
    evidence = []
    for s in sources:
        evidence.append({
            'label': s.get('label', 'unknown'),
            'source_url': s.get('source_url')
        })
        if s.get('status') == 'available':
            all_prices.extend(s.get('prices', []))

    market = {'status': 'unavailable', 'reason': 'No valid prices found across sources.'}
    if len(all_prices) >= 3:
        import numpy as np
        arr = np.array(all_prices)
        market = {
            'status': 'available',
            'min': int(arr.min()),
            'max': int(arr.max()),
            'median': int(np.median(arr)),
            'variance': float(np.var(arr) / (np.mean(arr) ** 2)),
            'unit': 'INR',
            'sources': [s for s in sources if s.get('status') == 'available']
        }

    # 5. confidence
    conf_score, conf_label = confidence_score(prob, market.get('variance', 1.0), climate_score)

    # 6. LLM reasoning
    reason_payload = {
        'product': product,
        'trend': trend,
        'trend_prob': prob,
        'confidence_label': conf_label,
        'climate_label': climate_label,
        'market': market,
        'market_summary': f"median: {market.get('median')} {market.get('unit')}" if market.get('status') == 'available' else 'Unavailable',
        'evidence': evidence,
        'evidence_list': '\n'.join([f"{i+1}. {e['label']} - {e['source_url']}" for i, e in enumerate(evidence)])
    }

    llm_text = groq_reasoning(reason_payload)

    response = {
        'product': product,
        'trend': trend,
        'trend_prob': prob,
        'model_status': model_status,
        'climate': {'score': climate_score, 'label': climate_label},
        'market': market,
        'confidence': {'score': conf_score, 'label': conf_label},
        'evidence': evidence,
        'llm': llm_text
    }

    return JSONResponse(response)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
