#!/usr/bin/env python3
"""
茨城県工務店情報抽出スクリプト
"""
import json
import re
import os
import sys
from urllib.parse import urlparse

def extract_koumuten_from_html(html, source_name):
    """Extract koumuten company info from HTML"""
    results = []

    # Skip portal/aggregate sites
    skip_domains = ['ie-tateru', 'builder-w', 'home4u', 'kinoie-hiroba', 'r-plus-house',
                   'auka.jp', 'suumo', 'homes.co.jp', 'athome', 'google', 'facebook',
                   'twitter', 'instagram', 'youtube', 'line.me', 'pinterest',
                   'duckduckgo', 'amazon', 'rakuten', 'yahoo', 'nifty', 'wikipedia',
                   'cloudflare', 'w3.org', 'jsdelivr', 'googleapis']

    # Method 1: Find all links that look like company pages
    links = re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>([^<]+)</a>', html, re.IGNORECASE)

    for url, text in links:
        domain = urlparse(url).netloc.lower()
        if any(s in domain for s in skip_domains):
            continue

        # Check if text looks like a company name
        text = text.strip()
        if len(text) > 2 and len(text) < 60:
            keywords = ['工務店', '建設', '住宅', 'ハウス', 'ホーム', '建築', '設計', '産業', '開発', '不動産']
            if any(kw in text for kw in keywords):
                results.append({
                    'name': text,
                    'url': url,
                    'source': source_name
                })

    # Method 2: Find company names in text (no link)
    company_patterns = [
        r'>([^<]{3,40}工務店)<',
        r'>([^<]{3,40}建設)<',
        r'>株式会社([^<]{3,30})<',
        r'>([^<]{3,30}住宅)<',
        r'>([^<]{3,30}ハウス)<',
        r'>([^<]{3,30}ホーム)<',
    ]

    for pattern in company_patterns:
        matches = re.findall(pattern, html)
        for m in matches:
            m = m.strip()
            if 5 < len(m) < 40 and not any(skip in m.lower() for skip in ['口コミ', 'ランキング', '一覧', '検索', 'お問い合わせ', 'ページ']):
                results.append({
                    'name': m,
                    'url': '',
                    'source': source_name + '_text'
                })

    return results

def main():
    # Process each file
    all_companies = []
    files = {
        '/tmp/ietateru.json': 'ie-tateru',
        '/tmp/builderw.json': 'builder-w',
        '/tmp/home4u.json': 'home4u',
        '/tmp/kinoie.json': 'kinoie-hiroba',
        '/tmp/rplus.json': 'r-plus-house',
        '/tmp/auka.json': 'auka',
        '/tmp/mito.json': 'builder-w-mito',
        '/tmp/tsuchiura.json': 'builder-w-tsuchiura',
        '/tmp/tsukuba.json': 'builder-w-tsukuba',
        '/tmp/ibaraki_all.json': 'ie-tateru-all',
        '/tmp/builderw_ib.json': 'builder-w-ibaraki',
        '/tmp/ietateru_ib.json': 'ie-tateru-ibaraki',
        '/tmp/auka_ib.json': 'auka-ibaraki',
        '/tmp/yume_ib.json': 'yume-wagaya'
    }

    for filepath, source in files.items():
        if os.path.exists(filepath):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                if data.get('success'):
                    html = data.get('html', '')
                    companies = extract_koumuten_from_html(html, source)
                    all_companies.extend(companies)
                    print(f"{source}: Found {len(companies)} companies", file=sys.stderr)
            except Exception as e:
                print(f"Error processing {source}: {e}", file=sys.stderr)
        else:
            print(f"File not found: {filepath}", file=sys.stderr)

    # Separate companies with URLs and without
    with_url = [c for c in all_companies if c['url']]
    without_url = [c for c in all_companies if not c['url']]

    # Deduplicate by domain for those with URLs
    seen_domains = {}
    for company in with_url:
        domain = urlparse(company['url']).netloc
        if domain not in seen_domains:
            seen_domains[domain] = company

    # Deduplicate by name for those without URLs
    seen_names = set()
    unique_names = []
    for company in without_url:
        name = company['name']
        if name not in seen_names and len(name) > 5:
            seen_names.add(name)
            unique_names.append(company)

    print(f"\n=== Companies with URLs: {len(seen_domains)} ===", file=sys.stderr)
    print(f"=== Company names (no URL): {len(unique_names)} ===", file=sys.stderr)

    # Output as JSON
    output = {
        'companies_with_url': [],
        'company_names_only': []
    }

    for domain, company in seen_domains.items():
        output['companies_with_url'].append({
            'name': company['name'],
            'url': company['url'],
            'domain': domain,
            'source': company['source']
        })

    for company in unique_names:
        output['company_names_only'].append({
            'name': company['name'],
            'source': company['source']
        })

    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
