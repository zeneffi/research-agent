#!/usr/bin/env python3
"""
フォーム検出テスト（高速版）

使い方:
  python3 test_form_detection_fast.py [--max N] [--debug]
"""
import sys
import os
import json
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.browser import get_container_ports
from lib.contact_finder_fast import find_contact_form_url_fast


def main():
    parser = argparse.ArgumentParser(description='フォーム検出テスト（高速版）')
    parser.add_argument('--max', type=int, default=10, help='テストする最大企業数')
    parser.add_argument('--debug', action='store_true', help='デバッグ出力')
    parser.add_argument('--input', type=str, help='入力JSONファイル')
    args = parser.parse_args()

    # 最新のリストを読み込み
    output_dir = '/private/tmp/research-agent/projects/sales-automation/output'
    
    if args.input:
        input_file = args.input
    else:
        json_files = sorted([f for f in os.listdir(output_dir) if f.startswith('sales_list') and f.endswith('.json')])
        if not json_files:
            print("エラー: 営業リストが見つかりません")
            return
        input_file = os.path.join(output_dir, json_files[-1])

    print(f"リストファイル: {input_file}")
    
    with open(input_file) as f:
        data = json.load(f)
    
    companies = data.get('companies', [])
    print(f"企業数: {len(companies)}")
    
    ports = get_container_ports()
    if not ports:
        print("エラー: コンテナが起動していません")
        print("  docker compose up -d を実行してください")
        return
    
    port = ports[0]
    print(f"使用ポート: {port}")
    print("=" * 60)
    
    # テスト対象
    test_companies = companies[:args.max]
    
    results = {
        'total': len(test_companies),
        'detected': 0,
        'methods': {},
        'details': []
    }
    
    start_time = time.time()
    
    for i, company in enumerate(test_companies, 1):
        name = company.get('company_name', 'Unknown')[:30]
        url = company.get('company_url', '')
        
        print(f"\n[{i}/{len(test_companies)}] {name}")
        print(f"  URL: {url[:50]}")
        
        company_start = time.time()
        form_url, method = find_contact_form_url_fast(port, url, debug=args.debug)
        elapsed = time.time() - company_start
        
        if form_url:
            results['detected'] += 1
            results['methods'][method] = results['methods'].get(method, 0) + 1
            print(f"  ✓ 検出: {method} ({elapsed:.1f}秒)")
            print(f"    → {form_url[:60]}")
        else:
            print(f"  ✗ 未検出 ({elapsed:.1f}秒)")
        
        results['details'].append({
            'company_name': name,
            'company_url': url,
            'form_url': form_url,
            'method': method,
            'elapsed': round(elapsed, 1)
        })

    total_time = time.time() - start_time
    avg_time = total_time / len(test_companies) if test_companies else 0
    
    # サマリー
    print("\n" + "=" * 60)
    print("【サマリー】")
    print(f"  テスト企業数: {results['total']}")
    print(f"  検出成功: {results['detected']}/{results['total']} ({results['detected']/results['total']*100:.1f}%)")
    print(f"  合計時間: {total_time:.1f}秒 (平均 {avg_time:.1f}秒/社)")
    print("\n  検出方法内訳:")
    for method, count in sorted(results['methods'].items(), key=lambda x: -x[1]):
        print(f"    - {method}: {count}社")
    print("=" * 60)
    
    # 結果保存
    result_file = os.path.join(output_dir, 'form_test_result_fast.json')
    with open(result_file, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n結果保存: {result_file}")


if __name__ == "__main__":
    main()
