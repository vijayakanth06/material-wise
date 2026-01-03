from agentapp.ingestion.crawler_selenium import dynamic_crawl_seeds
import json
import os


if __name__ == '__main__':
    # sample seeds provided by user
    seeds = [
        'https://dir.indiamart.com/impcat/slag-cement.html',
        'https://www.buildersmart.in/buy-cement-online/ppc',
        'https://www.buildersmart.in/plumbing-html/cpvc-pipes-and-fittings'
    ]

    print('Starting dynamic Selenium crawl for seeds:')
    for s in seeds:
        print(' -', s)

    links = dynamic_crawl_seeds(seeds, headless=True, verify_with_visit=True, max_links_per_seed=30)

    os.makedirs('data', exist_ok=True)
    out_file = 'data/material_links_dynamic.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

    print('Saved', out_file)
