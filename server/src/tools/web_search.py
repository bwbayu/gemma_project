"""Google Custom Search restricted to a domain whitelist; full-page content fetched via Jina AI."""

import os
import urllib.parse

import requests
from dotenv import load_dotenv

load_dotenv()

WHITELIST_DOMAIN = [
    "phys.libretexts.org",
    "openstax.org",
    # "physicsclassroom.com",
]

def _norm_host(url: str) -> str:
    """Extract and normalize the hostname from a URL, stripping the www. prefix."""
    host = (urllib.parse.urlparse(url).netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def google_search(query: str, limit: int = 2) -> dict:
    """Search each whitelisted domain via Google CSE, then fetch full page content through Jina AI."""
    # check cse key and cx
    cse_key = os.getenv("GOOGLE_CSE_API_KEY", "")
    cse_cx = os.getenv("GOOGLE_CSE_CX", "")
    if not cse_key or not cse_cx:
        return {
            "status": "error",
            "provider": "google_cse",
            "error": "Missing GOOGLE_CSE_API_KEY or GOOGLE_CSE_CX",
            "results": [],
            "visited_hosts": ["customsearch.googleapis.com"],
        }

    # normalize limit to safe bounds
    if limit < 1:
        limit = 1
    if limit > 10:
        limit = 10

    # iterate through whitelist domains and collect search items
    all_results = []
    errors = []

    for domain in WHITELIST_DOMAIN:
        try:
            search_query = f"site:{domain} {query}"
            search_result = requests.get(
                "https://www.googleapis.com/customsearch/v1",
                params={
                    "key": cse_key,
                    "cx": cse_cx,
                    "q": search_query,
                    "num": min(limit, 5),
                },
                timeout=10,
            )

            # raise status for error handling
            search_result.raise_for_status()
            # get the items
            items = search_result.json().get("items", [])
            # append to all_results
            all_results.extend(items)
        except requests.HTTPError as exc:
            errors.append({
                "stage": "search",
                "domain": domain,
                "error": f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            })
        except Exception as e:
            errors.append({
                "stage": "search",
                "domain": domain,
                "error": f"Search failed: {str(e)}"
            })

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # extract full context from each link of items
    combined_results = []
    seen_links = set()
    for item in all_results:
        link = item.get("link", "")
        if not link or link in seen_links:
            continue
        seen_links.add(link)

        jina_url = f"https://r.jina.ai/{link}"
        fetch_error = None

        try:
            fetch_res = requests.get(jina_url, headers=headers, timeout=15)
            fetch_res.raise_for_status()
            content = fetch_res.text
        except requests.exceptions.RequestException as e:
            content = ""
            fetch_error = f"Error fetching content: {str(e)}"
            errors.append({
                "stage": "fetch",
                "url": link,
                "error": fetch_error,
            })

        combined_results.append({
            "title": item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link": link,
            "source_domain": _norm_host(link),
            "full_content": content,
            "fetch_error": fetch_error,
        })

    if combined_results and errors:
        status = "partial_error"
    elif combined_results:
        status = "success"
    else:
        status = "error"

    return {
        "status": status,
        "provider": "google_cse",
        "query": query,
        "results": combined_results,
        "errors": errors,
        "meta": {
            "limit_requested": limit,
            "results_count": len(combined_results),
            "queried_whitelist_domains": WHITELIST_DOMAIN,
            "visited_hosts": ["customsearch.googleapis.com", "r.jina.ai"],
        },
    }

# print(google_search("thermodynamics"))