#!/usr/bin/env python3
"""
フォーム検出テストスクリプト

営業リストから問い合わせフォームの検出のみを実行（送信は行わない）
"""
import sys
import os
import json
import argparse
from datetime import datetime

# ライブラリのインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.browser import get_container_ports, browser_navigate
from lib.form_handler import detect_form_fields, detect_captcha


def load_sales_list(file_path: str) -> list:
    """営業リスト読み込み"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, dict) and 'companies' in data:
            return data['companies']
        elif isinstance(data, list):
            return data
        else:
            return []


def test_form_detection(port: int, company: dict) -> dict:
    """1企業のフォーム検出テスト"""
    result = {
        'company_name': company.get('company_name', 'Unknown'),
        'url': company.get('contact_form_url', ''),
        'timestamp': datetime.now().isoformat(),
        'has_captcha': False,
        'form_fields': {},
        'status': 'pending',
        'error': None
    }

    # フォームURLチェック
    form_url = company.get('contact_form_url', '')
    if not form_url:
        result['status'] = 'skipped'
        result['error'] = 'No contact form URL'
        return result

    # ページにナビゲート
    if not browser_navigate(port, form_url, timeout=30):
        result['status'] = 'failed'
        result['error'] = 'Navigation failed'
        return result

    # CAPTCHA検出
    try:
        has_captcha = detect_captcha(port)
        result['has_captcha'] = has_captcha
        if has_captcha:
            result['status'] = 'has_captcha'
    except Exception as e:
        result['error'] = f'CAPTCHA detection error: {e}'

    # フォーム項目検出
    try:
        fields = detect_form_fields(port, form_url)
        if fields:
            result['form_fields'] = fields
            result['status'] = 'detected' if not has_captcha else 'has_captcha'
        else:
            result['status'] = 'not_detected'
            result['error'] = 'Form fields not found'
    except Exception as e:
        result['status'] = 'failed'
        result['error'] = f'Form detection error: {e}'

    return result


def generate_report(results: list, output_path: str):
    """検出結果レポート生成"""
    # 統計計算
    total = len(results)
    detected = sum(1 for r in results if r['status'] == 'detected')
    has_captcha = sum(1 for r in results if r['status'] == 'has_captcha')
    not_detected = sum(1 for r in results if r['status'] == 'not_detected')
    failed = sum(1 for r in results if r['status'] == 'failed')
    skipped = sum(1 for r in results if r['status'] == 'skipped')

    # Markdownレポート生成
    md = f"""# フォーム検出テスト結果

実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

## サマリー

| 項目 | 件数 | 割合 |
|-----|------|------|
| **総数** | {total}社 | 100.0% |
| **検出成功** | {detected}社 | {detected/total*100 if total > 0 else 0:.1f}% |
| **CAPTCHA検出** | {has_captcha}社 | {has_captcha/total*100 if total > 0 else 0:.1f}% |
| **検出失敗** | {not_detected}社 | {not_detected/total*100 if total > 0 else 0:.1f}% |
| **エラー** | {failed}社 | {failed/total*100 if total > 0 else 0:.1f}% |
| **スキップ** | {skipped}社 | {skipped/total*100 if total > 0 else 0:.1f}% |

---

## 検出成功

"""

    # 検出成功した企業
    detected_results = [r for r in results if r['status'] == 'detected']
    if detected_results:
        for i, r in enumerate(detected_results, 1):
            fields = ', '.join(r['form_fields'].keys())
            md += f"""### {i}. {r['company_name']}

- **URL**: {r['url']}
- **検出フィールド**: {fields}
- **CAPTCHA**: なし

"""
    else:
        md += "検出成功した企業はありません。\n\n"

    md += """---

## CAPTCHA検出

"""
    # CAPTCHA検出した企業
    captcha_results = [r for r in results if r['status'] == 'has_captcha']
    if captcha_results:
        for i, r in enumerate(captcha_results, 1):
            fields = ', '.join(r['form_fields'].keys()) if r['form_fields'] else 'フォーム検出済み'
            md += f"""### {i}. {r['company_name']}

- **URL**: {r['url']}
- **検出フィールド**: {fields}
- **CAPTCHA**: あり（送信時は自動スキップされます）

"""
    else:
        md += "CAPTCHA検出された企業はありません。\n\n"

    md += """---

## 検出失敗

"""
    # 検出失敗した企業
    failed_results = [r for r in results if r['status'] in ['not_detected', 'failed']]
    if failed_results:
        for i, r in enumerate(failed_results, 1):
            md += f"""### {i}. {r['company_name']}

- **URL**: {r['url']}
- **理由**: {r['error'] or '不明'}

"""
    else:
        md += "検出失敗した企業はありません。\n\n"

    md += """---

## 注意事項

- このテストは検出のみを実行し、実際の送信は行っていません
- CAPTCHA検出された企業は、本番送信時に自動スキップされます
- 検出失敗した企業は、フォーム構造が特殊な可能性があります

"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(description='フォーム検出テストスクリプト')
    parser.add_argument('list_file', help='営業リスト（JSON）')
    parser.add_argument('--max-tests', type=int, default=10, help='最大テスト件数（デフォルト: 10）')
    args = parser.parse_args()

    print("=" * 60)
    print("フォーム検出テスト")
    print("=" * 60)
    print()

    # 1. 営業リスト読み込み
    print("[1/4] 営業リスト読み込み中...")
    companies = load_sales_list(args.list_file)

    # フォームURLがある企業のみ抽出
    companies_with_form = [c for c in companies if c.get('contact_form_url')]
    print(f"  総数: {len(companies)}社")
    print(f"  フォームURL有り: {len(companies_with_form)}社")
    print()

    # 2. ブラウザコンテナ取得
    print("[2/4] ブラウザコンテナ確認中...")
    ports = get_container_ports()
    if not ports:
        print("エラー: Dockerコンテナが起動していません")
        print("docker compose up -d で起動してください")
        return
    print(f"  利用可能: {len(ports)}個")
    print()

    # 3. フォーム検出テスト
    print(f"[3/4] フォーム検出テスト中（最大{args.max_tests}社）...")
    results = []
    port = ports[0]  # 1コンテナのみ使用

    for i, company in enumerate(companies_with_form[:args.max_tests], 1):
        company_name = company.get('company_name', 'Unknown')[:40]
        print(f"  [{i}/{min(args.max_tests, len(companies_with_form))}] {company_name}...", end=' ')

        result = test_form_detection(port, company)
        results.append(result)

        # ステータス表示
        status_icon = {
            'detected': '✓',
            'has_captcha': '⚠',
            'not_detected': '✗',
            'failed': '✗',
            'skipped': '⊘'
        }.get(result['status'], '?')

        print(f"{status_icon} {result['status']}")

    print()

    # 4. レポート生成
    print("[4/4] レポート生成中...")
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)

    report_path = os.path.join(output_dir, f'form_detection_test_{datetime.now().strftime("%Y%m%d_%H%M")}.md')
    generate_report(results, report_path)
    print(f"  レポート: {report_path}")
    print()

    # サマリー表示
    detected = sum(1 for r in results if r['status'] == 'detected')
    has_captcha = sum(1 for r in results if r['status'] == 'has_captcha')

    print("=" * 60)
    print("完了!")
    print("=" * 60)
    print(f"  検出成功: {detected}社")
    print(f"  CAPTCHA検出: {has_captcha}社")
    print(f"  検出失敗: {len(results) - detected - has_captcha}社")
    print()
    print("⚠️  注意: このテストは検出のみで、実際の送信は行っていません")


if __name__ == "__main__":
    main()
