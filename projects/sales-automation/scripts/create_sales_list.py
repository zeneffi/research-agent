#!/usr/bin/env python
"""
営業リスト作成スクリプト
DuckDuckGo検索で企業情報を自動収集（15コンテナ並列）
"""
import argparse
import os
import sys
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ライブラリのインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.browser import get_container_ports, browser_navigate, browser_evaluate
from lib.search import search_duckduckgo, determine_search_context, generate_query_variations
from lib.extractor import extract_company_info
from lib.contact_finder import find_contact_form_url
from lib.normalizer import deduplicate_companies, validate_company_data
from lib.output import generate_json_output, generate_csv_output, generate_markdown_report


def collect_search_results(ports, query, max_results=50):
    """
    複数コンテナで並列検索してURLを収集（クエリバリエーション対応）

    Args:
        ports: ブラウザコンテナのポートリスト
        query: 検索クエリ
        max_results: 最大収集件数

    Returns:
        [{title, url, snippet}, ...]
    """
    # クエリバリエーションを生成
    query_variations = generate_query_variations(query)
    print(f"  検索クエリ: {query}")
    print(f"  バリエーション: {len(query_variations)}個")

    all_results = []
    seen_urls = set()

    # 各バリエーションで検索
    for q_idx, q in enumerate(query_variations):
        if len(all_results) >= max_results:
            break

        print(f"    [{q_idx + 1}/{len(query_variations)}] {q}")

        # コンテナを分割して並列検索
        ports_per_query = max(1, len(ports) // len(query_variations))
        query_ports = ports[q_idx * ports_per_query:(q_idx + 1) * ports_per_query]
        if not query_ports:
            query_ports = [ports[q_idx % len(ports)]]

        with ThreadPoolExecutor(max_workers=len(query_ports)) as executor:
            futures = {}
            for port in query_ports:
                # スクロールで追加結果も取得
                # site:co.jpで企業サイトに限定（まとめサイト除外に効果大）
                futures[executor.submit(search_duckduckgo, port, q, max_results=20, scroll_pages=3, use_site_operator=True)] = port

            for future in as_completed(futures):
                port = futures[future]
                try:
                    results = future.result()
                    for r in results:
                        url = r.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)
                except Exception as e:
                    print(f"      ポート{port}での検索エラー: {e}")

    print(f"  検索結果: {len(all_results)}件のユニークURL")
    return all_results[:max_results]


def collect_company_info(ports, search_results, search_context, max_companies=100):
    """
    企業情報を並列収集

    Args:
        ports: ブラウザコンテナのポートリスト
        search_results: 検索結果リスト
        search_context: 業種コンテキスト
        max_companies: 最大収集企業数

    Returns:
        企業情報のリスト
    """
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
                        # 検索クエリを記録
                        company['source_query'] = result.get('title', '')
                        companies.append(company)
                        print(f"  [{len(companies)}] {company.get('company_name', 'Unknown')[:40]}")
                except Exception as e:
                    pass

        time.sleep(0.5)

    return companies


def collect_contact_forms(ports, companies):
    """
    問い合わせフォームURLを並列検出

    Args:
        ports: ブラウザコンテナのポートリスト
        companies: 企業情報のリスト

    Returns:
        問い合わせフォームURLを追加した企業リスト
    """
    batch_size = len(ports)

    for batch_start in range(0, len(companies), batch_size):
        batch = companies[batch_start:batch_start + batch_size]

        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = {}
            for i, company in enumerate(batch):
                port = ports[i % len(ports)]
                base_url = company.get('company_url', '')
                print(f"    → フォーム検出開始: {company.get('company_name', '')[:30]} ({base_url})")
                futures[executor.submit(find_contact_form_url, port, base_url)] = company

            for future in as_completed(futures):
                company = futures[future]
                try:
                    contact_url = future.result()
                    company['contact_form_url'] = contact_url
                    if contact_url:
                        print(f"    ✓ {company.get('company_name', '')[:30]} - フォーム検出")
                except Exception as e:
                    company['contact_form_url'] = ''

        time.sleep(0.5)

    return companies


def main():
    parser = argparse.ArgumentParser(description='営業リスト作成スクリプト')
    parser.add_argument('query', help='検索クエリ（例: "東京 IT企業"）')
    parser.add_argument('--max-companies', type=int, default=100, help='最大収集企業数（デフォルト: 100）')
    parser.add_argument('--skip-contact-forms', action='store_true', help='問い合わせフォーム検出をスキップ')
    args = parser.parse_args()

    print("=" * 60)
    print("営業リスト作成スクリプト")
    print("=" * 60)
    print(f"検索クエリ: {args.query}")
    print(f"目標企業数: {args.max_companies}社")
    print()

    # コンテナポート取得
    ports = get_container_ports()
    if not ports:
        print("エラー: Dockerコンテナが起動していません")
        print("docker compose up -d で起動してください")
        return

    print(f"利用可能なブラウザコンテナ: {len(ports)}個")
    print()

    # 業種コンテキスト判定
    search_context = determine_search_context(args.query)
    print(f"業種コンテキスト: {search_context}")
    print()

    # ステップ1: 検索結果を収集
    print("[1/4] 検索結果を収集中...")
    search_results = collect_search_results(ports, args.query, max_results=args.max_companies * 2)
    print()

    # ステップ2: 企業情報を収集
    print(f"[2/4] 企業情報を収集中（目標: {args.max_companies}社）...")
    companies = collect_company_info(ports, search_results, search_context, args.max_companies)
    print(f"  収集完了: {len(companies)}社")
    print()

    # ステップ3: 重複排除
    print("[3/4] 重複排除中...")
    companies = deduplicate_companies(companies)
    print(f"  重複排除後: {len(companies)}社")
    print()

    # ステップ4: 問い合わせフォーム検出
    if not companies:
        print("[4/4] 問い合わせフォーム検出: 対象企業が0社のためスキップ")
        print()
    elif not args.skip_contact_forms:
        print("[4/4] 問い合わせフォーム検出中...")
        companies = collect_contact_forms(ports, companies)
        detected_count = sum(1 for c in companies if c.get('contact_form_url', ''))
        pct = (detected_count / len(companies) * 100) if companies else 0.0
        print(f"  検出完了: {detected_count}/{len(companies)}社 ({pct:.1f}%)")
        print()
    else:
        print("[4/4] 問い合わせフォーム検出: スキップ")
        for company in companies:
            company['contact_form_url'] = ''
        print()

    # 出力
    print("レポート生成中...")
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    json_path = os.path.join(output_dir, f"sales_list_{timestamp}.json")
    csv_path = os.path.join(output_dir, f"sales_list_{timestamp}.csv")
    md_path = os.path.join(output_dir, f"sales_list_{timestamp}.md")

    generate_json_output(companies, json_path, search_context)
    generate_csv_output(companies, csv_path, search_context)
    generate_markdown_report(companies, md_path, search_context)

    print(f"\n{'=' * 60}")
    print("完了!")
    print(f"{'=' * 60}")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV: {csv_path}")
    print(f"  - Markdown: {md_path}")
    print(f"  - 収集企業数: {len(companies)}社")


if __name__ == "__main__":
    main()
