#!/usr/bin/env python3
"""
Multi-domain data collection from OpenAlex and HackerNews APIs.
Reads keywords from SQLite DB (seeded from domains/*.yaml).
"""

import json
import requests
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from db import get_connection, get_keywords, get_active_domains

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def fetch_openalex(keywords: list[str], days_back: int = 30, per_keyword_limit: int = 10, domain_id: str = "") -> list[dict]:
    """Fetch recent papers from OpenAlex API for given keywords."""
    base_url = "https://api.openalex.org/works"
    since_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    results = []
    seen_ids = set()

    for kw in keywords:
        params = {
            "search": kw,
            "filter": f"from_publication_date:{since_date}",
            "sort": "cited_by_count:desc",
            "per_page": per_keyword_limit,
            "mailto": "yuyanishimura0312@gmail.com",
        }
        try:
            resp = requests.get(base_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            for work in data.get("results", []):
                wid = work.get("id", "")
                if wid in seen_ids:
                    continue
                seen_ids.add(wid)

                abstract = ""
                inv_abstract = work.get("abstract_inverted_index")
                if inv_abstract:
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
                    "domain": domain_id,
                })
        except Exception as e:
            print(f"    [WARNING] OpenAlex '{kw}': {e}", file=sys.stderr)
            continue
        time.sleep(0.2)  # Be polite to API

    return results


def fetch_hackernews(keywords: list[str], days_back: int = 30, per_keyword_limit: int = 10, domain_id: str = "") -> list[dict]:
    """Fetch recent posts from HackerNews Algolia API for given keywords."""
    base_url = "https://hn.algolia.com/api/v1/search"
    since_ts = int((datetime.now() - timedelta(days=days_back)).timestamp())
    results = []
    seen_ids = set()

    for kw in keywords:
        params = {
            "query": kw,
            "tags": "story",
            "numericFilters": f"created_at_i>{since_ts}",
            "hitsPerPage": per_keyword_limit,
        }
        try:
            resp = requests.get(base_url, params=params, timeout=30)
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
                    "abstract": "",
                    "url": hit.get("url", f"https://news.ycombinator.com/item?id={hid}"),
                    "publication_date": hit.get("created_at", ""),
                    "cited_by_count": hit.get("points", 0),
                    "source": "hackernews",
                    "source_type": "tech_media",
                    "query_keyword": kw,
                    "domain": domain_id,
                })
        except Exception as e:
            print(f"    [WARNING] HN '{kw}': {e}", file=sys.stderr)
            continue
        time.sleep(0.2)

    return results


def run(days_back: int = 30, domain_filter: list[str] = None) -> Path:
    """Run collection for all active domains (or filtered subset)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    domains = get_active_domains()
    if domain_filter:
        domains = [d for d in domains if d["slug"] in domain_filter]

    all_items = []
    domain_stats = {}

    for domain in domains:
        slug = domain["slug"]
        name = domain["name_ja"]
        print(f"\n  [{slug}] {name}")

        oa_keywords = get_keywords(slug, "openalex")
        hn_keywords = get_keywords(slug, "hackernews")

        oa_items = fetch_openalex(oa_keywords, days_back=days_back, domain_id=slug)
        hn_items = fetch_hackernews(hn_keywords, days_back=days_back, domain_id=slug)

        domain_total = len(oa_items) + len(hn_items)
        domain_stats[slug] = {"openalex": len(oa_items), "hackernews": len(hn_items), "total": domain_total}
        print(f"    OA: {len(oa_items)}, HN: {len(hn_items)}, Total: {domain_total}")

        all_items.extend(oa_items)
        all_items.extend(hn_items)

    # Deduplicate across domains (same article may appear in multiple domains)
    seen = set()
    unique_items = []
    for item in all_items:
        key = item["id"]
        if key not in seen:
            seen.add(key)
            unique_items.append(item)
        else:
            # Keep domain tag for duplicates (add to existing)
            for existing in unique_items:
                if existing["id"] == key and item.get("domain") not in existing.get("domains", [existing.get("domain", "")]):
                    if "domains" not in existing:
                        existing["domains"] = [existing.pop("domain", "")]
                    existing["domains"].append(item["domain"])
                    break

    today = datetime.now().strftime("%Y-%m-%d")
    output_path = DATA_DIR / f"{today}.json"

    output = {
        "collected_at": datetime.now().isoformat(),
        "days_back": days_back,
        "total_items": len(unique_items),
        "domain_stats": domain_stats,
        "items": unique_items,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n  Total unique: {len(unique_items)} items saved to {output_path}")
    return output_path


if __name__ == "__main__":
    run()
