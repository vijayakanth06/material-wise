import requests, re, numpy as np
from bs4 import BeautifulSoup

def scrape_indiamart_prices(product):
    query = product.replace(" ", "-").lower()
    url = f"https://dir.indiamart.com/impcat/{query}.html"

    headers = {"User-Agent": "Mozilla/5.0"}
    prices = []

    try:
        html = requests.get(url, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all(text=re.compile(r"₹")):
            prices += [int(x) for x in re.findall(r"\d{2,6}", tag)]
    except Exception:
        pass

    if len(prices) < 5:
        return None

    return {
        "min": min(prices),
        "max": max(prices),
        "median": int(np.median(prices)),
        "variance": float(np.var(prices) / (np.mean(prices) ** 2))
    }
