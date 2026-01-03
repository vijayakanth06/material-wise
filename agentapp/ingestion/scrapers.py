import re
import json
import requests
from bs4 import BeautifulSoup
import numpy as np
from typing import Dict, Any, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def _extract_numbers(text: str) -> List[int]:
    # remove commas then find numbers of length >=3
    s = text.replace(',', '')
    nums = re.findall(r"\d{3,7}", s)
    return [int(n) for n in nums]


def _normalize_prices(prices: List[int]) -> List[int]:
    # realistic construction price bounds (INR)
    return [p for p in prices if 300 <= p <= 500000]


def _build_session():
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; material-wise-agent/1.0)", "Accept-Language": "en-IN,en;q=0.9"})
    return session


def scrape_buildersmart(product: str) -> Dict[str, Any]:
    """Scrape BuildersMART for the given product using prioritized candidate URLs.
    Returns structured dict with `source_url` indicating the canonical page used and `candidate_urls` tried.
    """
    session = _build_session()

    def _slugify(s: str) -> str:
        s = s.strip().lower()
        s = re.sub(r"[^a-z0-9\s-]", '', s)
        s = re.sub(r"\s+", '-', s)
        return s

    def _candidates(prod: str) -> List[str]:
        p = prod.strip().lower()
        qs = prod.replace(' ', '+')
        mapping = {
            'ppc cement': '/buy-cement-online/ppc',
            'ppc': '/buy-cement-online/ppc',
            '53 grade cement': '/buy-cement-online/53-grade-cement',
            'birla white cement': '/birla-white-cement-50kg-26711'
        }
        candidates: List[str] = []
        for k, path in mapping.items():
            if re.search(rf"\b{re.escape(k)}\b", p):
                candidates.append(f"https://www.buildersmart.in{path}")

        slug = _slugify(product)
        if slug:
            candidates.append(f"https://www.buildersmart.in/{slug}")
            candidates.append(f"https://www.buildersmart.in/{slug}-price")

        if 'cement' in p:
            candidates.append('https://www.buildersmart.in/buy-cement-online')
        if 'tmt' in p or 'steel' in p or 'bars' in p:
            candidates.append('https://www.buildersmart.in/tmt-steel')

        candidates.append(f"https://www.buildersmart.in/catalogsearch/result?q={qs}")

        seen = set()
        out = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    candidates = _candidates(product)
    last_exc = None
    tried: List[str] = []
    for candidate in candidates:
        try:
            r = session.get(candidate, timeout=10)
            r.raise_for_status()
            tried.append(candidate)
            soup = BeautifulSoup(r.text, 'html.parser')

            prices: List[int] = []
            # JSON-LD first
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    j = json.loads(script.string or '{}')
                    if isinstance(j, dict) and 'offers' in j:
                        off = j['offers']
                        if isinstance(off, dict) and 'price' in off:
                            try:
                                prices.append(int(float(off['price'])))
                            except Exception:
                                pass
                except Exception:
                    pass

            if not prices:
                for tag in soup.find_all(['span', 'div', 'p', 'li']):
                    text = tag.get_text(separator=' ', strip=True)
                    if '₹' in text or 'Rs.' in text or 'INR' in text:
                        prices.extend(_extract_numbers(text))

            prices = _normalize_prices(prices)

            if len(prices) >= 3:
                arr = np.array(prices)
                return {
                    "status": "available",
                    "label": "BuildersMART",
                    "source_url": candidate,
                    "candidate_urls": tried,
                    "prices": prices,
                    "min": int(arr.min()),
                    "max": int(arr.max()),
                    "median": int(np.median(arr)),
                    "variance": float(np.var(arr) / (np.mean(arr) ** 2)) if np.mean(arr) else 0.0,
                    "unit": "INR",
                }

        except Exception as e:
            last_exc = e
            tried.append(candidate)
            continue

    reason = "Insufficient numeric price points found across candidates."
    if last_exc:
        reason = f"Scraping errors encountered; last: {str(last_exc)}"
    return {
        "status": "unavailable",
        "reason": reason,
        "source_url": candidates[0] if candidates else None,
        "candidate_urls": tried,
        "label": "BuildersMART",
    }


def scrape_indiamart(product: str) -> Dict[str, Any]:
    """Lightweight IndiaMART scraping via prioritized directory and search pages."""
    session = _build_session()

    def _candidates_india(prod: str) -> List[str]:
        slug = re.sub(r"[^a-z0-9]+", '-', prod.strip().lower()).strip('-')
        candidates = []
        candidates.append(f"https://dir.indiamart.com/impcat/{slug}.html")
        candidates.append(f"https://dir.indiamart.com/indianexporters/{slug}.html")
        candidates.append(f"https://dir.indiamart.com/search.mp?ss={prod.replace(' ', '+')}")
        candidates.append(f"https://dir.indiamart.com/search.mp?ss={slug}")
        seen = set()
        out = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    candidates = _candidates_india(product)
    last_exc = None
    tried: List[str] = []
    for candidate in candidates:
        try:
            r = session.get(candidate, timeout=10)
            r.raise_for_status()
            tried.append(candidate)
            soup = BeautifulSoup(r.text, 'html.parser')

            prices: List[int] = []
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    j = json.loads(script.string or '{}')
                    if isinstance(j, dict) and 'offers' in j and isinstance(j['offers'], dict):
                        off = j['offers']
                        if 'price' in off:
                            try:
                                prices.append(int(float(off['price'])))
                            except Exception:
                                pass
                except Exception:
                    pass

            if not prices:
                for tag in soup.find_all(['span', 'div', 'p']):
                    text = tag.get_text(separator=' ', strip=True)
                    if '₹' in text or 'Rs.' in text:
                        prices.extend(_extract_numbers(text))

            prices = _normalize_prices(prices)

            if len(prices) >= 3:
                arr = np.array(prices)
                return {
                    "status": "available",
                    "label": "IndiaMART",
                    "source_url": candidate,
                    "candidate_urls": tried,
                    "prices": prices,
                    "min": int(arr.min()),
                    "max": int(arr.max()),
                    "median": int(np.median(arr)),
                    "variance": float(np.var(arr) / (np.mean(arr) ** 2)) if np.mean(arr) else 0.0,
                    "unit": "INR",
                }

        except Exception as e:
            last_exc = e
            tried.append(candidate)
            continue

    reason = "Insufficient numeric price points found across IndiaMART candidates."
    if last_exc:
        reason = f"Scraping errors encountered; last: {str(last_exc)}"
    return {
        "status": "unavailable",
        "reason": reason,
        "source_url": candidates[0] if candidates else None,
        "candidate_urls": tried,
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
