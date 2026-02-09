#!/usr/bin/env python3
"""
大量検索テスト - 15コンテナ並列 × 複数クエリ
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concurrent.futures import ThreadPoolExecutor, as_completed
from lib.browser import get_container_ports
from lib.search import search_duckduckgo, generate_query_variations

def test_bulk_search(base_query: str):
    """複数クエリで大量検索テスト"""
    ports = get_container_ports()
    print(f"利用可能コンテナ: {len(ports)}個")
    print(f"ベースクエリ: {base_query}")
    print("=" * 60)
    
    # クエリバリエーション生成
    variations = generate_query_variations(base_query)
    print(f"\nクエリバリエーション ({len(variations)}個):")
    for i, v in enumerate(variations, 1):
        print(f"  {i}. {v}")
    
    # 結果格納
    all_results = []
    seen_domains = set()
    
    # 各バリエーションを並列実行
    print(f"\n検索開始...")
    
    with ThreadPoolExecutor(max_workers=min(len(ports), len(variations))) as executor:
        futures = {}
        for i, query in enumerate(variations):
            port = ports[i % len(ports)]
            futures[executor.submit(
                search_duckduckgo, port, query, 
                max_results=20, scroll_pages=4, use_site_operator=True
            )] = query
        
        for future in as_completed(futures):
            query = futures[future]
            try:
                results = future.result()
                new_count = 0
                for r in results:
                    url = r.get('url', '')
                    if '/' in url:
                        domain = url.split('/')[2]
                        if domain not in seen_domains:
                            seen_domains.add(domain)
                            all_results.append(r)
                            new_count += 1
                print(f"  ✓ [{query[:30]}...] → +{new_count}件 (累計: {len(all_results)})")
            except Exception as e:
                print(f"  ✗ [{query[:30]}...] → エラー: {e}")
    
    print("\n" + "=" * 60)
    print(f"総ユニーク企業数: {len(all_results)}")
    print("=" * 60)
    
    print("\n取得企業一覧:")
    for i, r in enumerate(all_results, 1):
        url = r.get('url', '')
        domain = url.split('/')[2] if '/' in url else url
        title = r.get('title', '')[:40]
        print(f"  {i:3}. {domain[:35]:35} {title}")
    
    return all_results


if __name__ == "__main__":
    # テストクエリ
    queries = [
        "東京 システム開発会社",
        "大阪 Web制作会社", 
        "名古屋 IT企業",
    ]
    
    for q in queries:
        print("\n" + "#" * 70)
        print(f"# テスト: {q}")
        print("#" * 70)
        results = test_bulk_search(q)
        print(f"\n→ 結果: {len(results)}社\n")
