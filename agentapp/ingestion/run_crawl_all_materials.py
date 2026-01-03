from agentapp.ingestion.crawler_selenium import crawl_material_links_deep
import json
import os


MATERIALS = [
    "Stainless Steel bars & rods, including flats",
    "Ordinary Portland cement",
    "slag cement",
    "Pozzolana cement",
    "Steel structures",
    "e. Manufacture of cement, lime and plaster",
    "c. Mild Steel - Semi Finished Steel",
    "d. Mild Steel -Long Products",
    "e. Mild Steel - Flat products",
    "Mild Steel (MS) Blooms",
    "White cement",
    "Cement superfine",
    "f. Manufacture of articles of concrete, cement...",
    "Cement blocks (concrete)",
    "Angles, Channels, Sections, steel (coated/not)",
    "Mild steel (MS) flats & sheets",
]

if __name__ == '__main__':
    print('Running Selenium crawler for materials (count={}):'.format(len(MATERIALS)))
    for m in MATERIALS:
        print(' -', m)

    results = crawl_material_links_deep(MATERIALS, headless=True, max_pages_per_material=40, max_depth=2, max_results=25)

    os.makedirs('data', exist_ok=True)
    out_file = 'data/material_links_all_materials_deep.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # show basic summary counts
    total = 0
    nulls = 0
    for m, d in results.items():
        for k, v in d.items():
            total += 1
            if not v:
                nulls += 1

    print(f'Saved {out_file} — total entries: {total}, nulls: {nulls}')
