"""
フォーム検出・入力・送信機能

auto_contact.py からの移植版（Playwright → browser_evaluate 変換）
"""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from .browser import browser_navigate, browser_evaluate


def detect_form_fields(port: int, url: str) -> Optional[Dict[str, str]]:
    """
    フォーム項目を自動検出

    移植元: koumuten/auto_contact.py 行69-75

    Args:
        port: ブラウザコンテナのポート
        url: フォームページURL

    Returns:
        {'company': 'company-name', 'name': 'your-name', 'email': 'email',
         'phone': 'tel', 'message': 'message'}
        または None（フォームが見つからない場合）
    """
    # auto_contact.py のセレクタパターンをそのまま使用
    form_selectors = {
        "name": ['input[name*="name"]', 'input[name*="氏名"]', 'input[placeholder*="お名前"]'],
        "email": ['input[type="email"]', 'input[name*="mail"]', 'input[name*="メール"]'],
        "phone": ['input[name*="tel"]', 'input[name*="phone"]', 'input[name*="電話"]'],
        "company": ['input[name*="company"]', 'input[name*="会社"]', 'input[name*="法人"]'],
        "message": ['textarea', 'textarea[name*="message"]', 'textarea[name*="内容"]']
    }

    script = """
    (function() {
        const selectors = """ + json.dumps(form_selectors) + """;
        const result = {};
        for (const [field, patterns] of Object.entries(selectors)) {
            for (const pattern of patterns) {
                const el = document.querySelector(pattern);
                if (el && el.offsetParent !== null) {  // is_visible相当
                    result[field] = el.name || el.id || pattern;
                    break;
                }
            }
        }
        return JSON.stringify(result);
    })()
    """

    result_str = browser_evaluate(port, script)
    if not result_str:
        return None

    try:
        result = json.loads(result_str)
        # 最低限messageフィールドが必要
        if not result.get('message'):
            return None
        return result
    except:
        return None


def detect_captcha(port: int) -> bool:
    """
    CAPTCHA存在を検出（reCAPTCHA/hCaptcha）

    Args:
        port: ブラウザコンテナのポート

    Returns:
        True if CAPTCHA detected, False otherwise
    """
    script = """
    (function() {
        return !!(
            document.querySelector('.g-recaptcha') ||
            document.querySelector('.h-captcha') ||
            document.querySelector('[data-sitekey]') ||
            document.querySelector('iframe[src*="recaptcha"]') ||
            document.querySelector('iframe[src*="hcaptcha"]')
        );
    })()
    """

    result = browser_evaluate(port, script)
    return result == 'true'


def fill_and_submit_form(port: int, form_fields: Dict[str, str],
                         form_data: Dict[str, str],
                         timeout: int = 120) -> Dict[str, Any]:
    """
    フォーム入力・送信

    移植元: koumuten/auto_contact.py 行86-134
    変換: Playwright fill() → JavaScript .value =
    変換: Playwright click() → JavaScript .click()

    Args:
        port: ブラウザコンテナのポート
        form_fields: detect_form_fields() で取得したフィールド情報
        form_data: 入力データ {'company': ..., 'name': ..., 'email': ..., 'phone': ..., 'message': ...}
        timeout: タイムアウト（秒）

    Returns:
        {'status': 'success'|'failed'|'skipped', 'error': str, 'screenshot': str}
    """
    # JSONエスケープ処理
    fields_json = json.dumps(form_fields)
    data_json = json.dumps(form_data)

    script = f"""
    (function() {{
        try {{
            // 各フィールドに値を設定（auto_contact.py 行90-94の変換）
            const fields = {fields_json};
            const data = {data_json};

            for (const [field, selector] of Object.entries(fields)) {{
                // name属性またはid属性で要素を検索
                const el = document.querySelector('[name="' + selector + '"]') ||
                           document.querySelector('#' + selector) ||
                           document.querySelector(selector);

                if (el && data[field] !== undefined) {{
                    el.value = data[field];
                    // イベント発火（バリデーション対応）
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}

            // 送信ボタン検出（auto_contact.py 行110-127の変換）
            const submitSelectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("送信")',
                'button:has-text("確認")',
                'input[value*="送信"]',
                'button:contains("送信")',
                'input[value*="確認"]'
            ];

            for (const sel of submitSelectors) {{
                // :has-text, :contains は標準セレクタでないため、代替検索
                let btn;
                if (sel.includes(':has-text') || sel.includes(':contains')) {{
                    const buttons = document.querySelectorAll('button');
                    for (const b of buttons) {{
                        const buttonText = b.textContent.trim();
                        if (buttonText === '送信' || buttonText === '確認' || buttonText === '送信する' || buttonText === '確認する') {{
                            btn = b;
                            break;
                        }}
                    }}
                }} else {{
                    btn = document.querySelector(sel);
                }}

                if (btn && btn.offsetParent !== null) {{
                    btn.click();
                    return JSON.stringify({{status: 'success'}});
                }}
            }}

            return JSON.stringify({{status: 'failed', error: '送信ボタンが見つかりません'}});
        }} catch(e) {{
            return JSON.stringify({{status: 'failed', error: e.message}});
        }}
    }})()
    """

    result_str = browser_evaluate(port, script, timeout=timeout)
    if not result_str:
        return {'status': 'failed', 'error': 'No response from browser', 'screenshot': None}

    try:
        result = json.loads(result_str)
        result['screenshot'] = None
        return result
    except:
        return {'status': 'failed', 'error': 'Failed to parse response', 'screenshot': None}


def take_screenshot(port: int, output_path: str) -> bool:
    """
    エラー時のスクリーンショット保存

    移植元: koumuten/auto_contact.py 行104-107

    Note: ブラウザAPIにスクリーンショット機能がないため、
    現在は未実装。将来的にAPIが追加された場合に実装可能。

    Args:
        port: ブラウザコンテナのポート
        output_path: 保存先パス

    Returns:
        True if successful, False otherwise
    """
    # TODO: ブラウザAPIの/browser/screenshotエンドポイントを使用（あれば）
    # 現時点では browser.py にスクリーンショット機能がないため未実装
    return False
