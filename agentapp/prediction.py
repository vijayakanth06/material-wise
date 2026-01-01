import os
import joblib
import numpy as np
from typing import Tuple, Dict

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'trend_model.pkl'))
FEATURES_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'models', 'model_features.pkl'))


def _fallback_trend(X_row: dict) -> Tuple[str, float, str]:
    # Deterministic safe fallback: compute relative change between price_index and lag_1
    price = float(X_row.get('price_index', 0))
    lag1 = float(X_row.get('lag_1', price))
    lag3 = float(X_row.get('lag_3_mean', price))

    change = (price - lag1) / (lag1 + 1e-6)
    if change > 0.02:
        return 'UP', min(0.65, 0.5 + change), 'model_unavailable'
    elif change < -0.02:
        return 'DOWN', min(0.65, 0.5 - change), 'model_unavailable'
    else:
        return 'STABLE', 0.5, 'model_unavailable'


def predict_trend(X_latest) -> Tuple[str, float, str]:
    """Return (trend, probability, status).
    Attempts to load a trained model from ../models; if unavailable, uses safe fallback.
    """
    try:
        model = joblib.load(MODEL_PATH)
        # model expects DataFrame-like ordering; support pandas DataFrame or dict
        if hasattr(X_latest, 'values'):
            probs = model.predict_proba(X_latest)[0]
        else:
            # assume dict
            import pandas as pd
            Xdf = pd.DataFrame([X_latest])
            probs = model.predict_proba(Xdf)[0]

        idx = int(np.argmax(probs))
        classes = model.classes_
        trend = str(classes[idx])
        prob = float(probs[idx])
        return trend, prob, 'model_loaded'
    except Exception:
        # fallback deterministic rule
        if hasattr(X_latest, 'to_dict'):
            row = X_latest.to_dict(orient='records')[0]
        elif isinstance(X_latest, dict):
            row = X_latest
        else:
            try:
                row = dict(zip(X_latest.columns, X_latest.iloc[0].values))
            except Exception:
                row = {}
        return _fallback_trend(row)
