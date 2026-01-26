#!/usr/bin/env python
"""
追加の工務店を検索
"""
import json
import re
import subprocess
import time
from urllib.parse import urlparse, quote
import sys

PORTS = [55146, 55141, 55151, 55145, 55154]

# 追加の工務店リスト
COMPANIES = [
    "クレバリーホーム 茨城",
    "桧家住宅 茨城",
    "三井ホーム 茨城",
    "大和ハウス工業 茨城",
    "積水ハウス 茨城",
    "住友林業 茨城",
    "セキスイハイム 茨城",
    "タマホーム 茨城",
    "アキュラホーム 茨城",
    "アエラホーム 茨城",
    "トヨタホーム 茨城",
    "ユニバーサルホーム 茨城",
    "セルコホーム 茨城",
    "グランディハウス 茨城",
    "アイダ設計 茨城",
    "オープンハウス 茨城",
    "ポラスグループ 茨城",
    "富士住建 茨城",
    "レオハウス 茨城",
    "アールプラスハウス 茨城",
    "無添加住宅 茨城",
    "BESS 茨城",
    "ログハウス 茨城 工務店",
    "カスミ工務店 茨城",
    "茨城県南 工務店",
]

def navigate(port, url):
    cmd = f'curl -s -X POST http://localhost:{port}/browser/navigate -H "Content-Type: application/json" -d \'{{"url": "{url}"}}\''
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return 'success' in result.stdout

def get_content(port):
    cmd = f'curl -s -X POST http://localhost:{port}/browser/content'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return None

def extract_first_url(html, company_name):
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
        if '.co.jp' in domain or '.jp' in domain or '.com' in domain:
            return link
    return None

def main():
    results = {}
    batch_size = len(PORTS)

    for i in range(0, len(COMPANIES), batch_size):
        batch = COMPANIES[i:i+batch_size]

        for j, company in enumerate(batch):
            if j < len(PORTS):
                port = PORTS[j]
                query = quote(company)
                url = f"https://duckduckgo.com/?q={query}"
                navigate(port, url)

        time.sleep(3)

        for j, company in enumerate(batch):
            if j < len(PORTS):
                port = PORTS[j]
                data = get_content(port)
                if data and data.get('success'):
                    html = data.get('html', '')
                    found_url = extract_first_url(html, company)
                    if found_url:
                        clean_name = company.replace(' 茨城', '').replace(' 工務店', '')
                        results[clean_name] = found_url
                        print(f"{clean_name}: {found_url}", file=sys.stderr)

    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
