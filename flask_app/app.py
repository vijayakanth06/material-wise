from flask import Flask, render_template, request
import pandas as pd

# Import your existing pipeline
from services.features import build_latest_features
from services.predictor import predict_trend
from services.climate import rainfall_risk_tn
from services.scraper import scrape_buildersmart_prices
from services.confidence import confidence_score
from services.llm import llm_reasoning

app = Flask(__name__)


import logging
log = logging.getLogger('werkzeug')
class Ignore404(logging.Filter):
    def filter(self, record):
        return '404' not in record.getMessage()
log.addFilter(Ignore404())



DATA_PATH = "data/price_index.csv"

# Load once for dropdown
df = pd.read_csv(DATA_PATH)

KEYWORDS = ["steel", "iron", "bars", "rods", "alloy", "metal"]

MATERIALS = sorted(
    df[df["comm_name"].str.lower().apply(
        lambda x: any(k in x for k in KEYWORDS)
    )]["comm_name"].unique()
)
def build_sources(product):
    return [
        {
            "label": "Wholesale Price Trend (MOSPI – WPI Metals)",
            "url": "https://www.mospi.gov.in/web/mospi/wholesale-price-index"
        },
        {
            "label": f"Live Market Listings for {product} (IndiaMART)",
            "url": f"https://dir.indiamart.com/search.mp?ss={product.replace(' ', '+')}"
        },
        {
            "label": "Rainfall & Climate Risk (Open-Meteo API)",
            "url": "https://open-meteo.com/en/docs"
        }
    ]


@app.route("/", methods=["GET", "POST"])
def index():
    result = None

    if request.method == "POST":
        product = request.form.get("product")

        # Build features
        X_latest = build_latest_features(
            csv_path=DATA_PATH,
            feature_names=["price_index", "lag_1", "lag_3_mean"]
        )

        trend, model_prob = predict_trend(X_latest)
        climate_score, climate_label = rainfall_risk_tn()

        market = scrape_buildersmart_prices(product)

        if market["status"] == "available":
            market_view = {
                "available": True,
                "text": f"{market['unit']}: ₹{market['min']} – ₹{market['max']} (Median ₹{market['median']})",
                "source_url": market["source_url"],
                "search_term": market["search_term"]
            }
            market_variance = market["variance"]
        else:
            market_view = {
                "available": False,
                "text": market["reason"],
                "source_url": market["source_url"]
            }
            market_variance = 0.6

        conf_score, conf_label = confidence_score(
            model_prob,
            market_variance,
            climate_score
        )


        explanation = llm_reasoning({
            "product": product,
            "trend": trend,
            "confidence": conf_label,
            "climate": climate_label,
            "market_status": market["status"],
            "market_text": market_view["text"]
        })


        result = {
            "product": product,
            "trend": trend,
            "confidence": conf_label,
            "climate": climate_label,
            "market": market_view,
            "explanation": explanation,
        }



    return render_template("index.html", materials=MATERIALS, result=result)

if __name__ == "__main__":
    app.run(debug=True)
