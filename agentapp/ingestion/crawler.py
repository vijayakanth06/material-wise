import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse


def _extract_numbers(text: str) -> List[int]:
    s = text.replace(',', '').replace('\u20b9', '')
    nums = re.findall(r"\d{2,7}", s)
    return [int(n) for n in nums]


def _score_match(text: str, material_tokens: List[str]) -> int:
    t = text.lower()
    score = 0
    for tok in material_tokens:
        if tok in t:
            score += 2
    # bonus for exact phrase
    if ' '.join(material_tokens) in t:
        score += 5
    return score


def find_best_link_for_material(material: str, site: str = 'buildersmart') -> Optional[str]:
    """Search the target site and return the best-matching link (absolute URL) for the material.

    This is a lightweight crawler that prefers anchor text matches and clean hrefs.
    """
    q = material.replace(' ', '+')
    if site == 'buildersmart':
        search_urls = [
            f"https://www.buildersmart.in/catalogsearch/result?q={q}",
            f"https://www.buildersmart.in/search?q={q}",
        ]
    elif site == 'indiamart':
        search_urls = [f"https://dir.indiamart.com/search.mp?ss={q}"]
    else:
        return None

    tokens = material.lower().split()
    best = (None, 0)  # (url, score)

    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-IN,en;q=0.9"}

    def _extract_url_from_onclick(onclick: str) -> Optional[str]:
        # try common patterns like location.href='...'; window.location='...'; window.open('...')
        if not onclick:
            return None
        # find quoted URL
        m = re.search(r"(?:location\.href|window\.location|window\.open)\(['\"](https?:\\/\\/[^'\"]+)['\"]", onclick)
        if m:
            return m.group(1)
        # find any quoted http(s) inside onclick
        m2 = re.search(r"['\"](https?://[^'\"]+)['\"]", onclick)
        if m2:
            return m2.group(1)
        return None

    def _find_urls_in_scripts(soup, domain_hint=None):
            urls = set()
            for script in soup.find_all('script'):
                txt = script.string
                if not txt:
                    # sometimes script has children or is empty
                    continue
                # raw URLs
                for m in re.findall(r"https?://[a-zA-Z0-9./?=_-]+", txt):
                    if domain_hint and domain_hint not in m:
                        continue
                    urls.add(m)

                # attempt to parse JSON blobs to find url/href fields
                try:
                    import json as _json
                    # find JSON-like blocks
                    for jtxt in re.findall(r"\{[\s\S]{10,5000}?\}", txt):
                        try:
                            obj = _json.loads(jtxt)
                        except Exception:
                            continue
                        # recursive search for url-like fields
                        def _walk(o):
                            if isinstance(o, dict):
                                for k, v in o.items():
                                    if isinstance(v, str) and v.startswith('http'):
                                        if (not domain_hint) or domain_hint in v:
                                            urls.add(v)
                                    else:
                                        _walk(v)
                            elif isinstance(o, list):
                                for it in o:
                                    _walk(it)
                        _walk(obj)
                except Exception:
                    pass

            return list(urls)

    for url in search_urls:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')

            # domain hint to filter script URLs
            domain_hint = None
            if 'buildersmart' in url:
                domain_hint = 'buildersmart.in'
            if 'indiamart' in url:
                domain_hint = 'indiamart.com'

            # collect candidates from anchors, data-/onclick attributes, and aria/title attributes
            for tag in soup.find_all(True):
                # prefer anchor hrefs
                cand = None
                text = (tag.get_text(separator=' ', strip=True) or '')
                # common data attributes
                for attr in ('href', 'data-href', 'data-url', 'data-link', 'data-target', 'data-redirect'):
                    val = tag.get(attr)
                    if val:
                        cand = val
                        break

                # onclick handlers may contain URLs
                if not cand and tag.get('onclick'):
                    c = _extract_url_from_onclick(tag.get('onclick'))
                    if c:
                        cand = c

                # sometimes aria-label/title contain clearer category names and link is on parent
                if not cand:
                    for attr in ('data-category', 'data-cat', 'title', 'aria-label'):
                        v = tag.get(attr)
                        if v and any(tok in v.lower() for tok in tokens):
                            # look for nearest anchor
                            parent_a = tag.find_parent('a')
                            if parent_a and parent_a.get('href'):
                                cand = parent_a.get('href')
                                break

                if cand:
                    # ignore fragments and javascript pseudo-links
                    if cand.startswith('javascript:') or cand.startswith('#'):
                        continue
                    full = urljoin(url, cand)
                    # reject static assets and CDN resources
                    def _is_static(u: str) -> bool:
                        low = u.lower()
                        static_signs = ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.css', '.woff', '.woff2', '.ttf', 'fontawesome', 'cdn-media', '/static/', '/assets/', '/media/']
                        for s in static_signs:
                            if s in low:
                                return True
                        return False

                    if _is_static(full):
                        continue

                    # domain hint enforcement
                    try:
                        p = urlparse(full)
                    except Exception:
                        p = None

                    if domain_hint and p and domain_hint not in (p.netloc or '') and domain_hint not in full:
                        # if candidate is not on-site, deprioritize
                        continue

                    surrounding = ''
                    # include parent text as context
                    if tag.parent:
                        surrounding = tag.parent.get_text(separator=' ', strip=True)

                    # boost score if path contains tokens
                    path = (p.path if p else '') if p else ''
                    path_score = 0
                    for tok in tokens:
                        if tok in path.lower():
                            path_score += 3

                    score = _score_match(text + ' ' + full + ' ' + surrounding, tokens) + path_score
                    if score > best[1]:
                        best = (full, score)

            # also parse inline scripts for possible category JSON/url
            for script_url in _find_urls_in_scripts(soup, domain_hint=domain_hint):
                full = script_url
                # use the script url string as context
                score = _score_match(full, tokens)
                if score > best[1]:
                    best = (full, score)

        except Exception:
            continue

    return best[0]


def crawl_material_links(materials: List[str], sites: List[str] = None) -> Dict[str, Dict[str, Optional[str]]]:
    if sites is None:
        sites = ['buildersmart', 'indiamart']

    result = {}
    for m in materials:
        result[m] = {}
        for s in sites:
            result[m][s] = find_best_link_for_material(m, site=s)
    return result


if __name__ == '__main__':
    # example runner using the user's classes
    sample = [
        'Stainless Steel bars & rods, including flats',
        'Ordinary Portland cement',
        'slag cement',
        'Pozzolana cement',
        'Steel structures',
        'Mild Steel - Semi Finished Steel'
    ]
    links = crawl_material_links(sample)
    import json
    print(json.dumps(links, indent=2))


# canonical material classes (from MOSPI-like list); used as default crawl targets
MATERIAL_CLASSES = [
    'Stainless Steel bars & rods, including flats',
    'Ordinary Portland cement',
    'slag cement',
    'Pozzolana cement',
    'Steel structures',
    'Manufacture of cement, lime and plaster',
    'Mild Steel - Semi Finished Steel',
    'Mild Steel - Long Products',
    'Mild Steel - Flat products',
    'Mild Steel (MS) Blooms',
    'White cement',
    'Cement superfine',
    'Manufacture of articles of concrete, cement',
    'Cement blocks (concrete)',
    'Angles, Channels, Sections, steel',
    'Mild steel (MS) flats & sheets'
]


BUILDERMART_CLASSES = [
    'Cement',
    'OPC-53 Grade Cement',
    'PPC Cement',
    'Sand & Aggregates',
    'TMT Steel Bars',
    'Fe-500 Grade TMT Bars',
    'Fe-550 Grade TMT Bars',
    'TMT Binding Wire',
    'Rebar Couplers',
    'Bricks & Blocks',
    'Concrete Solid Blocks',
    'Flyash Bricks',
    'Autoclaved Aerated Concrete (AAC) Blocks',
    'Red Bricks',
    'Electrical',
    'Conduit Pipes and Fittings',
    'Wires and Cables',
    'Modular Switches and Sockets',
    'Electric Panels',
    'Switch Gear',
    'Plumbing',
    'CPVC Pipes and Fittings',
    'UPVC Pipes and Fittings',
    'SWR Pipes and Fittings',
    'Wooden Products',
    'Plywood',
    'Block Boards',
    'Decorative Laminates',
    'Veneers',
    'Tiles',
    'Floor Tiles',
    'Wall Tiles',
    'Parking Tiles',
    'Vitrified Tiles',
    'Bathroom Accessories',
    'Faucets',
    'Showers',
    'Sanitaryware',
    'Hardware Fixtures',
    'Luxury Handles',
    'Premium Handles',
    'Stainless Steel Handles',
    'Stainless Steel Pull Handles',
    'Mortise Locks',
    'Latches and Hinges',
    'Drawer and Cabinet Hardware',
    'Euro Profile Cylinders',
    'Paints & Finishes',
    'Wall Care Putty',
    'Decorative Paint Coating',
    'Texture & Wall Care Finishes',
    'Lighting & Fixtures',
    'Indoor Luminaires',
    'Office Lighting',
    'Outdoor Luminaires',
    'Roadway LED Lighting',
    'Lighting Electronics and Controls',
    'Natural Stones',
    'Granites',
    'Marbles',
    'RMC (Ready Mix Concrete)',
    'Roofing Solutions',
    'UPVC Doors & Windows',
    'UPVC Doors',
    'UPVC Windows',
    'Home Automation',
    'Home Decor',
    'Modular Kitchen',
    'RO System Accessories',
    'Construction Chemicals',
    'Adhesive',
    'Dry Mix',
    'Solvents',
    'Glass Hardware',
    'Mirrors'
]


def save_links(links: Dict[str, Dict[str, Optional[str]]], path: str) -> None:
    import json
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)


def crawl_and_store(materials: List[str] = None, out_path: str = 'data/material_links.json') -> Dict[str, Dict[str, Optional[str]]]:
    if materials is None:
        # combine canonical MOSPI-like classes and BuilderMART categories
        combined = []
        for lst in (MATERIAL_CLASSES, BUILDERMART_CLASSES):
            for item in lst:
                if item not in combined:
                    combined.append(item)
        materials = combined
    links = crawl_material_links(materials)
    # ensure output directory exists
    import os
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    save_links(links, out_path)
    return links
