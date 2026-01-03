import json
import os
import re
from urllib.parse import urlparse
import requests


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


def check_status(url, session, timeout=6):
    try:
        resp = session.head(url, allow_redirects=True, timeout=timeout)
        if resp.status_code == 405 or resp.status_code == 403:
            # some servers block HEAD or return 403 for HEAD; try GET for a better check
            resp = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
        return resp.status_code
    except requests.RequestException:
        return None


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def main():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.json')]
    combined = set()
    report = {}

    session = requests.Session()
    session.headers.update({'User-Agent': 'material-wise-cleaner/1.0'})

    for fn in files:
        path = os.path.join(DATA_DIR, fn)
        data = load_json(path)
        urls = extract_urls(data)

        # filter schemes and images and non-useful schemes
        filtered = set()
        removed_reasons = { 'non_http':0, 'image':0 }
        for u in urls:
            if not is_http_url(u):
                removed_reasons['non_http'] += 1
                continue
            if is_image_url(u):
                removed_reasons['image'] += 1
                continue
            filtered.add(u)

        # dedupe and check status codes
        good = []
        bad = []
        for u in sorted(filtered):
            status = check_status(u, session)
            if status is None:
                bad.append((u, 'no-response'))
            elif status >= 400:
                bad.append((u, status))
            else:
                good.append(u)

        combined.update(good)

        cleaned_name = f'cleaned_{fn}'
        save_json(os.path.join(DATA_DIR, cleaned_name), good)

        report[fn] = {
            'original_count': len(urls),
            'after_scheme_and_image_filter': len(filtered),
            'kept': len(good),
            'removed_non_http_or_image': removed_reasons,
            'removed_bad_status_count': len(bad),
            'bad_examples': bad[:10]
        }

    # save combined
    combined_list = sorted(combined)
    save_json(os.path.join(DATA_DIR, 'cleaned_combined_links.json'), combined_list)
    save_json(os.path.join(DATA_DIR, 'cleaning_report.json'), report)

    print('Cleaning finished')
    print('Files processed:', len(files))
    total_original = sum(r['original_count'] for r in report.values())
    total_kept = len(combined_list)
    print(f'Total original URLs: {total_original}')
    print(f'Total unique URLs kept: {total_kept}')


if __name__ == '__main__':
    main()
