#!/usr/bin/env python3
"""Test Wikipedia API directly for Zelkova serrata"""

import requests
import re

search_title = "Zelkova serrata"
url = "https://en.wikipedia.org/w/api.php"
params = {
    "action": "query",
    "prop": "extracts|langlinks",
    "exintro": 1,
    "explaintext": 1,
    "titles": search_title,
    "lllang": "zh",
    "format": "json",
    "redirects": 1
}

headers = {"User-Agent": "VegetationIngestScript/1.0"}

response = requests.get(url, params=params, headers=headers, timeout=10)
data = response.json()

print("=" * 70)
print("Wikipedia API Response for 'Zelkova serrata'")
print("=" * 70)

pages = data.get("query", {}).get("pages", {})

for page_id, page_data in pages.items():
    print(f"\nPage ID: {page_id}")
    print(f"Title: {page_data.get('title', 'N/A')}")
    
    extract = page_data.get("extract", "")
    print(f"\nIntro paragraph:")
    print("-" * 70)
    print(extract[:500])
    print("-" * 70)
    
    # Try different regex patterns
    print("\n\nTesting regex patterns:")
    
    patterns = [
        (r"commonly known as (?:the )?([^,.]+)", "commonly known as"),
        (r"also (?:called|known as) (?:the )?([^,.]+)", "also called/known as"),
        (r"(?:Japanese zelkova|[A-Z][a-z]+ zelkova)", "Direct zelkova match"),
    ]
    
    for pattern, desc in patterns:
        match = re.search(pattern, extract, re.IGNORECASE)
        if match:
            print(f"✓ {desc}: '{match.group(0)}'")
            if match.groups():
                print(f"  Captured: '{match.group(1)}'")
        else:
            print(f"✗ {desc}: No match")
    
    # Language links
    langlinks = page_data.get("langlinks", [])
    print(f"\n\nChinese language link:")
    if langlinks:
        for link in langlinks:
            print(f"  {link.get('lang', '?')}: {link.get('*', '?')}")
    else:
        print("  None found")

print("\n" + "=" * 70)
