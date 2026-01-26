#!/usr/bin/env python
"""
DuckDuckGoで工務店を検索してURLを収集するスクリプト
"""
import json
import re
import subprocess
import time
from urllib.parse import urlparse, quote
import sys

# コンテナポート（引数で渡す）
PORTS = [55146, 55141, 55151, 55145, 55154]

# 茨城県の工務店リスト
COMPANIES = [
    "株式会社池田建設 茨城",
    "株式会社高野工務店 茨城",
    "株式会社コダマホーム 茨城",
    "株式会社ロゴスホーム 茨城",
    "有限会社エイチ・ケーホーム 茨城",
    "株式会社蓮見工務店 茨城",
    "株式会社スズセイホーム 茨城",
    "株式会社クリエすずき建設 茨城",
    "株式会社ワカバハウス 茨城",
    "株式会社丸八工務店 茨城",
    "センターホーム 菅谷工務店 茨城",
    "株式会社ハヤシ工務店 茨城",
    "株式会社一条工務店 茨城",
    "株式会社和奏建設 茨城",
    "株式会社吉川工務店 茨城",
    "株式会社小野不動産建設 茨城",
    "株式会社イサカホーム 茨城",
    "株式会社フォレストホーム 茨城",
    "株式会社石井工務店 茨城",
    "株式会社白石工務店 茨城",
    "株式会社イオスホーム 茨城",
    "株式会社黒須建設 茨城",
    "株式会社大塚建設 茨城",
    "株式会社東武ニューハウス 茨城",
    "株式会社アイ工務店 茨城",
    "ウィザースホーム 茨城",
    "株式会社ノーブルホーム 茨城",
    "株式会社細田工務店 茨城",
    "株式会社土屋ホーム 茨城",
    "株式会社大沼工務店 茨城",
    "株式会社三陽工務店 茨城",
    "株式会社奥山工務店 茨城",
    "株式会社大和田工務店 茨城",
    "株式会社匠の会住宅 茨城",
    "パパまるハウス 茨城",
    "ヤマダホームズ 茨城",
    "To Casa 茨城",
    "パネットホーム 茨城",
    "パナソニックホームズ 茨城",
    "ミサワホーム 茨城",
]

def navigate(port, url):
    """Navigate browser to URL"""
    cmd = f'curl -s -X POST http://localhost:{port}/browser/navigate -H "Content-Type: application/json" -d \'{{"url": "{url}"}}\''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return 'success' in result.stdout

def get_content(port):
    """Get page content"""
    cmd = f'curl -s -X POST http://localhost:{port}/browser/content'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return None

def extract_first_url(html, company_name):
    """Extract first relevant URL from search results"""
    links = re.findall(r'href="(https?://[^"]+)"', html)

    skip = ['duckduckgo', 'google', 'bing', 'yahoo', 'facebook', 'twitter',
            'instagram', 'youtube', 'wikipedia', 'amazon', 'rakuten',
            'suumo', 'homes.co.jp', 'athome', 'ie-tateru', 'builder-w',
            'houzz', 'auka', 'iestyle', 'home4u', 'yume-wagaya', 'cloudflare',
            'jsdelivr', 'googleapis', 'gstatic']

    for link in links:
        domain = urlparse(link).netloc.lower()
        if any(s in domain for s in skip):
            continue
        # Check if link looks like a company website
        if '.co.jp' in domain or '.jp' in domain or '.com' in domain:
            return link
    return None

def main():
    results = {}
    batch_size = len(PORTS)

    for i in range(0, len(COMPANIES), batch_size):
        batch = COMPANIES[i:i+batch_size]

        # Navigate all browsers in parallel
        for j, company in enumerate(batch):
            if j < len(PORTS):
                port = PORTS[j]
                query = quote(company)
                url = f"https://duckduckgo.com/?q={query}"
                navigate(port, url)

        time.sleep(3)  # Wait for pages to load

        # Get content from all browsers
        for j, company in enumerate(batch):
            if j < len(PORTS):
                port = PORTS[j]
                data = get_content(port)
                if data and data.get('success'):
                    html = data.get('html', '')
                    found_url = extract_first_url(html, company)
                    if found_url:
                        # Clean company name
                        clean_name = company.replace(' 茨城', '')
                        results[clean_name] = found_url
                        print(f"{clean_name}: {found_url}", file=sys.stderr)

    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
