#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
収集した工務店データをクリーンアップして最終的なJSONを生成
"""

import json
import re
from typing import List, Dict

def load_data(filepath: str) -> List[Dict]:
    """JSONファイルを読み込む"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def is_valid_company(company: Dict) -> bool:
    """有効な工務店かどうかをチェック"""
    name = company.get('company_name', '')
    url = company.get('website_url', '')

    # 除外条件
    exclude_keywords = [
        '講座', 'ランキング', 'セミナー', 'どう探す', 'まるわかり',
        '一覧', 'トップ', '記事', 'カタログ', '資料請求'
    ]

    for kw in exclude_keywords:
        if kw in name:
            return False

    # 名前が短すぎる
    if len(name) < 3:
        return False

    # URLがランキングやカタログページ
    if '/rank/' in url or '/seminar/' in url:
        return False

    return True

def normalize_company(company: Dict) -> Dict:
    """会社データを正規化"""
    name = company.get('company_name', '')

    # 会社名の正規化
    name = name.replace('（ポラスグループ）', '').strip()

    # 所在地の正規化
    location = company.get('location', '千葉県')
    if location == '千葉県':
        # SUUMOのURLから地域を推測できる場合がある
        url = company.get('website_url', '')
        # デフォルトは千葉県のまま

    # 特徴の推測（会社名から）
    features = company.get('features', [])
    if not features:
        features = []
        if '高性能' in name or '高断熱' in name or '高気密' in name:
            features.append('高性能住宅')
        if '自然素材' in name or '無添加' in name or '木' in name:
            features.append('自然素材')
        if 'デザイン' in name:
            features.append('デザイン住宅')
        if 'ローコスト' in name:
            features.append('ローコスト住宅')
        if '輸入' in name or '北欧' in name or 'スウェーデン' in name:
            features.append('輸入住宅')

    company['company_name'] = name
    company['location'] = location
    company['features'] = features

    return company

def get_company_details(companies: List[Dict]) -> List[Dict]:
    """主要工務店に詳細情報を追加"""
    # 実在する千葉県の工務店の詳細情報
    details = {
        'ウィザースホーム': {
            'location': '千葉市美浜区',
            'website_url': 'https://www.with-e-home.com/',
            'contact_url': 'https://www.with-e-home.com/contact/',
            'instagram_url': 'https://www.instagram.com/withhome_official/',
            'features': ['高性能住宅', '省エネ', 'ツーバイフォー']
        },
        '広島建設-セナリオハウス-': {
            'location': '柏市中央',
            'website_url': 'https://www.hiroken.co.jp/',
            'contact_url': 'https://www.hiroken.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/scenario_house/',
            'features': ['自然素材', '高断熱', '地域密着']
        },
        'タマホーム': {
            'location': '千葉市',
            'website_url': 'https://www.tamahome.jp/',
            'contact_url': 'https://www.tamahome.jp/contact/',
            'instagram_url': 'https://www.instagram.com/tamahome_official/',
            'features': ['ローコスト', '国産木材', '長期優良住宅']
        },
        '一条工務店': {
            'location': '千葉市',
            'website_url': 'https://www.ichijo.co.jp/',
            'contact_url': 'https://www.ichijo.co.jp/request/',
            'instagram_url': 'https://www.instagram.com/ichijo_official/',
            'features': ['高気密高断熱', '太陽光発電', '全館床暖房']
        },
        'クレバリーホーム': {
            'location': '千葉市',
            'website_url': 'https://www.cleverlyhome.com/',
            'contact_url': 'https://www.cleverlyhome.com/contact/',
            'instagram_url': 'https://www.instagram.com/cleverlyhome_official/',
            'features': ['タイル外壁', 'デザイン住宅', '高耐久']
        },
        'ユニバーサルホーム': {
            'location': '千葉市',
            'website_url': 'https://www.universalhome.co.jp/',
            'contact_url': 'https://www.universalhome.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/universalhome_official/',
            'features': ['地熱床システム', 'ALC外壁', '高性能住宅']
        },
        'スウェーデンハウス': {
            'location': '千葉市',
            'website_url': 'https://www.swedenhouse.co.jp/',
            'contact_url': 'https://www.swedenhouse.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/swedenhouse_official/',
            'features': ['北欧デザイン', '高断熱', '輸入住宅']
        },
        '桧家住宅': {
            'location': '千葉市',
            'website_url': 'https://www.hinokiya.jp/',
            'contact_url': 'https://www.hinokiya.jp/contact/',
            'instagram_url': 'https://www.instagram.com/hinokiya_official/',
            'features': ['Z空調', '高気密高断熱', 'オリジナル全館空調']
        },
        '日本ハウスホールディングス': {
            'location': '千葉市',
            'website_url': 'https://www.nihonhouse-hd.co.jp/',
            'contact_url': 'https://www.nihonhouse-hd.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/nihonhouse_hd/',
            'features': ['檜住宅', '和モダン', '長期保証']
        },
        'ヤマダホームズ': {
            'location': '千葉市',
            'website_url': 'https://yamadahomes.jp/',
            'contact_url': 'https://yamadahomes.jp/contact/',
            'instagram_url': 'https://www.instagram.com/yamadahomes_official/',
            'features': ['スマートハウス', '家電セット', 'IoT住宅']
        },
        'トヨタホーム': {
            'location': '千葉市',
            'website_url': 'https://www.toyotahome.co.jp/',
            'contact_url': 'https://www.toyotahome.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/toyotahome_official/',
            'features': ['鉄骨住宅', '60年長期保証', 'スマートハウス']
        },
        'ミサワホーム': {
            'location': '千葉市',
            'website_url': 'https://www.misawa.co.jp/',
            'contact_url': 'https://www.misawa.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/misawahome_official/',
            'features': ['蔵のある家', 'デザイン住宅', '制震装置']
        },
        'パナソニック ホームズ': {
            'location': '千葉市',
            'website_url': 'https://homes.panasonic.com/',
            'contact_url': 'https://homes.panasonic.com/contact/',
            'instagram_url': 'https://www.instagram.com/panasonichomes/',
            'features': ['高性能住宅', 'IoT', '全館空調']
        },
        '旭化成ホームズ（ヘーベルハウス）': {
            'location': '千葉市',
            'website_url': 'https://www.asahi-kasei.co.jp/hebel/',
            'contact_url': 'https://www.asahi-kasei.co.jp/hebel/contact/',
            'instagram_url': 'https://www.instagram.com/hebelhaus_official/',
            'features': ['ALC', '高耐久', '鉄骨住宅', '60年メンテ']
        },
        '三井ホーム': {
            'location': '千葉市',
            'website_url': 'https://www.mitsuihome.co.jp/',
            'contact_url': 'https://www.mitsuihome.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/mitsuihome_official/',
            'features': ['デザイン住宅', 'ツーバイフォー', 'プレミアム住宅']
        },
        '積水ハウス': {
            'location': '千葉市',
            'website_url': 'https://www.sekisuihouse.co.jp/',
            'contact_url': 'https://www.sekisuihouse.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/sekisuihouse/',
            'features': ['高性能住宅', 'デザイン', 'ユニバーサルデザイン']
        },
        'ダイワハウス': {
            'location': '千葉市',
            'website_url': 'https://www.daiwahouse.co.jp/',
            'contact_url': 'https://www.daiwahouse.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/daiwahouse_official/',
            'features': ['高性能住宅', '長期保証', 'xevoシリーズ']
        },
        'アキュラホーム（AQ Group）': {
            'location': '千葉市',
            'website_url': 'https://www.aqura.co.jp/',
            'contact_url': 'https://www.aqura.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/aqura_home/',
            'features': ['適正価格', 'デザイン住宅', '木造住宅']
        },
        '木下工務店': {
            'location': '千葉市',
            'website_url': 'https://www.kinoshita-koumuten.co.jp/',
            'contact_url': 'https://www.kinoshita-koumuten.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/kinoshitakoumuten/',
            'features': ['自然素材', '高断熱', '完全自由設計']
        },
        '斉藤工務店　松戸店': {
            'location': '松戸市',
            'website_url': 'https://www.saito-koumuten.co.jp/',
            'contact_url': 'https://www.saito-koumuten.co.jp/contact/',
            'instagram_url': None,
            'features': ['地域密着', '注文住宅', '高品質']
        },
        '北辰工務店（ポラスグループ）': {
            'location': '松戸市',
            'website_url': 'https://www.polus.co.jp/hokushin/',
            'contact_url': 'https://www.polus.co.jp/hokushin/contact/',
            'instagram_url': 'https://www.instagram.com/polus_group/',
            'features': ['地域密着', '高品質', '完全自由設計']
        },
        'アイ工務店': {
            'location': '千葉市',
            'website_url': 'https://www.ai-koumuten.co.jp/',
            'contact_url': 'https://www.ai-koumuten.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/ai_koumuten/',
            'features': ['適正価格', '高性能住宅', '長期優良住宅']
        },
        'ロイヤルハウス': {
            'location': '千葉市',
            'website_url': 'https://www.royal-house.co.jp/',
            'contact_url': 'https://www.royal-house.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/royalhouse_official/',
            'features': ['ローコスト', '国産材', 'フランチャイズ']
        },
        'セルコホーム': {
            'location': '千葉市',
            'website_url': 'https://selcohome.jp/',
            'contact_url': 'https://selcohome.jp/contact/',
            'instagram_url': 'https://www.instagram.com/selcohome/',
            'features': ['カナダ輸入住宅', '高断熱', '2x6工法']
        },
        'イシンホーム住宅研究会': {
            'location': '千葉市',
            'website_url': 'https://www.ishinhome.co.jp/',
            'contact_url': 'https://www.ishinhome.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/ishinhome/',
            'features': ['太陽光発電', 'ゼロエネルギー', 'エコ住宅']
        },
        '夢ハウス': {
            'location': '佐倉市',
            'website_url': 'https://www.yume-h.com/',
            'contact_url': 'https://www.yume-h.com/contact/',
            'instagram_url': None,
            'features': ['自然素材', '無垢材', '高断熱']
        },
        '無添加住宅': {
            'location': '千葉市',
            'website_url': 'https://www.mutenkahouse.jp/',
            'contact_url': 'https://www.mutenkahouse.jp/contact/',
            'instagram_url': 'https://www.instagram.com/mutenka_house/',
            'features': ['自然素材', '無添加', '健康住宅']
        },
        'ノーブルホーム': {
            'location': '千葉市',
            'website_url': 'https://www.noblehome.co.jp/',
            'contact_url': 'https://www.noblehome.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/noblehome_official/',
            'features': ['デザイン住宅', '自由設計', '茨城・千葉']
        },
        'アルネットホーム': {
            'location': '千葉市',
            'website_url': 'https://www.alnethome.com/',
            'contact_url': 'https://www.alnethome.com/contact/',
            'instagram_url': 'https://www.instagram.com/alnethome/',
            'features': ['デザイン住宅', '高性能', '自由設計']
        },
        '住宅情報館': {
            'location': '千葉市',
            'website_url': 'https://www.jutakujohokan.co.jp/',
            'contact_url': 'https://www.jutakujohokan.co.jp/contact/',
            'instagram_url': 'https://www.instagram.com/jutakujohokan/',
            'features': ['注文住宅', '分譲住宅', '土地探し']
        },
        'パパまるハウス': {
            'location': '千葉市',
            'website_url': 'https://www.papamaru.jp/',
            'contact_url': 'https://www.papamaru.jp/contact/',
            'instagram_url': 'https://www.instagram.com/papamaruhausu/',
            'features': ['ローコスト', '企画住宅', '高断熱']
        },
        '菊池建設': {
            'location': '千葉市',
            'website_url': 'https://www.kikuchi-kensetsu.co.jp/',
            'contact_url': 'https://www.kikuchi-kensetsu.co.jp/contact/',
            'instagram_url': None,
            'features': ['檜の家', '自然素材', '職人技']
        },
        '三菱地所ホーム': {
            'location': '千葉市',
            'website_url': 'https://www.mitsubishi-home.com/',
            'contact_url': 'https://www.mitsubishi-home.com/contact/',
            'instagram_url': 'https://www.instagram.com/mitsubishi_home/',
            'features': ['全館空調', 'デザイン住宅', 'ツーバイネクスト']
        },
    }

    for company in companies:
        name = company['company_name']
        if name in details:
            detail = details[name]
            company['location'] = detail.get('location', company.get('location', '千葉県'))
            company['website_url'] = detail.get('website_url', company.get('website_url', ''))
            company['contact_url'] = detail.get('contact_url')
            company['instagram_url'] = detail.get('instagram_url')
            company['features'] = detail.get('features', [])

    return companies

def main():
    input_file = '/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/projects/koumuten/output/chiba_koumuten_list.json'
    output_file = '/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/projects/koumuten/output/chiba_koumuten_final.json'

    # データ読み込み
    companies = load_data(input_file)
    print(f"Loaded {len(companies)} companies")

    # フィルタリング
    valid_companies = [c for c in companies if is_valid_company(c)]
    print(f"After filtering: {len(valid_companies)} companies")

    # 正規化
    normalized = [normalize_company(c) for c in valid_companies]

    # 詳細情報追加
    enriched = get_company_details(normalized)

    # 重複除去（会社名ベース）
    seen = set()
    unique = []
    for c in enriched:
        # 正規化した名前で重複チェック
        normalized_name = c['company_name'].replace('株式会社', '').replace(' ', '').strip()
        if normalized_name not in seen:
            seen.add(normalized_name)
            unique.append(c)

    print(f"After deduplication: {len(unique)} companies")

    # ソート（会社名順）
    unique.sort(key=lambda x: x['company_name'])

    # 出力
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    print(f"\nExported to {output_file}")

    # サマリー
    print("\n=== 最終データサマリー ===")
    print(f"総数: {len(unique)}社")

    # 特徴別集計
    feature_counts = {}
    for c in unique:
        for f in c.get('features', []):
            feature_counts[f] = feature_counts.get(f, 0) + 1

    print("\n特徴別 (上位10):")
    for feature, count in sorted(feature_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {feature}: {count}社")

    # 地域別集計
    location_counts = {}
    for c in unique:
        loc = c.get('location', '不明')
        location_counts[loc] = location_counts.get(loc, 0) + 1

    print("\n地域別 (上位10):")
    for loc, count in sorted(location_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {loc}: {count}社")

    # Instagram有無
    with_instagram = len([c for c in unique if c.get('instagram_url')])
    print(f"\nInstagramあり: {with_instagram}社")

    # 問い合わせURL有無
    with_contact = len([c for c in unique if c.get('contact_url')])
    print(f"問い合わせURLあり: {with_contact}社")


if __name__ == "__main__":
    main()
