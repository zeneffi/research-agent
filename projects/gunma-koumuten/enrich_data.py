import json
import requests
import re
import time

# Known official websites for major builders
KNOWN_WEBSITES = {
    "アイダ設計": {"homepage": "https://www.aidagroup.co.jp/", "location": "群馬県前橋市"},
    "日本ハウスホールディングス": {"homepage": "https://www.nihonhouse-hd.co.jp/", "location": "群馬県高崎市"},
    "タマホーム": {"homepage": "https://www.tamahome.jp/", "location": "群馬県高崎市"},
    "ヤマダホームズ": {"homepage": "https://yamadahomes.jp/", "location": "群馬県高崎市"},
    "住友林業": {"homepage": "https://sfc.jp/", "location": "群馬県高崎市"},
    "クレバリーホーム": {"homepage": "https://www.cleverlyhome.com/", "location": "群馬県前橋市"},
    "トヨタホーム": {"homepage": "https://www.toyotahome.co.jp/", "location": "群馬県前橋市"},
    "ミサワホーム": {"homepage": "https://www.misawa.co.jp/", "location": "群馬県前橋市"},
    "パナソニック ホームズ": {"homepage": "https://homes.panasonic.com/", "location": "群馬県前橋市"},
    "旭化成ホームズ（ヘーベルハウス）": {"homepage": "https://www.asahi-kasei.co.jp/hebel/", "location": "群馬県前橋市"},
    "三井ホーム": {"homepage": "https://www.mitsuihome.co.jp/", "location": "群馬県高崎市"},
    "積水ハウス": {"homepage": "https://www.sekisuihouse.co.jp/", "location": "群馬県前橋市"},
    "ダイワハウス": {"homepage": "https://www.daiwahouse.co.jp/", "location": "群馬県高崎市"},
    "ロイヤルハウス": {"homepage": "https://www.royal-house.co.jp/", "location": "群馬県"},
    "セルコホーム": {"homepage": "https://selcohome.jp/", "location": "群馬県"},
    "綿半林業": {"homepage": "https://www.science-home.jp/", "location": "群馬県"},
    "古河林業": {"homepage": "https://furukawa-ringyo.co.jp/", "location": "群馬県"},
    "ヤマト住建": {"homepage": "https://www.yamatojk.co.jp/", "location": "群馬県太田市"},
    "スウェーデンハウス": {"homepage": "https://www.swedenhouse.co.jp/", "location": "群馬県前橋市"},
    "ロビンスジャパン": {"homepage": "https://robins-j.com/", "location": "群馬県"},
    "イシンホーム住宅研究会": {"homepage": "https://www.ishinhome.co.jp/", "location": "群馬県"},
    "アキュラホーム（AQ Group）": {"homepage": "https://www.aqura.co.jp/", "location": "群馬県前橋市"},
    "一条工務店": {"homepage": "https://www.ichijo.co.jp/", "location": "群馬県前橋市"},
    "アイ工務店": {"homepage": "https://www.ai-koumuten.co.jp/", "location": "群馬県高崎市"},
    "富士住建": {"homepage": "https://www.fujijuken.co.jp/", "location": "群馬県前橋市"},
    "住友不動産": {"homepage": "https://www.sumitomo-rd.co.jp/", "location": "群馬県前橋市"},
    "アエラホーム": {"homepage": "https://www.aerahome.com/", "location": "群馬県"},
    "石田屋": {"homepage": "https://www.ishidaya.co.jp/", "location": "群馬県高崎市"},
    "アルネットホーム": {"homepage": "https://www.alnethome.com/", "location": "群馬県"},
    "ユニバーサルホーム": {"homepage": "https://www.universalhome.co.jp/", "location": "群馬県"},
    "夢ハウス": {"homepage": "https://www.yumehouse.co.jp/", "location": "群馬県"},
    "廣神建設": {"homepage": "https://www.wabika.jp/", "location": "群馬県高崎市"},
    "ハーバーハウス": {"homepage": "https://www.herbarhouse.jp/", "location": "群馬県"},
    "デザインハウス・エフ": {"homepage": "https://www.designhouse-f.com/", "location": "群馬県太田市"},
    "パパまるハウス": {"homepage": "https://www.papamaru.jp/", "location": "群馬県"},
    "大進建設": {"homepage": "https://www.daishin-kensetsu.co.jp/", "location": "群馬県伊勢崎市"},
    "セキスイハイム": {"homepage": "https://www.sekisuiheim.com/", "location": "群馬県前橋市"},
    "桧家住宅": {"homepage": "https://www.hinokiya.jp/", "location": "群馬県前橋市"},
    "昭栄建設": {"homepage": "https://www.shoei-c.co.jp/", "location": "群馬県"},
    "ステーツ": {"homepage": "https://www.states.co.jp/", "location": "群馬県"},
    "横尾材木店": {"homepage": "https://www.yokoo-zaimokuten.co.jp/", "location": "群馬県高崎市"},
    "Rico Life": {"homepage": "https://rico-life.jp/", "location": "群馬県"},
    "和奏建設": {"homepage": "https://wakana-k.com/", "location": "群馬県"},
    "オールハウジング": {"homepage": "https://all-housing.jp/", "location": "群馬県"},
    "T's ALL WORKS": {"homepage": "https://ts-allworks.com/", "location": "群馬県"},
    "コンチネンタルホーム": {"homepage": "https://www.continentalhome.jp/", "location": "群馬県前橋市"},
    "無添加住宅": {"homepage": "https://www.mutenkahouse.co.jp/", "location": "群馬県"},
    "野口建設": {"homepage": "https://www.noguchi-k.co.jp/", "location": "群馬県"},
    "相生建設": {"homepage": "https://www.aioi-k.co.jp/", "location": "群馬県"},
    "サンワ設計": {"homepage": "https://www.sanwa-sekkei.co.jp/", "location": "群馬県太田市"},
}

# Features mapping based on company characteristics
COMPANY_FEATURES = {
    "アイダ設計": ["ローコスト", "注文住宅", "高性能"],
    "日本ハウスホールディングス": ["檜の家", "木造", "注文住宅"],
    "タマホーム": ["ローコスト", "高性能", "長期優良住宅"],
    "ヤマダホームズ": ["注文住宅", "木造", "省エネ"],
    "住友林業": ["木造", "高品質", "デザイン住宅"],
    "クレバリーホーム": ["タイル外壁", "高性能", "注文住宅"],
    "トヨタホーム": ["鉄骨", "高性能", "スマートハウス"],
    "ミサワホーム": ["蔵のある家", "高性能", "デザイン住宅"],
    "パナソニック ホームズ": ["鉄骨", "高気密・高断熱", "スマートハウス"],
    "旭化成ホームズ（ヘーベルハウス）": ["鉄骨", "耐震", "長期優良住宅"],
    "三井ホーム": ["ツーバイフォー", "高品質", "デザイン住宅"],
    "積水ハウス": ["高品質", "高気密・高断熱", "注文住宅"],
    "ダイワハウス": ["高品質", "省エネ", "注文住宅"],
    "ロイヤルハウス": ["ローコスト", "木造", "注文住宅"],
    "セルコホーム": ["輸入住宅", "カナダ住宅", "高気密・高断熱"],
    "綿半林業": ["木の家", "自然素材", "注文住宅"],
    "古河林業": ["自然素材", "木の家", "注文住宅"],
    "ヤマト住建": ["高気密・高断熱", "ZEH対応", "省エネ"],
    "スウェーデンハウス": ["北欧住宅", "高気密・高断熱", "輸入住宅"],
    "ロビンスジャパン": ["輸入住宅", "デザイン住宅", "注文住宅"],
    "イシンホーム住宅研究会": ["太陽光発電", "省エネ", "注文住宅"],
    "アキュラホーム（AQ Group）": ["ローコスト", "高性能", "注文住宅"],
    "一条工務店": ["高気密・高断熱", "全館床暖房", "太陽光発電"],
    "アイ工務店": ["ローコスト", "高性能", "注文住宅"],
    "富士住建": ["フル装備", "ローコスト", "注文住宅"],
    "住友不動産": ["デザイン住宅", "高品質", "注文住宅"],
    "アエラホーム": ["高気密・高断熱", "省エネ", "注文住宅"],
    "石田屋": ["自然素材", "無添加", "健康住宅"],
    "アルネットホーム": ["注文住宅", "高性能", "デザイン住宅"],
    "ユニバーサルホーム": ["地熱", "省エネ", "注文住宅"],
    "夢ハウス": ["無垢材", "自然素材", "健康住宅"],
    "廣神建設": ["和風", "デザイン住宅", "注文住宅"],
    "ハーバーハウス": ["ローコスト", "注文住宅", "高性能"],
    "デザインハウス・エフ": ["デザイン住宅", "注文住宅", "ローコスト"],
    "パパまるハウス": ["ローコスト", "規格住宅", "注文住宅"],
    "大進建設": ["地域密着", "注文住宅", "木造"],
    "セキスイハイム": ["鉄骨", "太陽光発電", "スマートハウス"],
    "桧家住宅": ["Z空調", "高気密・高断熱", "注文住宅"],
    "昭栄建設": ["地域密着", "注文住宅", "リフォーム"],
    "ステーツ": ["デザイン住宅", "注文住宅", "高性能"],
    "横尾材木店": ["木の家", "自然素材", "注文住宅"],
    "Rico Life": ["ローコスト", "注文住宅", "平屋"],
    "和奏建設": ["自然素材", "無垢材", "健康住宅"],
    "オールハウジング": ["注文住宅", "リフォーム", "地域密着"],
    "T's ALL WORKS": ["ガレージハウス", "デザイン住宅", "注文住宅"],
    "コンチネンタルホーム": ["高気密・高断熱", "注文住宅", "省エネ"],
    "無添加住宅": ["自然素材", "無添加", "健康住宅"],
    "野口建設": ["地域密着", "注文住宅", "木造"],
    "相生建設": ["注文住宅", "省エネ", "地域密着"],
    "サンワ設計": ["デザイン住宅", "注文住宅", "高性能"],
}

def enrich_data():
    # Load existing data
    with open('/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/projects/gunma-koumuten/output/koumuten_detailed.json', 'r', encoding='utf-8') as f:
        companies = json.load(f)

    # Enrich with known data
    for company in companies:
        name = company['name']

        # Add known website info
        if name in KNOWN_WEBSITES:
            if not company.get('homepage'):
                company['homepage'] = KNOWN_WEBSITES[name].get('homepage')
            if not company.get('location'):
                company['location'] = KNOWN_WEBSITES[name].get('location')

        # Add known features
        if name in COMPANY_FEATURES:
            existing_features = set(company.get('features', []))
            new_features = COMPANY_FEATURES[name]
            company['features'] = list(existing_features.union(new_features))

    # Save enriched data
    output_path = '/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/projects/gunma-koumuten/output/koumuten_enriched.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(companies, f, ensure_ascii=False, indent=2)

    print(f"Enriched data saved to {output_path}")

    # Count stats
    with_homepage = sum(1 for c in companies if c.get('homepage'))
    with_location = sum(1 for c in companies if c.get('location'))
    with_features = sum(1 for c in companies if c.get('features'))

    print(f"Total companies: {len(companies)}")
    print(f"Companies with homepage: {with_homepage}")
    print(f"Companies with location: {with_location}")
    print(f"Companies with features: {with_features}")

    return companies

if __name__ == "__main__":
    enrich_data()
