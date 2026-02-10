#!/usr/bin/env python
"""
フォーム営業スクリプト

営業リストから自動的に問い合わせフォームを検出・入力・送信
移植元: create_sales_list.py の構造をそのまま使用
"""
import argparse
import os
import sys
import json
import csv
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ライブラリのインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.browser import get_container_ports, browser_navigate
from lib.form_handler import detect_form_fields, detect_captcha, fill_and_submit_form
from lib.message_generator import generate_sales_message
from lib.rate_limiter import RateLimiter
from lib.duplicate_checker import mark_as_sent


def load_sales_list(file_path: str) -> list:
    """
    営業リスト読み込み（JSON/CSV自動判定）

    移植元: koumuten/auto_contact.py 行29-32 のload_companies()パターン

    Args:
        file_path: 営業リストのファイルパス

    Returns:
        企業情報のリスト
    """
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # JSONの構造に応じて処理
            if isinstance(data, dict) and 'companies' in data:
                return data['companies']
            elif isinstance(data, list):
                return data
            else:
                return []

    elif file_ext == '.csv':
        companies = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append(row)
        return companies

    else:
        raise ValueError(f"Unsupported file format: {file_ext}")


def load_config(config_path: str) -> dict:
    """
    設定ファイルを読み込み、検証する

    Args:
        config_path: 設定ファイルパス

    Returns:
        設定辞書

    Raises:
        ValueError: 設定が不正な場合
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    sender_info = config['form_sales']['sender_info']

    # デフォルト値チェック
    if sender_info['company_name'] == '株式会社Example':
        print("=" * 60)
        print("⚠️  エラー: 送信者情報がデフォルト値のままです")
        print("=" * 60)
        print("config/sales_automation.json を編集して、以下を設定してください：")
        print("  - company_name: 実際の会社名")
        print("  - contact_name: 実際の担当者名")
        print("  - email: 実際のメールアドレス")
        print("  - phone: 実際の電話番号")
        print("=" * 60)
        raise ValueError("Sender info not configured. Please edit config/sales_automation.json")

    # メールアドレス形式検証
    email = sender_info['email']
    if '@' not in email or '.' not in email.split('@')[-1]:
        print(f"⚠️  エラー: メールアドレスが不正です: {email}")
        raise ValueError("Invalid email format")

    # example.comドメインの警告
    if 'example.com' in email:
        print("⚠️  警告: example.comドメインは使用できません")
        raise ValueError("Cannot use example.com domain")

    print(f"✓ 送信者情報: {sender_info['company_name']} / {sender_info['contact_name']}")
    print(f"✓ メール: {sender_info['email']}")

    return config


def send_to_company(port: int, company: dict, sender_info: dict, rate_limiter: RateLimiter, message_config: dict = None) -> dict:
    """
    1企業へのフォーム送信

    新規実装: ただしcreate_sales_list.pyのextract_company_info()と同じ構造

    Args:
        port: ブラウザコンテナのポート
        company: 企業情報
        sender_info: 送信者情報
        rate_limiter: レートリミッター

    Returns:
        送信結果
    """
    # a. 待機（3分間隔）
    rate_limiter.wait_if_needed()

    # b. フォームURLに遷移
    form_url = company.get('contact_form_url', '')
    if not form_url:
        result = {
            'status': 'skipped',
            'reason': 'No contact form URL',
            'error': None,
            'screenshot': None
        }
        log_and_return(rate_limiter, company, form_url, result, '')
        return result

    if not browser_navigate(port, form_url):
        result = {
            'status': 'failed',
            'error': 'Navigation failed',
            'screenshot': None
        }
        log_and_return(rate_limiter, company, form_url, result, '')
        return result

    # c. CAPTCHA検出
    if detect_captcha(port):
        result = {
            'status': 'skipped',
            'reason': 'CAPTCHA detected',
            'error': None,
            'screenshot': None
        }
        log_and_return(rate_limiter, company, form_url, result, '')
        return result

    # d. フォーム項目検出
    fields = detect_form_fields(port, form_url)
    if not fields or not fields.get('message'):
        result = {
            'status': 'skipped',
            'reason': 'Form not detected',
            'error': None,
            'screenshot': None
        }
        log_and_return(rate_limiter, company, form_url, result, '')
        return result

    # e. 営業文生成
    message = generate_sales_message(company, sender_info, message_config)

    # f. フォーム入力・送信
    form_data = {
        'company': sender_info.get('company_name', ''),
        'name': sender_info.get('contact_name', ''),
        'email': sender_info.get('email', ''),
        'phone': sender_info.get('phone', ''),
        'message': message
    }

    result = fill_and_submit_form(port, fields, form_data)

    # g. ログ記録
    log_and_return(rate_limiter, company, form_url, result, message, list(fields.keys()))

    return result


def log_and_return(rate_limiter: RateLimiter, company: dict, form_url: str,
                   result: dict, message: str, fields: list = None):
    """
    ログ記録のヘルパー関数

    Args:
        rate_limiter: レートリミッター
        company: 企業情報
        form_url: フォームURL
        result: 送信結果
        message: 営業メッセージ
        fields: 検出されたフォームフィールド
    """
    log_entry = {
        'company_name': company.get('company_name', 'Unknown'),
        'url': form_url,
        'status': result.get('status', 'unknown'),
        'timestamp': datetime.now().isoformat(),
        'message_preview': message[:50] + '...' if message else '',
        'form_fields_detected': fields if fields else [],
        'error': result.get('error') or result.get('reason'),
        'screenshot': result.get('screenshot')
    }
    rate_limiter.log_send(log_entry)

    # 送信成功時、ドメインを送信済みリストに記録
    if result.get('status') == 'success':
        company_url = company.get('url', form_url)
        mark_as_sent(company_url)


def generate_report(log_path: str, output_path: str):
    """
    送信結果レポート生成

    移植元: output.py generate_markdown_report() のパターン

    Args:
        log_path: send_log.json のパス
        output_path: レポート出力パス
    """
    with open(log_path, 'r', encoding='utf-8') as f:
        log_data = json.load(f)

    summary = log_data['summary']
    entries = log_data['entries']

    # output.py 行66-140 のMarkdown生成パターンを流用
    md = f"""# フォーム営業 送信結果レポート

実行日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}

## サマリー

| 指標 | 値 |
|-----|-----|
| **総数** | {summary['total']}社 |
| **成功** | {summary['success']}社 |
| **失敗** | {summary['failed']}社 |
| **スキップ** | {summary['skipped']}社 |
| **成功率** | {(summary['success'] / summary['total'] * 100) if summary['total'] > 0 else 0:.1f}% |

---

## 送信成功

"""

    # 成功した企業
    success_entries = [e for e in entries if e.get('status') == 'success']
    if success_entries:
        for i, entry in enumerate(success_entries, 1):
            md += f"""### {i}. {entry.get('company_name', 'Unknown')}

- **URL**: {entry.get('url', '不明')}
- **送信日時**: {entry.get('timestamp', '不明')}
- **検出フィールド**: {', '.join(entry.get('form_fields_detected', []))}
- **メッセージ**: {entry.get('message_preview', '')}

"""
    else:
        md += "送信成功した企業はありません。\n\n"

    md += """---

## 送信失敗

"""

    # 失敗した企業
    failed_entries = [e for e in entries if e.get('status') == 'failed']
    if failed_entries:
        for i, entry in enumerate(failed_entries, 1):
            md += f"""### {i}. {entry.get('company_name', 'Unknown')}

- **URL**: {entry.get('url', '不明')}
- **エラー**: {entry.get('error', '不明')}
- **日時**: {entry.get('timestamp', '不明')}

"""
    else:
        md += "送信失敗した企業はありません。\n\n"

    md += """---

## スキップ

"""

    # スキップした企業
    skipped_entries = [e for e in entries if e.get('status') == 'skipped']
    if skipped_entries:
        for i, entry in enumerate(skipped_entries, 1):
            md += f"""### {i}. {entry.get('company_name', 'Unknown')}

- **URL**: {entry.get('url', '不明')}
- **理由**: {entry.get('error', '不明')}
- **日時**: {entry.get('timestamp', '不明')}

"""
    else:
        md += "スキップした企業はありません。\n\n"

    md += """---

## 注意事項

- CAPTCHA検出: reCAPTCHA/hCaptchaが検出された場合、送信をスキップしています
- レート制限: 3分間隔、1日100件の制限を適用しています
- 営業文: 企業タイプ（スタートアップ/IT/製造業/汎用）に応じて自動生成しています

"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)


def main():
    """
    メイン処理

    移植元: create_sales_list.py main() 行146-226
    """
    parser = argparse.ArgumentParser(description='フォーム営業スクリプト')
    parser.add_argument('list_file', help='営業リスト（JSON/CSV）')
    parser.add_argument('--max-sends', type=int, default=100, help='最大送信件数（デフォルト: 100）')
    parser.add_argument('--config', default='config/sales_automation.json', help='設定ファイルパス')
    args = parser.parse_args()

    print("=" * 60)
    print("フォーム営業スクリプト")
    print("=" * 60)
    print()

    # 1. 営業リスト読み込み
    print("[1/5] 営業リスト読み込み中...")
    companies = load_sales_list(args.list_file)
    print(f"  読み込み完了: {len(companies)}社")
    print()

    # 2. 設定読み込み
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), args.config)
    config = load_config(config_path)
    sender_info = config['form_sales']['sender_info']
    message_config = config['form_sales'].get('message_generation', {})
    print(f"送信者情報: {sender_info['company_name']} / {sender_info['contact_name']}")
    print()

    # 3. レートリミッター初期化
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')
    os.makedirs(output_dir, exist_ok=True)

    log_path = os.path.join(output_dir, 'send_log.json')
    rate_limiter = RateLimiter(
        log_path,
        daily_limit=config['form_sales']['rate_limit']['daily_limit'],
        interval_seconds=config['form_sales']['rate_limit']['interval_seconds']
    )

    # 4. コンテナポート取得
    print("[2/5] ブラウザコンテナ確認中...")
    max_containers = config['form_sales'].get('max_containers', 5)
    ports = get_container_ports()[:max_containers]
    if not ports:
        print("エラー: Dockerコンテナが起動していません")
        print("docker compose up -d で起動してください")
        return

    print(f"  利用可能なブラウザコンテナ: {len(ports)}個")
    print()

    # 5. 並列送信（ThreadPoolExecutor使用）
    print("[3/5] フォーム送信中...")
    print(f"  レート制限: {config['form_sales']['rate_limit']['interval_seconds']}秒間隔、1日{config['form_sales']['rate_limit']['daily_limit']}件")
    print()

    # create_sales_list.py 行84-105 のcollect_company_info()パターンを完全流用
    sent_count = 0
    with ThreadPoolExecutor(max_workers=len(ports)) as executor:
        futures = {}
        for i, company in enumerate(companies[:args.max_sends]):
            # レート制限チェック
            can_send, reason = rate_limiter.can_send()
            if not can_send:
                print(f"  送信停止: {reason}")
                break

            port = ports[i % len(ports)]
            futures[executor.submit(send_to_company, port, company,
                                   sender_info, rate_limiter, message_config)] = company
            sent_count += 1

        # 結果収集（create_sales_list.py 行91-102と同じパターン）
        for future in as_completed(futures):
            company = futures[future]
            try:
                result = future.result()
                status = result.get('status', 'unknown')
                status_symbol = {
                    'success': '✓',
                    'failed': '✗',
                    'skipped': '⊘'
                }.get(status, '?')

                company_name = company.get('company_name', 'Unknown')[:40]
                print(f"  {status_symbol} {company_name} - {status}")

            except Exception as e:
                print(f"  ✗ {company.get('company_name', 'Unknown')[:40]} - エラー: {e}")

    print()

    # 6. レポート生成
    print("[4/5] レポート生成中...")
    md_path = os.path.join(output_dir, 'send_report.md')
    generate_report(log_path, md_path)
    print("  レポート生成完了")
    print()

    # 7. サマリー表示
    print("[5/5] 完了サマリー")
    summary = rate_limiter.get_summary()
    print(f"  - 総数: {summary['total']}社")
    print(f"  - 成功: {summary['success']}社")
    print(f"  - 失敗: {summary['failed']}社")
    print(f"  - スキップ: {summary['skipped']}社")

    print(f"\n{'=' * 60}")
    print("完了!")
    print(f"{'=' * 60}")
    print(f"  - 送信ログ: {log_path}")
    print(f"  - レポート: {md_path}")


if __name__ == "__main__":
    main()
