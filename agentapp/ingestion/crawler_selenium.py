from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import time
import json
import os
import shutil

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except Exception:
    webdriver = None
try:
    from webdriver_manager.firefox import GeckoDriverManager
except Exception:
    GeckoDriverManager = None
try:
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
except Exception:
    EdgeChromiumDriverManager = None

try:
    from agentapp.ingestion.crawler import _score_match, MATERIAL_CLASSES, BUILDERMART_CLASSES
except Exception:
    # avoid hard dependency on bs4 when running standalone selenium dynamic crawl
    def _score_match(s, tokens):
        return 0

    MATERIAL_CLASSES = []
    BUILDERMART_CLASSES = []


def _is_static(u: str) -> bool:
    low = (u or '').lower()
    static_signs = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.css', '.woff', '.woff2', '.ttf', 'fontawesome', 'cdn-media', '/static/', '/assets/', '/media/']
    for s in static_signs:
        if s in low:
            return True
    return False


def get_driver(headless: bool = True, preferred: str = None):
    """Attempt to create a webdriver. Tries Chrome, then Edge, then Firefox (unless `preferred` set).

    Set `preferred` to 'chrome', 'edge', 'firefox' or 'brave' to force a browser.
    """
    if webdriver is None:
        raise RuntimeError('Selenium or webdriver-manager not installed.')

    pref = (preferred or os.environ.get('BROWSER') or 'auto').lower()
    order = []
    if pref == 'chrome':
        order = ['chrome']
    elif pref == 'edge':
        order = ['edge']
    elif pref == 'firefox':
        order = ['firefox']
    elif pref == 'brave':
        order = ['brave', 'chrome']
    else:
        order = ['chrome', 'edge', 'firefox']

    # helper to locate binaries
    def _locate_binary(names):
        for n in names:
            path = os.environ.get(n.upper() + '_BINARY') or shutil.which(n)
            if path:
                return path
        # windows common
        if os.name == 'nt':
            candidates = {
                'chrome': [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"],
                'brave': [r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"],
                'edge': [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
                'firefox': [r"C:\Program Files\Mozilla Firefox\firefox.exe"]
            }
            for n in names:
                for c in candidates.get(n, []):
                    if os.path.exists(c):
                        return c
        return None

    last_exc = None
    for b in order:
        try:
            if b in ('chrome', 'brave'):
                opts = Options()
                if headless:
                    opts.add_argument('--headless=new')
                opts.add_argument('--no-sandbox')
                opts.add_argument('--disable-dev-shm-usage')
                opts.add_argument('--disable-gpu')
                opts.add_argument('--window-size=1920,1080')

                bin_path = None
                if b == 'brave':
                    bin_path = _locate_binary(['brave', 'brave-browser'])
                else:
                    bin_path = _locate_binary(['chrome', 'chromium', 'chrome.exe'])

                if bin_path:
                    opts.binary_location = bin_path

                if ChromeDriverManager is None:
                    raise RuntimeError('webdriver-manager.chrome not available')
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=opts)
                return driver

            if b == 'edge':
                from selenium.webdriver.edge.options import Options as EdgeOptions
                from selenium.webdriver.edge.service import Service as EdgeService
                opts = EdgeOptions()
                if headless:
                    opts.add_argument('--headless=new')
                bin_path = _locate_binary(['msedge', 'edge'])
                if bin_path:
                    opts.binary_location = bin_path
                if EdgeChromiumDriverManager is None:
                    raise RuntimeError('webdriver-manager.microsoft not available')
                service = EdgeService(EdgeChromiumDriverManager().install())
                driver = webdriver.Edge(service=service, options=opts)
                return driver

            if b == 'firefox':
                from selenium.webdriver.firefox.options import Options as FirefoxOptions
                from selenium.webdriver.firefox.service import Service as FirefoxService
                if GeckoDriverManager is None:
                    raise RuntimeError('webdriver-manager.firefox not available')
                optsf = FirefoxOptions()
                if headless:
                    optsf.add_argument('-headless')
                bin_path = _locate_binary(['firefox'])
                if bin_path:
                    optsf.binary_location = bin_path
                service = FirefoxService(GeckoDriverManager().install())
                driver = webdriver.Firefox(service=service, options=optsf)
                return driver

        except Exception as e:
            last_exc = e
            continue

    # if we reach here, none succeeded
    if last_exc:
        raise last_exc
    raise RuntimeError('No supported browser driver found')


def find_best_link_for_material_selenium(material: str, site: str, driver, verify_with_visit: bool = False) -> Optional[str]:
    q = material.replace(' ', '+')
    if site == 'buildersmart':
        url = f"https://www.buildersmart.in/catalogsearch/result?q={q}"
    elif site == 'indiamart':
        url = f"https://dir.indiamart.com/search.mp?ss={q}"
    else:
        return None

    tokens = material.lower().split()
    best = (None, 0)

    try:
        driver.get(url)
        # wait for body or some results container
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        time.sleep(0.5)
        # gather anchors and elements with data-attrs
        elems = driver.find_elements(By.XPATH, "//a | //*[@onclick] | //*[@data-href] | //*[@data-url] | //*[@data-link]")
        candidates = []
        for el in elems:
            try:
                href = el.get_attribute('href') or el.get_attribute('data-href') or el.get_attribute('data-url') or el.get_attribute('data-link') or ''
                text = el.text or el.get_attribute('title') or el.get_attribute('aria-label') or ''
                if not href:
                    # attempt to get onclick URL
                    onclick = el.get_attribute('onclick')
                    if onclick and 'http' in onclick:
                        import re
                        m = re.search(r"(https?://[\w\-./?=&%]+)", onclick)
                        href = m.group(1) if m else ''

                if not href:
                    continue
                full = urljoin(url, href)
                if _is_static(full):
                    continue
                # skip product-detail like links (we want category/listing pages)
                product_indicators = ['proddetail', '/prdt/', '/product/', '/prod/', '/p/', '/item/', 'proddetail', 'catalog/product', 'ap-', '-kg-', '?pos=']
                low_full = full.lower()
                if any(ind in low_full for ind in product_indicators):
                    # deprioritize product detail links
                    continue
                p = urlparse(full)
                if site == 'buildersmart' and 'buildersmart.in' not in (p.netloc or ''):
                    continue
                if site == 'indiamart' and 'indiamart' not in (p.netloc or ''):
                    continue
                surrounding = text
                score = _score_match(text + ' ' + full + ' ' + surrounding, tokens)
                # additional boost if token found in path
                for tok in tokens:
                    if tok in (p.path or '').lower():
                        score += 3
                # keep candidate list for further analysis rather than immediately choosing
                candidates.append((full, score, text))
            except Exception:
                continue

        # prefer category-like URLs: boost when path contains category keywords
        category_tokens = ['catalogsearch', 'catalog', 'category', 'products', 'product', 'buy', 'shop', 'list', 'tmt-steel', 'cement', 'bricks', 'plumbing', 'electrical', 'bricks-blocks', 'bricks-and-blocks', 'bricks-blocks-price']
        # sort candidates by initial score desc
        candidates = sorted(candidates, key=lambda x: x[1], reverse=True)

        # visit top candidates to detect product listing pages (which contain many product cards)
        max_visit = 5
        visits = 0
        for full, score, text in candidates:
            if visits >= max_visit:
                break
            try:
                p = urlparse(full)
                path = (p.path or '')
                # quick path-based boost
                path_boost = 0
                for tok in category_tokens:
                    if tok in full.lower() or tok in path.lower() or tok in (text or '').lower():
                        path_boost += 4

                score = score + path_boost

                # if score now promising, optionally visit the link and check for product card counts
                if score >= 3 and verify_with_visit:
                    try:
                        driver.get(full)
                        WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                        time.sleep(0.5)
                        # heuristics for product cards
                        prod_selectors = [
                            "//*[contains(@class,'product')]",
                            "//*[contains(@class,'product-item')]",
                            "//*[contains(@class,'product-list')]",
                            "//*[contains(@class,'search-result')]",
                            "//*[contains(@class,'listing')]",
                            "//ul[contains(@class,'products')]/li",
                            "//div[contains(@class,'prod')]",
                        ]
                        count = 0
                        for sel in prod_selectors:
                            els = driver.find_elements(By.XPATH, sel)
                            if els:
                                count = max(count, len(els))

                        # if multiple product cards found, strongly prefer this link
                        if count >= 3:
                            # boost by product count * 5
                            score += count * 5
                            best = (full, score)
                            # prefer first good category found
                            return best[0]

                        # otherwise, still consider score
                        if score > best[1]:
                            best = (full, score)

                    except Exception:
                        # on failure to visit, still consider path-based score
                        if score > best[1]:
                            best = (full, score)
                    visits += 1
                else:
                    # not visiting; rely on path/text scoring
                    if score > best[1]:
                        best = (full, score)
            except Exception:
                continue

        # if no visited candidate returned, pick the best-scoring candidate
        if best[0]:
            return best[0]

        # as fallback, try to parse page source for obvious category URL patterns
        src = driver.page_source
        import re
        for m in re.findall(r"https?://[\w\-./?=&%]+", src):
            if _is_static(m):
                continue
            if site == 'buildersmart' and 'buildersmart.in' not in m:
                continue
            if site == 'indiamart' and 'indiamart' not in m:
                continue
            score = _score_match(m, tokens)
            if score > best[1]:
                best = (m, score)

    except Exception:
        return None

    return best[0]


def crawl_material_links_selenium(materials: List[str], sites: List[str] = None, headless: bool = True) -> Dict[str, Dict[str, Optional[str]]]:
    if sites is None:
        sites = ['buildersmart', 'indiamart']
    driver = get_driver(headless=headless)
    out = {}
    try:
        for m in materials:
            out[m] = {}
            for s in sites:
                out[m][s] = find_best_link_for_material_selenium(m, s, driver, verify_with_visit=True)
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return out


def crawl_material_links_deep(materials: List[str], sites: List[str] = None, headless: bool = True,
                             max_pages_per_material: int = 40, max_depth: int = 2, max_results: int = 20) -> Dict[str, Dict[str, List[str]]]:
    """Deep BFS crawl per material+site. Returns multiple candidate category/listing links per material and site.

    - max_pages_per_material: how many pages to visit per material per site
    - max_depth: link-follow depth from initial search page
    - max_results: maximum number of links returned per material/site
    """
    if sites is None:
        sites = ['buildersmart', 'indiamart']

    driver = get_driver(headless=headless)
    out: Dict[str, Dict[str, List[str]]] = {}

    # selectors and heuristics
    prod_selectors = [
        "//*[contains(@class,'product')]",
        "//*[contains(@class,'product-item')]",
        "//*[contains(@class,'product-list')]",
        "//*[contains(@class,'search-result')]",
        "//*[contains(@class,'listing')]",
        "//ul[contains(@class,'products')]/li",
        "//div[contains(@class,'prod')]",
    ]
    product_indicators = ['proddetail', '/prdt/', '/product/', '/prod/', '/p/', '/item/', 'catalog/product', 'ap-', '-kg-', '?pos=']
    category_tokens = ['catalogsearch', 'catalog', 'category', 'products', 'buy', 'shop', 'list', 'tmt-steel', 'cement', 'bricks', 'plumbing', 'electrical', 'impcat']

    try:
        for material in materials:
            tokens = [t.lower() for t in material.split()]
            out[material] = {}
            for site in sites:
                # initial search URL
                q = material.replace(' ', '+')
                if site == 'buildersmart':
                    start_url = f"https://www.buildersmart.in/catalogsearch/result?q={q}"
                elif site == 'indiamart':
                    start_url = f"https://dir.indiamart.com/search.mp?ss={q}"
                else:
                    out[material][site] = []
                    continue

                visited = set()
                queue = [(start_url, 0)]
                candidates: Dict[str, float] = {}
                pages_visited = 0

                base_netloc = urlparse(start_url).netloc

                while queue and pages_visited < max_pages_per_material:
                    url, depth = queue.pop(0)
                    if url in visited:
                        continue
                    try:
                        driver.get(url)
                        WebDriverWait(driver, 6).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                        time.sleep(0.4)
                        visited.add(url)
                        pages_visited += 1

                        # compute product-like element count
                        prod_count = 0
                        for sel in prod_selectors:
                            try:
                                els = driver.find_elements(By.XPATH, sel)
                                if els:
                                    prod_count = max(prod_count, len(els))
                            except Exception:
                                continue

                        # scoring: product count, path tokens, text match
                        path = urlparse(url).path.lower()
                        score = prod_count * 5
                        for tok in category_tokens:
                            if tok in url.lower() or tok in path:
                                score += 3
                        page_text = (driver.find_element(By.TAG_NAME, 'body').text or '').lower()
                        for t in tokens:
                            if t in page_text:
                                score += 1

                        # if page looks like a listing/category, add to candidates
                        if prod_count >= 2 or any(tok in url.lower() for tok in category_tokens) or score >= 3:
                            candidates[url] = max(candidates.get(url, 0), score)

                        # extract links for BFS if depth allows
                        if depth < max_depth:
                            elems = driver.find_elements(By.XPATH, "//a | //*[@onclick] | //*[@data-href] | //*[@data-url] | //*[@data-link]")
                            for el in elems:
                                try:
                                    href = el.get_attribute('href') or el.get_attribute('data-href') or el.get_attribute('data-url') or el.get_attribute('data-link') or ''
                                    if not href:
                                        onclick = el.get_attribute('onclick')
                                        if onclick and 'http' in onclick:
                                            import re
                                            m = re.search(r"(https?://[\w\-./?=&%]+)", onclick)
                                            href = m.group(1) if m else ''
                                    if not href:
                                        continue
                                    full = urljoin(url, href)
                                    if _is_static(full):
                                        continue
                                    if urlparse(full).netloc != base_netloc:
                                        continue
                                    low_full = full.lower()
                                    if any(ind in low_full for ind in product_indicators):
                                        # still follow if path contains category tokens
                                        if not any(tok in low_full for tok in category_tokens):
                                            continue
                                    if full not in visited:
                                        queue.append((full, depth + 1))
                                except Exception:
                                    continue
                    except Exception:
                        continue

                # sort candidates by score and return top-k
                sorted_cands = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
                final = [u for u, s in sorted_cands[:max_results]]
                out[material][site] = final

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return out


def dynamic_crawl_seeds(seeds: List[str], headless: bool = True, verify_with_visit: bool = True, max_links_per_seed: int = 20) -> Dict[str, List[str]]:
    """Given a list of seed URLs, render each and extract candidate category/listing links from the same domain.

    Returns a mapping from seed -> list of discovered links (filtered, deduped).
    """
    driver = get_driver(headless=headless)
    out: Dict[str, List[str]] = {}
    product_indicators = ['proddetail', '/prdt/', '/product/', '/prod/', '/p/', '/item/', 'catalog/product', 'ap-', '-kg-', '?pos=']
    category_tokens = ['catalogsearch', 'catalog', 'category', 'products', 'buy', 'shop', 'list', 'tmt-steel', 'cement', 'bricks', 'plumbing', 'electrical']
    prod_selectors = [
        "//*[contains(@class,'product')]",
        "//*[contains(@class,'product-item')]",
        "//*[contains(@class,'product-list')]",
        "//*[contains(@class,'search-result')]",
        "//*[contains(@class,'listing')]",
        "//ul[contains(@class,'products')]/li",
        "//div[contains(@class,'prod')]",
    ]

    try:
        for seed in seeds:
            found = []
            try:
                driver.get(seed)
                WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                time.sleep(0.5)
                base_netloc = urlparse(seed).netloc

                elems = driver.find_elements(By.XPATH, "//a | //*[@onclick] | //*[@data-href] | //*[@data-url] | //*[@data-link]")
                candidates = []
                for el in elems:
                    try:
                        href = el.get_attribute('href') or el.get_attribute('data-href') or el.get_attribute('data-url') or el.get_attribute('data-link') or ''
                        text = el.text or el.get_attribute('title') or el.get_attribute('aria-label') or ''
                        if not href:
                            onclick = el.get_attribute('onclick')
                            if onclick and 'http' in onclick:
                                import re
                                m = re.search(r"(https?://[\w\-./?=&%]+)", onclick)
                                href = m.group(1) if m else ''

                        if not href:
                            continue
                        full = urljoin(seed, href)
                        if _is_static(full):
                            continue
                        if urlparse(full).netloc != base_netloc:
                            continue
                        low_full = full.lower()
                        if any(ind in low_full for ind in product_indicators):
                            continue
                        # basic scoring: prefer links with category tokens or the seed tokens
                        score = 0
                        for tok in category_tokens:
                            if tok in low_full:
                                score += 4
                        if tok := urlparse(seed).path.strip('/'):
                            if tok and tok in low_full:
                                score += 2
                        candidates.append((full, score, text))
                    except Exception:
                        continue

                # sort and optionally visit to confirm listing pages
                candidates = sorted({c[0]: c for c in candidates}.values(), key=lambda x: x[1], reverse=True)
                final = []
                for full, score, text in candidates:
                    if len(final) >= max_links_per_seed:
                        break
                    try:
                        if verify_with_visit:
                            try:
                                driver.get(full)
                                WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
                                time.sleep(0.5)
                                # count product-like elements
                                count = 0
                                for sel in prod_selectors:
                                    els = driver.find_elements(By.XPATH, sel)
                                    if els:
                                        count = max(count, len(els))
                                if count >= 2:
                                    final.append(full)
                                else:
                                    # if path/token score is high, still keep
                                    if score >= 4:
                                        final.append(full)
                            except Exception:
                                if score >= 4:
                                    final.append(full)
                        else:
                            final.append(full)
                    except Exception:
                        continue

                # dedupe while preserving order
                seen = set()
                deduped = []
                for u in final:
                    if u not in seen:
                        seen.add(u)
                        deduped.append(u)

                out[seed] = deduped
            except Exception:
                out[seed] = []
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return out


if __name__ == '__main__':
    combined = []
    for lst in (MATERIAL_CLASSES, BUILDERMART_CLASSES):
        for item in lst:
            if item not in combined:
                combined.append(item)

    links = crawl_material_links_selenium(combined[:40], headless=True)
    import os
    os.makedirs('data', exist_ok=True)
    with open('data/material_links_selenium.json', 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)
    print('Saved data/material_links_selenium.json')
