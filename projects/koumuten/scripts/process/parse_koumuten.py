#!/usr/bin/env python
"""
Parse koumuten info from saved HTML files
"""
import json
import re
import os
from urllib.parse import urlparse

def extract_from_yume_wagaya(html):
    """Extract from yume-wagaya ZEH builder list"""
    companies = []

    # Find table rows with company info
    # Pattern: company name followed by location info
    patterns = [
        # Table cell patterns
        r'<td[^>]*>([^<]{5,40}(?:工務店|建設|住宅|ハウス|ホーム|建築|不動産))</td>',
        r'<tr[^>]*>.*?<td[^>]*>([^<]{5,40})</td>.*?<td[^>]*>([^<]*茨城[^<]*)</td>',
    ]

    # Get all company-like names
    for pattern in patterns:
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                name, location = m
            else:
                name = m
                location = '茨城県'
            name = name.strip()
            if len(name) > 5 and len(name) < 50:
                companies.append({'name': name, 'location': location.strip() if isinstance(m, tuple) else ''})

    return companies

def extract_from_iestyle(html):
    """Extract from iestyle-ibaraki"""
    companies = []

    # Find company cards/listings
    patterns = [
        r'<h[234][^>]*>([^<]{5,50}(?:工務店|建設|住宅|ハウス|ホーム|建築))</h',
        r'class="[^"]*company[^"]*"[^>]*>([^<]{5,50})<',
        r'<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]{5,50}(?:工務店|建設|住宅|ハウス|ホーム|建築))</a>',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                url, name = m
                companies.append({'name': name.strip(), 'url': url})
            else:
                companies.append({'name': m.strip(), 'url': ''})

    return companies

def extract_from_houzz(html):
    """Extract from Houzz professionals list"""
    companies = []

    # Houzz uses structured listings
    # Look for professional names with links
    patterns = [
        r'<a[^>]*href="(https?://www\.houzz\.jp/[^"]+)"[^>]*>([^<]{5,50})</a>',
        r'<span[^>]*class="[^"]*pro-name[^"]*"[^>]*>([^<]+)</span>',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for m in matches:
            if isinstance(m, tuple):
                url, name = m
                companies.append({'name': name.strip(), 'url': url})
            else:
                companies.append({'name': m.strip(), 'url': ''})

    return companies

def main():
    all_companies = []

    # Process each file
    files = [
        ('/tmp/zeh.json', 'yume-wagaya', extract_from_yume_wagaya),
        ('/tmp/iestyle.json', 'iestyle', extract_from_iestyle),
        ('/tmp/houzz.json', 'houzz', extract_from_houzz),
    ]

    for filepath, source, extractor in files:
        if os.path.exists(filepath):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                if data.get('success'):
                    html = data.get('html', '')
                    companies = extractor(html)
                    for c in companies:
                        c['source'] = source
                    all_companies.extend(companies)
                    print(f"{source}: Found {len(companies)} companies")
            except Exception as e:
                print(f"Error processing {source}: {e}")

    # Deduplicate by name
    seen = {}
    for c in all_companies:
        name = c['name']
        if name not in seen:
            seen[name] = c

    print(f"\nTotal unique companies: {len(seen)}")

    # Output
    output = list(seen.values())
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
