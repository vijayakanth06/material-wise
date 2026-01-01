import requests
import re
import numpy as np
from bs4 import BeautifulSoup
from services.product_mapper import normalize_product_name
from agentapp.ingestion.crawler import crawl_material_links
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import requests

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


def scrape_prices_from_link(url: str) -> dict:
    """Scrape a given product/category page URL and return numeric price indicators.

    This function focuses on extracting numeric price tokens from a specific page (more precise than site search).
    """
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-IN,en;q=0.9"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')

        nums = []
        for tag in soup.find_all(['span', 'div', 'p', 'li', 'td']):
            text = tag.get_text(separator=' ', strip=True)
            if '₹' in text or 'Rs.' in text or 'INR' in text:
                found = re.findall(r"\d{2,7}", text.replace(',', ''))
                nums.extend(int(x) for x in found)

        nums = [n for n in nums if 300 <= n <= 1000000]

        if not nums:
            return {"status": "unavailable", "reason": "no numeric prices found", "source_url": url}

        arr = np.array(nums)
        return {
            "status": "available",
            "source_url": url,
            "min": int(arr.min()),
            "max": int(arr.max()),
            "median": int(np.median(arr)),
            "variance": float(np.var(arr) / (np.mean(arr) ** 2)),
            "sample_count": int(len(arr)),
            "unit": "INR",
        }

    except Exception as e:
        return {"status": "unavailable", "reason": str(e), "source_url": url}


def crawl_and_scrape(materials: list, sites: list = None) -> dict:
    """Use the crawler to find best links for each material, then scrape those links.

    Returns a mapping: material -> {site: scrape_result}
    """
    links = crawl_material_links(materials, sites=sites)
    out = {}
    for m, site_map in links.items():
        out[m] = {}
        for s, link in site_map.items():
            if link:
                out[m][s] = scrape_prices_from_link(link)
            else:
                out[m][s] = {"status": "missing_link"}
    return out
