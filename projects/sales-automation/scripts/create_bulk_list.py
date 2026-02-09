#!/usr/bin/env python3
"""
複数クエリで大量の営業リストを作成
100社目標
"""
import argparse
import os
import sys
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.browser import get_container_ports
from lib.search import search_duckduckgo, generate_query_variations
from lib.extractor import extract_company_info
from lib.normalizer import deduplicate_companies, validate_company_data
from lib.output import generate_json_output, generate_csv_output, generate_markdown_report


def search_multiple_queries(ports, queries, max_per_query=30):
    """複数クエリで並列検索"""
    all_results = []
    seen_domains = set()
    
    for base_query in queries:
        print(f"\n=== 検索: {base_query} ===")
        variations = generate_query_variations(base_query)
        
        with ThreadPoolExecutor(max_workers=min(len(ports), len(variations))) as executor:
            futures = {}
            for i, q in enumerate(variations):
                port = ports[i % len(ports)]
                futures[executor.submit(
                    search_duckduckgo, port, q, 
                    max_results=20, scroll_pages=4, use_site_operator=True
                )] = q
            
            for future in as_completed(futures):
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
                    if new_count > 0:
                        print(f"  +{new_count} 件")
                except Exception as e:
                    query_str = futures.get(future, "不明なクエリ")
                    print(f"  ! クエリでエラー: {e}")
        
        if len(all_results) >= max_per_query * len(queries):
            break
    
    print(f"\n総検索結果: {len(all_results)} 件のユニークURL")
    return all_results


def extract_companies_parallel(ports, search_results, search_context, max_companies):
    """並列で企業情報を抽出"""
    companies = []
    batch_size = len(ports)
    
    for batch_start in range(0, len(search_results), batch_size):
        if len(companies) >= max_companies:
            break
        
        batch = search_results[batch_start:batch_start + batch_size]
        
        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = {}
            for i, result in enumerate(batch):
                port = ports[i % len(ports)]
                url = result.get('url', '')
                futures[executor.submit(extract_company_info, port, url, search_context)] = result
            
            for future in as_completed(futures):
                result = futures[future]
                try:
                    company = future.result()
                    if company and validate_company_data(company):
                        company['source_query'] = result.get('title', '')
                        companies.append(company)
                        print(f"  [{len(companies)}] {company.get('company_name', 'Unknown')[:40]}")
                except Exception as e:
                    url = result.get('url', 'Unknown URL')
                    print(f"  ! URL '{url}' の情報抽出中にエラー: {e}")
        
        time.sleep(0.3)
    
    return companies


def main():
    parser = argparse.ArgumentParser(description='複数クエリで大量営業リスト作成')
    parser.add_argument('--max-companies', type=int, default=100, help='目標企業数')
    args = parser.parse_args()
    
    # 複数の検索クエリ
    queries = [
        "東京 システム開発会社",
        "東京 Web制作会社",
        "東京 アプリ開発",
        "東京 IT企業",
        "東京 ソフトウェア開発",
    ]
    
    print("=" * 60)
    print("複数クエリ営業リスト作成")
    print("=" * 60)
    print(f"検索クエリ数: {len(queries)}")
    print(f"目標企業数: {args.max_companies}")
    
    ports = get_container_ports()
    if not ports:
        print("エラー: コンテナが起動していません")
        return
    
    print(f"利用可能コンテナ: {len(ports)}個")
    
    # 検索
    print("\n[1/3] 検索中...")
    search_results = search_multiple_queries(ports, queries, max_per_query=50)
    
    # 企業情報抽出
    print(f"\n[2/3] 企業情報を収集中（目標: {args.max_companies}社）...")
    companies = extract_companies_parallel(ports, search_results, 'IT', args.max_companies)
    print(f"  収集完了: {len(companies)}社")
    
    # 重複排除
    print("\n[3/3] 重複排除中...")
    companies = deduplicate_companies(companies)
    print(f"  重複排除後: {len(companies)}社")
    
    # 出力
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    json_path = os.path.join(output_dir, f"bulk_sales_list_{timestamp}.json")
    csv_path = os.path.join(output_dir, f"bulk_sales_list_{timestamp}.csv")
    md_path = os.path.join(output_dir, f"bulk_sales_list_{timestamp}.md")
    
    generate_json_output(companies, json_path, 'IT')
    generate_csv_output(companies, csv_path, 'IT')
    generate_markdown_report(companies, md_path, 'IT')
    
    print(f"\n{'=' * 60}")
    print("完了!")
    print(f"{'=' * 60}")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV: {csv_path}")
    print(f"  - 収集企業数: {len(companies)}社")


if __name__ == "__main__":
    main()
