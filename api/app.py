from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd

from services.climate import rainfall_risk_tn
from services.scraper import scrape_indiamart_prices
from services.confidence import confidence_score
from services.predictor import predict_trend, FEATURES
from services.llm import llm_reasoning
from services.features import build_latest_features

app = FastAPI(title="Material Wise AI")

class ProductRequest(BaseModel):
    product_name: str
@app.post("/predict")
def predict(req: ProductRequest):
    X_latest = build_latest_features(
        csv_path="data/price_index.csv",
        feature_names=FEATURES
    )

    trend, prob = predict_trend(X_latest)
    climate_score, climate_label = rainfall_risk_tn()

    market = scrape_indiamart_prices(req.product_name) or {
        "min": None,
        "max": None,
        "variance": 0.4
    }

    conf_score, conf_label = confidence_score(
        prob, market["variance"], climate_score
    )

    explanation = llm_reasoning({
        "product": req.product_name,
        "trend": trend,
        "confidence": conf_label,
        "climate": climate_label,
        "min": market["min"],
        "max": market["max"]
    })

    return {
        "product": req.product_name,
        "trend": trend,
        "confidence": conf_label,
        "climate_risk": climate_label,
        "market_price": market,
        "recommendation": explanation
    }
