from agentapp.ingestion.crawler import crawl_and_store


if __name__ == '__main__':
    # run crawler and store results to data/material_links.json
    links = crawl_and_store()
    import json
    print(json.dumps(links, indent=2))
