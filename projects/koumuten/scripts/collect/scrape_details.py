import requests
import re
import json
import time
import os
from urllib.parse import urljoin

BASE_URL = "https://suumo.jp"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# All companies found from SUUMO
ALL_COMPANIES = [
    {"name": "アイダ設計", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_aida/"},
    {"name": "日本ハウスホールディングス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_higashinihon/"},
    {"name": "タマホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_tamahome/"},
    {"name": "ヤマダホームズ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_yamadahomes/"},
    {"name": "住友林業", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sfc/"},
    {"name": "クレバリーホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_cleverlyhome/"},
    {"name": "トヨタホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_toyotahome/"},
    {"name": "ミサワホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_misawa/"},
    {"name": "パナソニック ホームズ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_panasonichomes/"},
    {"name": "旭化成ホームズ（ヘーベルハウス）", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_hebel/"},
    {"name": "三井ホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_mitsuihome/"},
    {"name": "積水ハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sekisuihouse/"},
    {"name": "ダイワハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_daiwahouse/"},
    {"name": "ロイヤルハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_royalhouse/"},
    {"name": "セルコホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_selcohome/"},
    {"name": "綿半林業", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sciencehome/"},
    {"name": "古河林業", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_furukawaringyo/"},
    {"name": "ヤマト住建", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_yamatojk021/"},
    {"name": "スウェーデンハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_swedenhouse/"},
    {"name": "ロビンスジャパン", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_archph/"},
    {"name": "イシンホーム住宅研究会", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ishinhome/"},
    {"name": "アキュラホーム（AQ Group）", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_aqura/"},
    {"name": "一条工務店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ichijo/"},
    {"name": "アイ工務店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_140031/"},
    {"name": "富士住建", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_fujijuken/"},
    {"name": "住友不動産", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sumitomord/"},
    {"name": "アエラホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_aerahome/"},
    {"name": "石田屋", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_116572/"},
    {"name": "アルネットホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_alnethome/"},
    {"name": "ユニバーサルホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_universalhome/"},
    {"name": "夢ハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_139306/"},
    {"name": "廣神建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_116557/"},
    {"name": "ハーバーハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_herbarhouse/"},
    {"name": "デザインハウス・エフ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_dhf/"},
    {"name": "パパまるハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_papamaruhausu/"},
    {"name": "大進建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_116397/"},
    {"name": "セキスイハイム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sekisuiheim/"},
    {"name": "桧家住宅", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_129404/"},
    {"name": "昭栄建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_080019/"},
    {"name": "ステーツ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_501267/"},
    {"name": "横尾材木店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_yokoo/"},
    {"name": "Rico Life", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_kakudaihome/"},
    {"name": "和奏建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_120393/"},
    {"name": "オールハウジング", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_allhousing/"},
    {"name": "T's ALL WORKS", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_tsgaragefurniture/"},
    {"name": "コンチネンタルホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_contihome/"},
    {"name": "無添加住宅", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_mutenkahouse/"},
    {"name": "野口建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_141836/"},
    {"name": "相生建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ishinhomejyuutakukenkyuukaiaioikensetsu/"},
    {"name": "サンワ設計", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_127147/"},
    {"name": "ホビースタイル角屋工業", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_hobbystyle/"},
    {"name": "アイワホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_aiwahome/"},
    {"name": "マスケン", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_masuken/"},
    {"name": "ファイブイズホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_fiveishome/"},
    {"name": "アートクラフト", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_artcraft/"},
    {"name": "いい感じの平屋IKI", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_iikanji/"},
    {"name": "ファーストステージ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_firststage/"},
    {"name": "栃木ハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_tochigihouse/"},
    {"name": "石井工務店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ishiikoumuten/"},
    {"name": "かなう家", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_kanauya/"},
    {"name": "サンエルホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sanelhome/"},
    {"name": "オークヴィルホームズ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_oakvillehomes/"},
    {"name": "楽屋", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_rakuya/"},
    {"name": "thinks", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_thinks/"},
    {"name": "メープルホームズ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_maplehomes/"},
    {"name": "竹並建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_takenami/"},
    {"name": "カシワ建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_kashiwa/"},
    {"name": "平屋工房", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_hirayakoubou/"},
    {"name": "ジブンハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_jibunhouse/"},
    {"name": "TIME+", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_timeplus/"},
    {"name": "BinO前橋/立見建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_bino/"},
    {"name": "小向建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_komukai/"},
    {"name": "エースホーム太田店(白石建設)", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_acehome/"},
    {"name": "古郡ホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_furugori/"},
    {"name": "しのだ工務店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_shinoda/"},
    {"name": "大一建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_daiichi/"},
    {"name": "アットナチュレ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_atnature/"},
    {"name": "タツホーム 竜建", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_tatsuhome/"},
    {"name": "Eco+Kamiken 上里建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_kamisato/"},
    {"name": "Kayu style ハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_kayustyle/"},
    {"name": "栃木建築社", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_tochigikensetsu/"},
    {"name": "Bespoke Design Works", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_bespoke/"},
    {"name": "ハウス オブ デコ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_houseofdeco/"},
    {"name": "ジブログデザイン", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ziblogdesign/"},
    {"name": "SAMATA", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_samata/"},
    {"name": "ZENSYU-HOUSE", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_zensyuhouse/"},
    {"name": "東建ビルダー", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_token/"},
    {"name": "モックの家/草処建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_mock/"},
    {"name": "IE-LABO/三山建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ielabo/"},
    {"name": "エイ・ワン(A-1 home)", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_aone/"},
    {"name": "フジコーポレーション", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_fujicorp/"},
    {"name": "SHIROTA", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_shirota/"},
    {"name": "ヤマミズホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_yamamizu/"},
    {"name": "リッケンハウジング", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_rikken/"},
    {"name": "ARC style", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_arcstyle/"},
    {"name": "Archi Factory ヒマワリ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_himawari/"},
    {"name": "Vie house", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_viehouse/"},
    {"name": "無垢スタイル建築設計", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_mukustyle/"},
    {"name": "Toiro 四季の住まい", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_toiro/"},
    {"name": "ワコーハウジング", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_wakohousing/"},
    {"name": "ソーフィールドホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sofield/"},
    {"name": "リソーケンセツ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_risou/"},
    {"name": "大雄建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_daiyu/"},
    {"name": "齋藤住建", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_saito/"},
    {"name": "ビスコッティハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_biscotti/"},
    {"name": "藍の家", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ainoie/"},
    {"name": "RELUXY HOME", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_reluxy/"},
    {"name": "彩ハウス", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_ayahouse/"},
    {"name": "トトモニ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_totomoni/"},
    {"name": "渋沢", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_shibusawa/"},
    {"name": "関工務所", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sekikoumuten/"},
    {"name": "シブサワスタイル", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_shibusawastyle/"},
    {"name": "杉内建設", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_sugiuchi/"},
    {"name": "fun style", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_funstyle/"},
    {"name": "ニットーホーム", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_nittohome/"},
    {"name": "高草木工務店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_takakusagi/"},
    {"name": "BinO太田 中村住宅工業", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_binoota/"},
    {"name": "ヒロミヤ住建", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_hiromiya/"},
    {"name": "A ARCHiTECT", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_aarchitect/"},
    {"name": "古川工務店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_furukawa/"},
    {"name": "studio*mag", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_studiomag/"},
    {"name": "山田工務店", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_yamada/"},
    {"name": "リプレイ", "suumo_url": "https://suumo.jp/chumon/tn_gumma/rn_replay/"},
]


def get_company_details(company):
    """Get detailed information from company page"""
    try:
        response = requests.get(company['suumo_url'], headers=headers, timeout=30)
        html = response.text

        details = {
            'name': company['name'],
            'suumo_url': company['suumo_url'],
            'homepage': None,
            'contact_url': None,
            'instagram': None,
            'location': None,
            'features': []
        }

        # Extract official homepage URL
        # Look for patterns like "公式サイト" or "ホームページ"
        hp_patterns = [
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>公式[サホ]',
            r'<a[^>]*href="(https?://[^"]+)"[^>]*>[^<]*ホームページ',
            r'公式[サホ][イー][トム][^<]*<a[^>]*href="(https?://[^"]+)"',
            r'href="(https?://[^"]+)"[^>]*class="[^"]*official',
            r'data-official-url="(https?://[^"]+)"',
            r'"officialUrl"\s*:\s*"(https?://[^"]+)"',
        ]

        for pattern in hp_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                url = match.group(1)
                if 'suumo' not in url.lower() and url not in ['#', '']:
                    details['homepage'] = url
                    break

        # Extract location info
        loc_patterns = [
            r'所在地[^<]*</dt>[^<]*<dd[^>]*>([^<]+)',
            r'所在地[^\n]*\n[^\n]*([^\n<]+市[^\n<]*)',
            r'群馬県([^<\n]+市)',
            r'<address[^>]*>([^<]+)</address>',
        ]

        for pattern in loc_patterns:
            match = re.search(pattern, html)
            if match:
                loc = match.group(1).strip()
                if '群馬' in loc or '前橋' in loc or '高崎' in loc or '太田' in loc:
                    details['location'] = loc
                    break

        # If no specific location found, try to find city name in HTML
        if not details['location']:
            city_match = re.search(r'群馬県([^<\n]+?(?:市|町|村))', html)
            if city_match:
                details['location'] = '群馬県' + city_match.group(1)

        # Extract Instagram URL
        insta_patterns = [
            r'href="(https?://(?:www\.)?instagram\.com/[^"]+)"',
            r'instagram\.com/([a-zA-Z0-9_.]+)',
        ]

        for pattern in insta_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                if 'instagram.com/' in match.group(0):
                    details['instagram'] = match.group(1) if 'http' in match.group(1) else f"https://www.instagram.com/{match.group(1)}"
                    break

        # Extract features/keywords
        feature_patterns = [
            r'キーワード[^<]*</dt>[^<]*<dd[^>]*>([^<]+)',
            r'こだわり[^<]*</dt>[^<]*<dd[^>]*>([^<]+)',
            r'特徴[^<]*</dt>[^<]*<dd[^>]*>([^<]+)',
            r'class="[^"]*keyword[^"]*"[^>]*>([^<]+)',
        ]

        for pattern in feature_patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                feature = match.strip()
                if feature and len(feature) < 100 and feature not in details['features']:
                    details['features'].append(feature)

        # Check for common feature keywords in page
        feature_keywords = [
            ('高性能住宅', '高性能'),
            ('高気密高断熱', '高気密・高断熱'),
            ('自然素材', '自然素材'),
            ('無垢材', '無垢材'),
            ('デザイン住宅', 'デザイン住宅'),
            ('ローコスト', 'ローコスト'),
            ('平屋', '平屋'),
            ('ZEH', 'ZEH対応'),
            ('省エネ', '省エネ'),
            ('長期優良住宅', '長期優良住宅'),
            ('耐震', '耐震'),
            ('注文住宅', '注文住宅'),
            ('木造', '木造'),
            ('輸入住宅', '輸入住宅'),
        ]

        for keyword, label in feature_keywords:
            if keyword in html and label not in details['features']:
                details['features'].append(label)

        return details
    except Exception as e:
        print(f"Error fetching details for {company['name']}: {e}")
        return {
            'name': company['name'],
            'suumo_url': company['suumo_url'],
            'homepage': None,
            'contact_url': None,
            'instagram': None,
            'location': None,
            'features': []
        }


def main():
    detailed_companies = []

    for i, company in enumerate(ALL_COMPANIES):
        print(f"Processing {i+1}/{len(ALL_COMPANIES)}: {company['name']}")
        details = get_company_details(company)
        detailed_companies.append(details)
        time.sleep(0.5)  # Rate limiting

    # Save results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    output_path = os.path.join(project_dir, 'output', 'koumuten_detailed.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_companies, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {output_path}")
    print(f"Total companies: {len(detailed_companies)}")

    # Count companies with various data
    with_homepage = sum(1 for c in detailed_companies if c.get('homepage'))
    with_location = sum(1 for c in detailed_companies if c.get('location'))
    with_instagram = sum(1 for c in detailed_companies if c.get('instagram'))
    with_features = sum(1 for c in detailed_companies if c.get('features'))

    print(f"Companies with homepage: {with_homepage}")
    print(f"Companies with location: {with_location}")
    print(f"Companies with Instagram: {with_instagram}")
    print(f"Companies with features: {with_features}")

    return detailed_companies


if __name__ == "__main__":
    main()
