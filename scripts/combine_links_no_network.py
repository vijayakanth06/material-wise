import json
import os
import re
from urllib.parse import urlparse


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(ROOT, 'data')

IMAGE_EXT_RE = re.compile(r"\.(jpg|jpeg|png|gif|svg|webp|bmp|ico|tif|tiff)$", re.I)


def extract_urls(obj):
    urls = set()
    if obj is None:
        return urls
    if isinstance(obj, str):
        s = obj.strip()
        if s and s.lower() != 'null':
            urls.add(s)
        return urls
    if isinstance(obj, list):
        for v in obj:
            urls.update(extract_urls(v))
        return urls
    if isinstance(obj, dict):
        for v in obj.values():
            urls.update(extract_urls(v))
        return urls
    return urls


def is_image_url(url):
    path = urlparse(url).path
    return bool(IMAGE_EXT_RE.search(path))


def is_http_url(url):
    p = urlparse(url)
    return p.scheme in ('http', 'https')


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def main():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    combined = set()
    per_file_counts = {}

    for fn in files:
        path = os.path.join(DATA_DIR, fn)
        try:
            data = load_json(path)
        except Exception:
            continue
        urls = extract_urls(data)
        filtered = set(u for u in urls if is_http_url(u) and not is_image_url(u))
        combined.update(filtered)
        per_file_counts[fn] = {
            'original': len(urls),
            'kept': len(filtered)
        }

    combined_list = sorted(combined)
    out_path = os.path.join(DATA_DIR, 'combined_links.json')
    save_json(out_path, combined_list)

    # delete original json files except the newly created combined file
    for fn in files:
        p = os.path.join(DATA_DIR, fn)
        if os.path.abspath(p) == os.path.abspath(out_path):
            continue
        try:
            os.remove(p)
        except Exception:
            pass

    report = {
        'per_file_counts': per_file_counts,
        'total_unique_kept': len(combined_list)
    }
    save_json(os.path.join(DATA_DIR, 'combine_report.json'), report)

    print('Combined', len(files), 'files ->', out_path)


if __name__ == '__main__':
    main()
