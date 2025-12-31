import requests

def rainfall_risk_tn():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        "?latitude=13.08&longitude=80.27"
        "&daily=precipitation_sum"
        "&past_days=14"
        "&timezone=Asia/Kolkata"
    )

    try:
        data = requests.get(url, timeout=10).json()
        rainfall = sum(data["daily"]["precipitation_sum"])
    except Exception:
        rainfall = 15.0

    normal = 15.0
    anomaly = (rainfall - normal) / normal

    if anomaly > 0.3:
        return 0.8, "High"
    elif anomaly > 0.1:
        return 0.5, "Medium"
    else:
        return 0.2, "Low"
