def confidence_score(model_prob, market_variance, climate_risk):
    market_consistency = max(0, 1 - market_variance)

    score = (
        0.55 * model_prob +
        0.25 * market_consistency +
        0.20 * (1 - climate_risk)
    )

    if score >= 0.75:
        label = "High"
    elif score >= 0.5:
        label = "Medium"
    else:
        label = "Low"

    return round(score, 2), label
