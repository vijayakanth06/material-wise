import requests, re, numpy as np
from bs4 import BeautifulSoup

# Expected price ranges (₹) to eliminate garbage
EXPECTED_RANGES = {
    "steel": (30000, 90000),   # per tonne
    "iron": (30000, 90000),
    "bars": (30000, 90000),
    "rods": (30000, 90000),
    "blooms": (25000, 80000),
}

def scrape_indiamart_prices(product):
    query = product.replace(" ", "-").lower()
    url = f"https://dir.indiamart.com/impcat/{query}.html"

    headers = {"User-Agent": "Mozilla/5.0"}
    prices = []

    try:
        html = requests.get(url, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(text=re.compile(r"₹")):
            nums = re.findall(r"\d{3,6}", tag)
            for n in nums:
                prices.append(int(n))
    except Exception:
        return None

    if not prices:
        return None

    # Infer range
    low, high = 0, 1e9
    for k, (l, h) in EXPECTED_RANGES.items():
        if k in product.lower():
            low, high = l, h
            break

    filtered = [p for p in prices if low <= p <= high]

    if len(filtered) < 3:
        return None

    return {
        "min": min(filtered),
        "max": max(filtered),
        "median": int(np.median(filtered)),
        "variance": float(np.var(filtered) / (np.mean(filtered) ** 2)),
        "unit": "₹/tonne"
    }
