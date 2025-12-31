import joblib

model = joblib.load("models/trend_model.pkl")
FEATURES = joblib.load("models/model_features.pkl")

def predict_trend(X_latest):
    probs = model.predict_proba(X_latest)[0]
    idx = probs.argmax()
    trend_map = {1: "UP", 0: "STABLE", -1: "DOWN"}
    return trend_map[model.classes_[idx]], float(probs[idx])
