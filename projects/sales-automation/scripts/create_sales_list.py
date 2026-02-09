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
from urllib.parse import urlparse

# ライブラリのインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.browser import get_container_ports, browser_navigate, browser_evaluate
from lib.search import search_duckduckgo, determine_search_context, generate_query_variations
from lib.extractor import extract_company_info
from lib.contact_finder import find_contact_form_url
from lib.normalizer import deduplicate_companies, validate_company_data
from lib.output import generate_json_output, generate_csv_output, generate_markdown_report


def collect_search_results(ports, query, max_results=50, num_variations=10, scroll_pages=5):
    """
    複数コンテナで並列検索してURLを収集（クエリバリエーション対応）

    Args:
        ports: ブラウザコンテナのポートリスト
        query: 検索クエリ
        max_results: 最大収集件数
        num_variations: クエリバリエーション数
        scroll_pages: 各検索でのスクロール回数

    Returns:
        [{title, url, snippet}, ...]
    """
    # クエリバリエーションを生成
    query_variations = generate_query_variations(query, num_variations)
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
                futures[executor.submit(search_duckduckgo, port, q, max_results=20, scroll_pages=scroll_pages)] = port

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


def get_domain(url: str) -> str:
    """URLからドメインを抽出（www.を除去）"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ''


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
                futures[executor.submit(find_contact_form_url, port, base_url)] = company

            for future in as_completed(futures):
                company = futures[future]
                try:
                    contact_url = future.result()
                    
                    # ドメイン検証: 会社URLとフォームURLのドメインが一致するか
                    if contact_url:
                        company_domain = get_domain(company.get('company_url', ''))
                        form_domain = get_domain(contact_url)
                        
                        # 完全一致 or サブドメイン（form.company.com等）を許可
                        if company_domain and form_domain:
                            if form_domain != company_domain and not form_domain.endswith('.' + company_domain):
                                print(f"    ⚠ {company.get('company_name', '')[:30]} - ドメイン不一致（{form_domain} != {company_domain}）")
                                contact_url = ''  # ドメイン不一致なので無効化
                    
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
    parser.add_argument('--query-variations', type=int, default=10, help='検索クエリのバリエーション数（デフォルト: 10）')
    parser.add_argument('--scroll-pages', type=int, default=5, help='各検索でのスクロール回数（デフォルト: 5）')
    parser.add_argument('--skip-contact-forms', action='store_true', help='問い合わせフォーム検出をスキップ')
    parser.add_argument('--additional-queries', '-q', nargs='+', default=[], 
                        help='追加の検索クエリ（例: -q "システム開発 東京" "Web制作会社"）')
    args = parser.parse_args()

    # メインクエリ + 追加クエリを結合
    all_queries = [args.query] + args.additional_queries
    
    # 業種コンテキスト判定して関連クエリを自動追加（LLMで生成）
    search_context = determine_search_context(args.query)
    if len(all_queries) == 1:
        # 地域を抽出
        regions = ['東京', '大阪', '名古屋', '福岡', '横浜', '札幌', '仙台', '神戸', '京都', '広島']
        found_region = None
        for region in regions:
            if region in args.query:
                found_region = region
                break
        
        if found_region:
            # LLMで関連クエリを生成
            try:
                from lib.llm_helper import generate_base_queries
                additional_queries = generate_base_queries(args.query, max_queries=8)
                for q in additional_queries:
                    if q not in all_queries:
                        all_queries.append(q)
                print(f"[LLM] {len(all_queries)}個のベースクエリを使用")
            except Exception as e:
                print(f"[LLM] フォールバック: {e}")
                # フォールバック: ITコンテキストの場合のみハードコード
                if search_context == 'IT':
                    additional_it_queries = [
                        f"{found_region} システム開発会社",
                        f"{found_region} Web制作会社",
                        f"{found_region} アプリ開発",
                        f"{found_region} ソフトウェア開発",
                        f"{found_region} IT企業",
                        f"{found_region} DX支援",
                        f"{found_region} AI開発",
                        f"{found_region} クラウド開発",
                    ]
                    for q in additional_it_queries:
                        if q not in all_queries:
                            all_queries.append(q)
                    print(f"ITコンテキスト検出: {len(all_queries)}個のクエリを使用")

    print("=" * 60)
    print("営業リスト作成スクリプト")
    print("=" * 60)
    print(f"検索クエリ: {', '.join(all_queries)}")
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

    # ステップ1: 検索結果を収集（複数クエリ対応）
    print("[1/4] 検索結果を収集中...")
    all_search_results = []
    seen_urls = set()
    
    for query_idx, query in enumerate(all_queries):
        print(f"  クエリ {query_idx + 1}/{len(all_queries)}: {query}")
        results = collect_search_results(
            ports, query,
            max_results=args.max_companies * 2 // len(all_queries),
            num_variations=args.query_variations,
            scroll_pages=args.scroll_pages
        )
        # 重複排除しながら追加
        for r in results:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_search_results.append(r)
    
    search_results = all_search_results
    print(f"  合計検索結果: {len(search_results)}件のユニークURL")
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
    if not args.skip_contact_forms:
        print("[4/4] 問い合わせフォーム検出中...")
        companies = collect_contact_forms(ports, companies)
        detected_count = sum(1 for c in companies if c.get('contact_form_url', ''))
        print(f"  検出完了: {detected_count}/{len(companies)}社 ({detected_count/len(companies)*100:.1f}%)")
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
