#!/usr/bin/env python3
"""
Data collection from OpenAlex and HackerNews APIs.
Fetches energy technology related articles and papers from the past 30 days.
"""

import json
import requests
import sys
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

# Energy technology keywords for querying
ENERGY_KEYWORDS = [
    "energy transition",
    "battery storage",
    "solar cell",
    "carbon capture",
    "green hydrogen",
    "perovskite solar",
    "flow battery",
    "nuclear fusion",
    "wind energy",
    "grid storage",
    "electrolysis",
    "solid state battery",
    "energy harvesting",
    "supercapacitor",
    "geothermal energy",
]

HN_KEYWORDS = [
    "solar", "battery", "energy", "hydrogen", "fusion",
    "carbon capture", "wind power", "grid", "EV charging",
    "perovskite", "electrolysis", "geothermal",
]


def fetch_openalex(days_back: int = 30, per_keyword_limit: int = 10) -> list[dict]:
    """Fetch recent energy tech papers from OpenAlex API (free, no auth)."""
    base_url = "https://api.openalex.org/works"
    since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    results = []
    seen_ids = set()

    for kw in ENERGY_KEYWORDS:
        params = {
            "search": kw,
            "filter": f"from_publication_date:{since_date}",
            "sort": "cited_by_count:desc",
            "per_page": per_keyword_limit,
            "mailto": "yuyanishimura0312@gmail.com",  # polite pool
        }
        try:
            resp = requests.get(base_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for work in data.get("results", []):
                wid = work.get("id", "")
                if wid in seen_ids:
                    continue
                seen_ids.add(wid)

                # Extract abstract from inverted index if available
                abstract = ""
                inv_abstract = work.get("abstract_inverted_index")
                if inv_abstract:
                    # Reconstruct abstract from inverted index
                    word_positions = []
                    for word, positions in inv_abstract.items():
                        for pos in positions:
                            word_positions.append((pos, word))
                    word_positions.sort()
                    abstract = " ".join(w for _, w in word_positions)

                results.append({
                    "id": wid,
                    "title": work.get("title", ""),
                    "abstract": abstract[:500] if abstract else "",
                    "url": work.get("doi", "") or work.get("id", ""),
                    "publication_date": work.get("publication_date", ""),
                    "cited_by_count": work.get("cited_by_count", 0),
                    "source": "openalex",
                    "source_type": "academic",
                    "query_keyword": kw,
                })
        except Exception as e:
            print(f"  [WARNING] OpenAlex query '{kw}' failed: {e}", file=sys.stderr)
            continue

    print(f"  OpenAlex: {len(results)} papers collected")
    return results


def fetch_hackernews(days_back: int = 30, per_keyword_limit: int = 10) -> list[dict]:
    """Fetch recent energy tech posts from HackerNews Algolia API (free, no auth)."""
    base_url = "https://hn.algolia.com/api/v1/search"
    since_ts = int((datetime.now() - timedelta(days=days_back)).timestamp())
    results = []
    seen_ids = set()

    for kw in HN_KEYWORDS:
        params = {
            "query": kw,
            "tags": "story",
            "numericFilters": f"created_at_i>{since_ts}",
            "hitsPerPage": per_keyword_limit,
        }
        try:
            resp = requests.get(base_url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for hit in data.get("hits", []):
                hid = hit.get("objectID", "")
                if hid in seen_ids:
                    continue
                seen_ids.add(hid)

                results.append({
                    "id": f"hn-{hid}",
                    "title": hit.get("title", ""),
                    "abstract": "",  # HN stories don't have abstracts
                    "url": hit.get("url", f"https://news.ycombinator.com/item?id={hid}"),
                    "publication_date": hit.get("created_at", ""),
                    "cited_by_count": hit.get("points", 0),
                    "source": "hackernews",
                    "source_type": "tech_media",
                    "query_keyword": kw,
                })
        except Exception as e:
            print(f"  [WARNING] HackerNews query '{kw}' failed: {e}", file=sys.stderr)
            continue

    print(f"  HackerNews: {len(results)} posts collected")
    return results


def run(days_back: int = 30) -> Path:
    """Run collection and save results."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Collecting data...")
    openalex_data = fetch_openalex(days_back=days_back)
    hn_data = fetch_hackernews(days_back=days_back)

    all_items = openalex_data + hn_data
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = DATA_DIR / f"{today}.json"

    output = {
        "collected_at": datetime.now().isoformat(),
        "days_back": days_back,
        "total_items": len(all_items),
        "sources": {
            "openalex": len(openalex_data),
            "hackernews": len(hn_data),
        },
        "items": all_items,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  Total: {len(all_items)} items saved to {output_path}")
    return output_path


if __name__ == "__main__":
    run()
