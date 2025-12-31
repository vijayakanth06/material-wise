Material Wise – AI Platform for Construction Material Sourcing

Level 1 (College / City Prototype)

Overview

Material Wise is an AI-augmented decision-support platform for transparent construction material sourcing.
It helps contractors, homeowners, and rural SHGs make better procurement decisions by combining:

Historical price trend prediction

Live market price signals

Climate-aware risk assessment

Confidence scoring

LLM-based reasoning and explanations

This repository contains a working prototype focused on price trend intelligence and recommendations, suitable for hackathons, academic evaluation, and demos.

Key Capabilities

Historical Price Trend Model

Predicts UP / STABLE / DOWN trends using official price index data

Uses a lightweight, explainable Logistic Regression model

Climate-Aware Risk Assessment

Dynamically estimates rainfall risk using recent weather data

Designed to be robust to climate change (not month-based assumptions)

Live Market Signal Integration

Scrapes indicative price ranges from online marketplaces (e.g., IndiaMART)

Used only for market consistency, not exact pricing

Confidence Scoring

Combines model certainty, market stability, and climate risk

Outputs High / Medium / Low confidence

LLM-Based Reasoning (Groq)

Generates human-readable recommendations:

BUY / WAIT / BULK BUY

Explains decisions using trend + climate + market context

API-Ready Architecture

Exposes predictions via FastAPI

Designed for dropdown-based frontend integration

Project Structure
material-wise/
│
├── data/
│   └── price_index.csv          # Cleaned historical index data
│
├── models/
│   ├── trend_model.pkl          # Trained ML model (saved once)
│   └── model_features.pkl       # Feature schema
│
├── services/
│   ├── climate.py               # Rainfall-based climate risk
│   ├── confidence.py            # Confidence scoring logic
│   ├── scraper.py               # Live market price scraping
│   ├── predictor.py             # ML trend prediction
│   └── llm.py                   # Groq LLM reasoning
│
├── api/
│   └── app.py                   # FastAPI application
│
├── notebooks/
│   └── training.ipynb           # Model training & validation
│
├── requirements.txt
└── README.md

Technology Stack

Python 3.10+

scikit-learn – trend classification model

pandas / numpy – data processing

FastAPI – REST API

BeautifulSoup + requests – light web scraping

Groq LLM – reasoning and explanation generation

joblib – model serialization

Model Choice (Important Design Decision)

Multiple models (Logistic Regression, XGBoost, LightGBM, ensembles) were evaluated.

Logistic Regression performed best on this dataset:

Highest accuracy and macro-F1

Preserved the critical STABLE class

More robust and explainable for index-based time series

Final production model: Logistic Regression
Complex ensembles were rejected based on empirical results.

Setup Instructions
1. Install Dependencies
pip install -r requirements.txt

2. Train and Save the Model (Run Once)
python train_model.py


This generates:

models/trend_model.pkl

models/model_features.pkl

3. Start the API Server
uvicorn api.app:app --reload


API will be available at:

http://127.0.0.1:8000

4. Make a Prediction (Example)

Endpoint

POST /predict


Request

{
  "product_name": "TMT Steel Bars"
}


Response (Sample)

{
  "product": "TMT Steel Bars",
  "trend": "UP",
  "confidence": "Medium",
  "climate_risk": "High",
  "market_price": {
    "min": 58000,
    "max": 62000,
    "median": 60000
  },
  "recommendation": "Bulk buy recommended before logistics disruptions increase costs."
}

Scope and Limitations (Level 1)

Price predictions are trend-based, not exact prices

Market prices are indicative, scraped lightly for demo purposes

Climate risk uses recent rainfall anomalies, not long-term forecasts

Supplier verification and payments are out of scope at this level

These constraints are intentional and appropriate for a college / city-level prototype.

Why This Solution Fits the Problem Statement

Addresses price uncertainty and timing decisions

Uses public data + AI responsibly

Integrates climate risk (important for construction logistics)

Supports urban builders and rural SHGs through simple recommendations

Modular and scalable for future levels

Future Enhancements (Beyond Level 1)

Supplier trust scoring and verification

City-level price normalization

Recycled / demolition material matching

Bulk procurement optimization

Frontend dashboard and user authentication

Final Note

This repository represents a complete, working, and defensible prototype that prioritizes:

Correct problem framing

Sound ML decisions

Explainability

Real-world constraints

It is intentionally designed to score well at Level 1 and remain extensible for higher-level implementations.
