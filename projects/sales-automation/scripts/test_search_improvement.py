#!/usr/bin/env python3
"""
検索改善のテストスクリプト
改善前後の取得率を比較
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.browser import get_container_ports
from lib.search import search_duckduckgo, generate_query_variations

def test_search_strategies():
    """検索戦略の比較テスト"""
    ports = get_container_ports()
    if not ports:
        print("エラー: コンテナが起動していません")
        return
    
    port = ports[0]
    print(f"テストポート: {port}")
    print("=" * 60)
    
    query = "東京 システム開発会社"
    
    # === テスト1: 従来の方法（site:なし） ===
    print("\n【テスト1】従来の方法（site:オペレータなし）")
    print(f"クエリ: {query}")
    results_old = search_duckduckgo(port, query, max_results=20, scroll_pages=2, use_site_operator=False)
    print(f"取得結果: {len(results_old)} 件")
    
    # co.jp ドメインの割合を計算
    cojp_count = sum(1 for r in results_old if '.co.jp' in r.get('url', ''))
    if results_old:
        print(f"co.jpドメイン率: {cojp_count}/{len(results_old)} ({cojp_count/len(results_old)*100:.1f}%)")
    
    for i, r in enumerate(results_old[:5], 1):
        url = r.get('url', '')
        domain = url.split('/')[2] if '/' in url else url
        print(f"  {i}. {domain[:40]}")
    
    # === テスト2: 改善版（site:co.jp） ===
    print("\n【テスト2】改善版（site:co.jp オペレータ使用）")
    print(f"クエリ: site:co.jp {query}")
    results_new = search_duckduckgo(port, query, max_results=20, scroll_pages=2, use_site_operator=True)
    print(f"取得結果: {len(results_new)} 件")
    
    cojp_count_new = sum(1 for r in results_new if '.co.jp' in r.get('url', ''))
    if results_new:
        print(f"co.jpドメイン率: {cojp_count_new}/{len(results_new)} ({cojp_count_new/len(results_new)*100:.1f}%)")
    
    for i, r in enumerate(results_new[:5], 1):
        url = r.get('url', '')
        domain = url.split('/')[2] if '/' in url else url
        print(f"  {i}. {domain[:40]}")
    
    # === テスト3: 改善版クエリバリエーション ===
    print("\n【テスト3】改善版クエリバリエーション")
    variations = generate_query_variations(query)
    print(f"生成されたバリエーション ({len(variations)}個):")
    for i, v in enumerate(variations, 1):
        print(f"  {i}. {v}")
    
    # 各バリエーションでテスト
    print("\n【テスト4】バリエーション + site:co.jp の組み合わせ")
    total_results = []
    seen_domains = set()
    
    for v in variations[:3]:  # 上位3つでテスト
        print(f"\n  クエリ: {v}")
        results = search_duckduckgo(port, v, max_results=15, scroll_pages=2, use_site_operator=True)
        print(f"    結果: {len(results)} 件")
        
        for r in results:
            url = r.get('url', '')
            if '/' in url:
                domain = url.split('/')[2]
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    total_results.append(r)
    
    print(f"\n総ユニークドメイン数: {len(seen_domains)}")
    print("\nサンプル（最初の10件）:")
    for i, r in enumerate(total_results[:10], 1):
        url = r.get('url', '')
        domain = url.split('/')[2] if '/' in url else url
        title = r.get('title', '')[:30]
        print(f"  {i}. {domain} - {title}")


if __name__ == "__main__":
    test_search_strategies()
