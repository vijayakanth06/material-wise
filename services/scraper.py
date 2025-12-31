import requests, re, numpy as np
from bs4 import BeautifulSoup
def scrape_indiamart_prices(product):
    query = product.replace(" ", "-").lower()
    url = f"https://dir.indiamart.com/search.mp?ss={query}"

    headers = {"User-Agent": "Mozilla/5.0"}
    prices = []

    try:
        html = requests.get(url, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup.find_all(text=re.compile(r"₹")):
            nums = re.findall(r"\d{3,6}", tag)
            prices.extend(int(n) for n in nums)

    except Exception:
        pass

    # HARD RULE: if prices unreliable → return None
    if len(prices) < 3:
        return {
            "status": "unavailable",
            "reason": "Most listings show 'Ask Price' or negotiated pricing.",
            "source_url": url
        }

    filtered = [p for p in prices if 20000 <= p <= 100000]

    if len(filtered) < 3:
        return {
            "status": "unavailable",
            "reason": "Prices vary widely; not reliable for aggregation.",
            "source_url": url
        }

    return {
        "status": "available",
        "min": min(filtered),
        "max": max(filtered),
        "median": int(np.median(filtered)),
        "unit": "₹/tonne",
        "source_url": url
    }
