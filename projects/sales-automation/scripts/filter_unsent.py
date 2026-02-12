#!/usr/bin/env python3
"""
送信済み企業をフィルタリングするCLIツール

使用例:
    python filter_unsent.py companies.json > unsent.json
    python filter_unsent.py companies.json --stats
"""
import argparse
import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from lib.duplicate_checker import filter_unsent_companies, get_stats, mark_as_sent, get_domain_from_url


def main():
    parser = argparse.ArgumentParser(description='送信済み企業をフィルタリング')
    parser.add_argument('input_file', nargs='?', help='入力JSONファイル')
    parser.add_argument('--stats', action='store_true', help='統計情報を表示')
    parser.add_argument('--mark-sent', help='指定URLを送信済みとしてマーク')
    parser.add_argument('--url-key', default='contact_form_url', help='URLが格納されているキー名')
    args = parser.parse_args()

    # 統計表示
    if args.stats:
        stats = get_stats()
        print(f"送信済みドメイン数: {stats['total_sent']}")
        return

    # 送信済みマーク
    if args.mark_sent:
        mark_as_sent(args.mark_sent)
        domain = get_domain_from_url(args.mark_sent)
        print(f"送信済みとしてマーク: {domain}", file=sys.stderr)
        return

    # フィルタリング
    if not args.input_file:
        parser.print_help()
        sys.exit(1)

    with open(args.input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # {"metadata": ..., "companies": [...]} 形式に対応
    if isinstance(data, dict) and 'companies' in data:
        companies = data['companies']
    elif isinstance(data, list):
        companies = data
    else:
        print("エラー: 不明なJSON形式", file=sys.stderr)
        sys.exit(1)

    original_count = len(companies)
    unsent = filter_unsent_companies(companies, args.url_key)
    filtered_count = original_count - len(unsent)

    print(json.dumps(unsent, ensure_ascii=False, indent=2))
    print(f"# フィルタ結果: {original_count}社 → {len(unsent)}社 ({filtered_count}社除外)", file=sys.stderr)


if __name__ == '__main__':
    main()
