#!/usr/bin/env python3
"""Check what Chinese language variants Wikipedia has"""

import requests

search_title = "Zelkova serrata"
url = "https://en.wikipedia.org/w/api.php"
params = {
    "action": "query",
    "prop": "langlinks",
    "titles": search_title,
    "lllimit": "max",
    "format": "json",
    "redirects": 1
}

response = requests.get(url, params=params, headers={"User-Agent": "Test/1.0"}, timeout=10)
data = response.json()

print("=" * 70)
print(f"Language Links for '{search_title}'")
print("=" * 70)

pages = data.get("query", {}).get("pages", {})
for page_id, page_data in pages.items():
    langlinks = page_data.get("langlinks", [])
    print(f"\nTotal language links: {len(langlinks)}")
    
    # Filter to Chinese variants
    chinese_variants = [link for link in langlinks if link.get("lang", "").startswith("zh")]
    
    print(f"\nChinese language variants found: {len(chinese_variants)}")
    for link in chinese_variants:
        print(f"  {link.get('lang', '?'):10} → {link.get('*', '?')}")
    
    if not chinese_variants:
        print("\n  Only 'zh' (generic Chinese) available")
        zh_link = next((link for link in langlinks if link.get("lang") == "zh"), None)
        if zh_link:
            print(f"  zh → {zh_link.get('*', '?')}")

print("\n" + "=" * 70)
print("\nConclusion:")
print("  If only 'zh' is available, Wikipedia uses the same article")
print("  for both Simplified and Traditional Chinese.")
print("  We need to convert Simplified → Traditional programmatically.")
print("=" * 70)
