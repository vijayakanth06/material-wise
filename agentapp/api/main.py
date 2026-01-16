import os
import sys
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List, Dict
import logging

# ensure project root imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from agentapp.ingestion.scrapers import scrape_buildersmart, scrape_indiamart
from agentapp.features import build_latest_features
from agentapp.prediction import predict_trend
from agentapp.reasoning.groq import groq_reasoning
from agentapp.visualizations import create_comprehensive_visualization, create_multi_material_comparison
from agentapp.product_matcher import find_matching_product
from services.climate import rainfall_risk_tn
from services.confidence import confidence_score
from agentapp.ingestion.scrapers import get_available_categories
app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..', 'web', 'static')), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), '..', 'web', 'templates'))

# Suppress noisy 404 access logs from uvicorn.access while keeping other logs.
# Use SUPPRESS_ACCESS_LOGS=0 to keep access logs.
class Ignore404Access(logging.Filter):
    def filter(self, record):
        try:
            msg = record.getMessage()
        except Exception:
            return True
        # uvicorn access logs typically look like: '"GET /path HTTP/1.1" 404 -'
        if '"' in msg and ' 404 ' in msg:
            return False
        return True

logger_access = logging.getLogger('uvicorn.access')
logger_access.addFilter(Ignore404Access())
if os.getenv('SUPPRESS_ACCESS_LOGS', '1') == '1':
    try:
        logger_access.setLevel(logging.WARNING)
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


@app.get('/api/test-viz')
async def test_visualization():
    """Test endpoint to verify visualizations work"""
    try:
        import pandas as pd
        from datetime import datetime
        
        # Create test data
        dates = pd.date_range(end=datetime.now(), periods=12, freq='ME')
        df = pd.DataFrame({
            'date': dates,
            'price_index': [100, 102, 105, 103, 108, 110, 107, 112, 115, 113, 118, 120]
        })
        
        prediction = {
            'trend': 'UP',
            'probability': 0.75,
            'predicted_value': 125
        }
        
        scraper_results = {
            'buildersmart': {'status': 'available', 'median': 5300},
            'indiamart': {'status': 'available', 'median': 5450}
        }
        
        visualizations = create_comprehensive_visualization(
            df, prediction, scraper_results, "Test Cement"
        )
        
        return JSONResponse({
            'success': True,
            'line_graph_length': len(visualizations.get('line_graph', '')),
            'bar_graph_length': len(visualizations.get('bar_graph', '')),
            'line_graph_preview': visualizations.get('line_graph', '')[:100],
            'visualizations': visualizations
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status_code=500)


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

    # 7. Generate visualizations
    visualizations = {'line_graph': None, 'bar_graph': None}
    try:
        import pandas as pd
        # Get historical data for line graph
        df = pd.read_csv(csv_path)
        
        # Use improved product matching
        mask = find_matching_product(df, product, 'comm_name')
        
        if mask.sum() > 0:
            sub = df[mask]
            index_cols = [c for c in sub.columns if c.startswith('indx')]
            df_long = sub.melt(id_vars=['comm_name','comm_code','comm_wt'], 
                              value_vars=index_cols,
                              var_name='month', value_name='price_index')
            df_long['month'] = df_long['month'].str.replace('indx','', regex=False)
            df_long['date'] = pd.to_datetime(df_long['month'], format='%m%Y', errors='coerce')
            df_long = df_long.dropna(subset=['date']).sort_values('date').tail(12)  # Last 12 months
            
            if not df_long.empty:
                prediction_dict = {
                    'trend': trend,
                    'probability': prob,
                    'predicted_value': float(X_latest['price_index'].iloc[0])
                }
                
                scraper_results = {
                    'buildersmart': b,
                    'indiamart': im
                }
                
                visualizations = create_comprehensive_visualization(
                    df_long, prediction_dict, scraper_results, product
                )
            else:
                visualizations = {'line_graph': None, 'bar_graph': None, 'error': 'No historical data available'}
        else:
            visualizations = {'line_graph': None, 'bar_graph': None, 'error': 'Product not found in CSV'}
    except Exception as e:
        import traceback
        visualizations = {
            'line_graph': None, 
            'bar_graph': None, 
            'error': f'{str(e)}',
            'traceback': traceback.format_exc()
        }

    response = {
        'product': product,
        'trend': trend,
        'trend_prob': prob,
        'model_status': model_status,
        'climate': {'score': climate_score, 'label': climate_label},
        'market': market,
        'confidence': {'score': conf_score, 'label': conf_label},
        'evidence': evidence,
        'llm': llm_text,
        'visualizations': visualizations
    }

    return JSONResponse(response)


@app.post('/api/visualize')
async def visualize(request: Request):
    """Generate visualizations for materials"""
    payload = await request.json()
    materials = payload.get('materials', [])
    
    if not materials:
        return JSONResponse({'error': 'materials list required'}, status_code=400)
    
    csv_path = os.path.join(ROOT, 'data', 'price_index.csv')
    results = []
    
    for product in materials:
        try:
            # Get latest features
            X_latest = build_latest_features(csv_path, product, ['price_index', 'lag_1', 'lag_3_mean'])
            trend, prob, _ = predict_trend(X_latest)
            
            # Scrape prices
            b = scrape_buildersmart(product)
            im = scrape_indiamart(product)
            
            results.append({
                'name': product,
                'model_price': float(X_latest['price_index'].iloc[0]),
                'indiamart_price': im.get('median') if im.get('status') == 'available' else None,
                'buildersmart_price': b.get('median') if b.get('status') == 'available' else None,
                'trend': trend
            })
        except Exception as e:
            results.append({
                'name': product,
                'model_price': None,
                'indiamart_price': None,
                'buildersmart_price': None,
                'error': str(e)
            })
    
    # Create multi-material comparison
    try:
        comparison_chart = create_multi_material_comparison(results)
    except Exception as e:
        comparison_chart = None
    
    return JSONResponse({
        'materials': results,
        'comparison_chart': comparison_chart
    })


if __name__ == '__main__':
    import uvicorn
    # Control access logs via SUPPRESS_ACCESS_LOGS env var (default: '1' to suppress)
    access_log = False if os.getenv('SUPPRESS_ACCESS_LOGS', '1') == '1' else True
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info', access_log=access_log)
