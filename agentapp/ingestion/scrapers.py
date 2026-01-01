import re
import requests
from bs4 import BeautifulSoup
import numpy as np
from typing import Dict, Any, List


def _extract_numbers(text: str) -> List[int]:
    # remove commas then find numbers of length >=3
    s = text.replace(',', '')
    nums = re.findall(r"\d{3,7}", s)
    return [int(n) for n in nums]


def _normalize_prices(prices: List[int]) -> List[int]:
    # realistic construction price bounds (INR)
    return [p for p in prices if 300 <= p <= 500000]


def scrape_buildersmart(product: str) -> Dict[str, Any]:
    """Scrape BuildersMART search results for numeric prices.
    Returns structured dict; never fabricates prices.
    """
    query = product.replace(' ', '+')
    url = f"https://www.buildersmart.in/catalogsearch/result?q={query}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-IN,en;q=0.9"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        prices = []
        for tag in soup.find_all(['span', 'div', 'p', 'li']):
            text = tag.get_text(separator=' ', strip=True)
            if '₹' in text or 'Rs.' in text or 'INR' in text:
                prices.extend(_extract_numbers(text))

        prices = _normalize_prices(prices)

        if len(prices) < 3:
            return {
                "status": "unavailable",
                "reason": "Insufficient numeric price points found (may be Ask Price or images/JS rendered).",
                "source_url": url,
                "label": "BuildersMART"
            }

        arr = np.array(prices)
        return {
            "status": "available",
            "label": "BuildersMART",
            "source_url": url,
            "prices": prices,
            "min": int(arr.min()),
            "max": int(arr.max()),
            "median": int(np.median(arr)),
            "variance": float(np.var(arr) / (np.mean(arr) ** 2)),
            "unit": "INR",
        }

    except Exception as e:
        return {
            "status": "unavailable",
            "reason": f"Scraping error: {str(e)}",
            "source_url": url,
            "label": "BuildersMART",
        }


def scrape_indiamart(product: str) -> Dict[str, Any]:
    """Lightweight IndiaMART scraping via search page.
    IndiaMART often uses JS; this will attempt to extract server-rendered prices.
    """
    query = product.replace(' ', '+')
    url = f"https://dir.indiamart.com/search.mp?ss={query}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-IN,en;q=0.9"}

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        prices = []
        for tag in soup.find_all(['span', 'div', 'p']):
            text = tag.get_text(separator=' ', strip=True)
            if '₹' in text or 'Rs.' in text:
                prices.extend(_extract_numbers(text))

        prices = _normalize_prices(prices)

        if len(prices) < 3:
            return {
                "status": "unavailable",
                "reason": "Insufficient numeric price points found (IndiaMART pages are often JS heavy).",
                "source_url": url,
                "label": "IndiaMART",
            }

        arr = np.array(prices)
        return {
            "status": "available",
            "label": "IndiaMART",
            "source_url": url,
            "prices": prices,
            "min": int(arr.min()),
            "max": int(arr.max()),
            "median": int(np.median(arr)),
            "variance": float(np.var(arr) / (np.mean(arr) ** 2)),
            "unit": "INR",
        }

    except Exception as e:
        return {
            "status": "unavailable",
            "reason": f"Scraping error: {str(e)}",
            "source_url": url,
            "label": "IndiaMART",
        }


BUILDERMART_CATEGORIES = {
    "Cement": ["OPC-53 Grade Cement", "PPC Cement"],
    "Sand & Aggregates": [],
    "TMT Steel Bars": ["Fe-500 Grade TMT Bars", "Fe-550 Grade TMT Bars", "TMT Binding Wire", "Rebar Couplers"],
    "Bricks & Blocks": ["Concrete Solid Blocks", "FlyashBricks", "Autoclaved Aerated Concrete (AAC) Blocks", "Red Bricks"],
    # Add more as needed
}

INDIAMART_CATEGORIES = {
    "Cement and Concrete": ["Portland Cement", "Slag Cement", "Cement", "Calcium Aluminate Cement"],
    "Bricks & Construction Aggregates": ["Building Materials", "River Sand", "Bricks", "Ceramic Brick", "Construction Sand"],
    # Add more as needed
}

def get_available_categories():
    return {
        "buildersmart": BUILDERMART_CATEGORIES,
        "indiamart": INDIAMART_CATEGORIES,
    }
