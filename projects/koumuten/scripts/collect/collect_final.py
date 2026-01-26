#!/usr/bin/env python
"""
茨城県工務店の最終リスト作成スクリプト
収集した情報を統合し、各社の詳細情報を含むJSONを生成
"""
import json
import re
import os
from urllib.parse import urlparse

# 茨城県の工務店リスト（収集データから抽出）
IBARAKI_KOUMUTEN = [
    # yume-wagaya ZEHビルダー一覧より
    {"name": "株式会社池田建設", "location": "茨城県"},
    {"name": "株式会社高野工務店", "location": "茨城県"},
    {"name": "株式会社コダマホーム", "location": "茨城県"},
    {"name": "株式会社ロゴスホーム", "location": "茨城県"},
    {"name": "有限会社エイチ・ケーホーム", "location": "茨城県"},
    {"name": "株式会社蓮見工務店", "location": "茨城県"},
    {"name": "株式会社スズセイホーム", "location": "茨城県"},
    {"name": "株式会社クリエすずき建設", "location": "茨城県"},
    {"name": "株式会社ワカバハウス", "location": "茨城県"},
    {"name": "株式会社丸八工務店", "location": "茨城県"},
    {"name": "センターホーム（株式会社菅谷工務店）", "location": "茨城県"},
    {"name": "株式会社ハヤシ工務店", "location": "茨城県"},
    {"name": "株式会社一条工務店", "location": "茨城県"},
    {"name": "株式会社和奏建設", "location": "茨城県"},
    {"name": "株式会社吉川工務店", "location": "茨城県"},
    {"name": "株式会社小野不動産建設", "location": "茨城県"},
    {"name": "株式会社イサカホーム", "location": "茨城県"},
    {"name": "株式会社フォレストホーム", "location": "茨城県"},
    {"name": "株式会社石井工務店", "location": "茨城県"},
    {"name": "株式会社白石工務店", "location": "茨城県"},
    {"name": "株式会社イオスホーム", "location": "茨城県"},
    {"name": "株式会社黒須建設", "location": "茨城県"},
    {"name": "株式会社大塚建設", "location": "茨城県"},
    {"name": "株式会社東武ニューハウス", "location": "茨城県"},
    {"name": "株式会社アイ工務店", "location": "茨城県"},
    {"name": "ウィザースホーム", "location": "茨城県"},
    {"name": "株式会社ノーブルホーム", "location": "茨城県つくば市"},
    {"name": "株式会社細田工務店", "location": "茨城県"},
    {"name": "株式会社土屋ホーム", "location": "茨城県"},

    # home4u・その他ソースより
    {"name": "パナソニックホームズ", "location": "茨城県"},
    {"name": "ミサワホーム", "location": "茨城県"},
    {"name": "クレバリーホーム", "location": "茨城県"},
    {"name": "桧家住宅", "location": "茨城県"},
    {"name": "三井ホーム", "location": "茨城県"},
    {"name": "大和ハウス工業", "location": "茨城県"},
    {"name": "積水ハウス", "location": "茨城県"},
    {"name": "住友林業", "location": "茨城県"},
    {"name": "セキスイハイム", "location": "茨城県"},
    {"name": "タマホーム", "location": "茨城県"},
    {"name": "アキュラホーム", "location": "茨城県"},
    {"name": "アエラホーム", "location": "茨城県"},

    # builder-w・ie-tateru等より
    {"name": "株式会社大沼工務店", "location": "茨城県水戸市"},
    {"name": "株式会社三陽工務店", "location": "茨城県"},
    {"name": "株式会社奥山工務店", "location": "茨城県"},
    {"name": "株式会社大和田工務店", "location": "茨城県"},
    {"name": "株式会社匠の会住宅", "location": "茨城県"},
    {"name": "パパまるハウス", "location": "茨城県"},
    {"name": "ヤマダホームズ", "location": "茨城県"},
    {"name": "To Casa", "location": "茨城県"},
    {"name": "パネットホーム", "location": "茨城県"},
]

def search_company_url(company_name, html_files):
    """Search for company URL in saved HTML files"""
    for filepath in html_files:
        if os.path.exists(filepath):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                if data.get('success'):
                    html = data.get('html', '')
                    # Search for company name near a URL
                    pattern = rf'<a[^>]*href="(https?://[^"]+)"[^>]*>[^<]*{re.escape(company_name[:10])}[^<]*</a>'
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for url in matches:
                        domain = urlparse(url).netloc.lower()
                        skip = ['google', 'facebook', 'twitter', 'instagram', 'youtube',
                               'suumo', 'homes.co.jp', 'athome', 'yume-wagaya', 'houzz',
                               'ie-tateru', 'builder-w', 'auka', 'iestyle']
                        if not any(s in domain for s in skip):
                            return url
            except:
                pass
    return None

def main():
    # HTML files to search
    html_files = [
        '/tmp/zeh.json',
        '/tmp/iestyle.json',
        '/tmp/houzz.json',
        '/tmp/builderw_ib.json',
        '/tmp/ietateru_ib.json',
        '/tmp/auka_ib.json',
        '/tmp/home4u.json',
    ]

    results = []
    for company in IBARAKI_KOUMUTEN:
        name = company['name']
        location = company.get('location', '茨城県')

        # Try to find URL
        url = search_company_url(name, html_files)

        result = {
            "company_name": name,
            "location": location,
            "website_url": url or "",
            "contact_form_url": "",
            "instagram_url": "",
            "features": []
        }
        results.append(result)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n// Total: {len(results)} companies", file=__import__('sys').stderr)

if __name__ == '__main__':
    main()
