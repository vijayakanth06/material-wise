import requests
import re
import numpy as np
from bs4 import BeautifulSoup
from services.product_mapper import normalize_product_name

def scrape_buildersmart_prices(product):
    """
    Scrape BuildersMART for numeric prices using normalized product names
    """

    search_term = normalize_product_name(product)
    query = search_term.replace(" ", "+")
    url = f"https://www.buildersmart.in/search?q={query}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-IN,en;q=0.9"
    }

    prices = []

    try:
        html = requests.get(url, headers=headers, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        # BuildersMART price blocks often look like:
        # <span>₹ 52,000</span>
        for span in soup.find_all("span"):
            text = span.get_text(strip=True)
            if "₹" in text:
                nums = re.findall(r"\d{2,6}", text.replace(",", ""))
                prices.extend(int(n) for n in nums)

    except Exception as e:
        return {
            "status": "unavailable",
            "reason": f"Scraping error: {str(e)}",
            "source_url": url
        }

    # realistic construction material prices
    prices = [p for p in prices if 300 <= p <= 150000]

    if len(prices) < 3:
        return {
            "status": "unavailable",
            "reason": f"No consistent numeric prices found for '{search_term}' on BuildersMART.",
            "source_url": url
        }

    prices = np.array(prices)

    return {
        "status": "available",
        "min": int(prices.min()),
        "max": int(prices.max()),
        "median": int(np.median(prices)),
        "variance": float(np.var(prices) / (np.mean(prices) ** 2)),
        "unit": "₹ (indicative retail)",
        "search_term": search_term,
        "source_url": url
    }
