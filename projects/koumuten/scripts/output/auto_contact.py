"""
工務店自動問い合わせスクリプト

Playwrightを使用して、収集した工務店リストの問い合わせフォームに
自動でメッセージを送信するスクリプト。

使用方法:
    python auto_contact.py --list companies.json --dry-run
    python auto_contact.py --list companies.json --execute

注意:
    - 初回は必ず --dry-run で動作確認してください
    - 大量送信は相手サーバーに負荷をかけるため、適度な間隔を空けてください
    - 送信内容は事前に確認し、スパム行為にならないよう注意してください
"""

import json
import time
import random
import argparse
import asyncio
from datetime import datetime
from pathlib import Path

# pip install playwright
# playwright install chromium


async def load_companies(file_path: str) -> list:
    """企業リストをJSONから読み込む"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def send_contact_form(page, company: dict, message_template: str, dry_run: bool = True) -> dict:
    """
    問い合わせフォームに送信する

    Args:
        page: Playwrightのページオブジェクト
        company: 企業情報
        message_template: 送信メッセージテンプレート
        dry_run: Trueの場合、実際には送信しない

    Returns:
        送信結果
    """
    result = {
        "company_name": company.get("name", "不明"),
        "url": company.get("contact_url", ""),
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "error": None
    }

    contact_url = company.get("contact_url")
    if not contact_url:
        result["status"] = "skipped"
        result["error"] = "問い合わせURLが未設定"
        return result

    try:
        # ページにアクセス
        await page.goto(contact_url, timeout=30000)
        await page.wait_for_load_state("networkidle")

        # フォーム要素を検出（一般的なパターン）
        # 実際の運用では、各サイトに合わせてカスタマイズが必要
        form_selectors = {
            "name": ['input[name*="name"]', 'input[name*="氏名"]', 'input[placeholder*="お名前"]'],
            "email": ['input[type="email"]', 'input[name*="mail"]', 'input[name*="メール"]'],
            "phone": ['input[name*="tel"]', 'input[name*="phone"]', 'input[name*="電話"]'],
            "company": ['input[name*="company"]', 'input[name*="会社"]', 'input[name*="法人"]'],
            "message": ['textarea', 'textarea[name*="message"]', 'textarea[name*="内容"]']
        }

        # フォームに入力
        form_data = {
            "name": "脇山 宗良",  # カスタマイズしてください
            "email": "example@example.com",  # カスタマイズしてください
            "phone": "000-0000-0000",  # カスタマイズしてください
            "company": "株式会社○○",  # カスタマイズしてください
            "message": message_template.format(company_name=company.get("name", "御社"))
        }

        filled_fields = []
        for field, selectors in form_selectors.items():
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element and await element.is_visible():
                        await element.fill(form_data.get(field, ""))
                        filled_fields.append(field)
                        break
                except Exception:
                    continue

        result["filled_fields"] = filled_fields

        if dry_run:
            result["status"] = "dry_run"
            result["message"] = f"入力フィールド: {filled_fields}"
            # スクリーンショットを保存（確認用）
            screenshot_path = f"projects/koumuten/output/screenshots/{company.get('name', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=screenshot_path)
            result["screenshot"] = screenshot_path
        else:
            # 送信ボタンをクリック
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("送信")',
                'button:has-text("確認")',
                'input[value*="送信"]'
            ]

            submitted = False
            for selector in submit_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        submitted = True
                        break
                except Exception:
                    continue

            if submitted:
                await page.wait_for_load_state("networkidle")
                result["status"] = "sent"
            else:
                result["status"] = "error"
                result["error"] = "送信ボタンが見つかりませんでした"

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)

    return result


async def main(args):
    """メイン処理"""
    from playwright.async_api import async_playwright

    # 企業リストを読み込む
    companies = await load_companies(args.list)
    print(f"読み込んだ企業数: {len(companies)}")

    # メッセージテンプレート
    message_template = """
突然のご連絡失礼いたします。
工務店専門のLP制作を行っております。

{company_name}様のホームページを拝見し、
素晴らしい施工事例を拝見しました。

現在、多くの工務店様が以下のような課題を抱えていらっしゃいます。
・チラシ依存から脱却したい
・問い合わせ数を増やしたい
・見学会の集客を強化したい

私どもは工務店業界に特化したLP制作を行っており、
見学会予約や資料請求の獲得に特化したLPをご提供しています。

もし少しでもご興味がございましたら、
無料のLP診断レポートをお送りさせていただきます。

ご検討いただけますと幸いです。
""".strip()

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headed)
        context = await browser.new_context(
            locale='ja-JP',
            timezone_id='Asia/Tokyo'
        )
        page = await context.new_page()

        for i, company in enumerate(companies):
            if args.limit and i >= args.limit:
                break

            print(f"[{i+1}/{len(companies)}] {company.get('name', '不明')}...")

            result = await send_contact_form(
                page,
                company,
                message_template,
                dry_run=args.dry_run
            )
            results.append(result)

            print(f"  → {result['status']}")

            # 次の送信まで待機（サーバー負荷軽減）
            if i < len(companies) - 1:
                wait_time = random.uniform(args.min_wait, args.max_wait)
                print(f"  {wait_time:.1f}秒待機...")
                await asyncio.sleep(wait_time)

        await browser.close()

    # 結果を保存
    output_path = f"projects/koumuten/output/contact_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n結果を保存しました: {output_path}")

    # サマリー
    sent = sum(1 for r in results if r['status'] == 'sent')
    dry_run_count = sum(1 for r in results if r['status'] == 'dry_run')
    errors = sum(1 for r in results if r['status'] == 'error')
    skipped = sum(1 for r in results if r['status'] == 'skipped')

    print(f"\n=== サマリー ===")
    print(f"送信完了: {sent}")
    print(f"ドライラン: {dry_run_count}")
    print(f"エラー: {errors}")
    print(f"スキップ: {skipped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="工務店自動問い合わせスクリプト")
    parser.add_argument("--list", required=True, help="企業リストのJSONファイルパス")
    parser.add_argument("--dry-run", action="store_true", default=True, help="実際には送信しない（デフォルト: True）")
    parser.add_argument("--execute", action="store_true", help="実際に送信する")
    parser.add_argument("--limit", type=int, help="処理する企業数の上限")
    parser.add_argument("--min-wait", type=float, default=10.0, help="最小待機時間（秒）")
    parser.add_argument("--max-wait", type=float, default=30.0, help="最大待機時間（秒）")
    parser.add_argument("--headed", action="store_true", help="ブラウザを表示する")

    args = parser.parse_args()

    # --executeが指定された場合、dry_runをFalseに
    if args.execute:
        args.dry_run = False

    asyncio.run(main(args))
