"""
問い合わせフォーム検出機能
"""
import json
import re
import time
from urllib.parse import urljoin, urlparse
from typing import Optional
from .browser import browser_navigate, browser_evaluate


# よくある問い合わせフォームパス
COMMON_CONTACT_PATHS = [
    # 英語系
    '/contact',
    '/contact/',
    '/contact-us',
    '/contactus',
    '/inquiry',
    '/inquiry/',
    '/form',
    '/form/',
    '/support',
    '/support/',
    '/contact.html',
    '/inquiry.html',
    '/contact.php',
    # 日本語系
    '/toiawase',
    '/otoiawase',
    '/お問い合わせ',
    '/お問合せ',
    '/問い合わせ',
    '/問合せ',
    '/お問い合わせ/',
    '/contact/form',
    '/inquiry/form',
    # その他よくあるパターン
    '/info',
    '/info/',
    '/ask',
    '/request',
]


def find_contact_form_url(port: int, base_url: str) -> str:
    """
    問い合わせフォームURLを4段階で検出

    Args:
        port: ブラウザコンテナのポート
        base_url: 企業サイトのベースURL

    Returns:
        問い合わせフォームURL（見つからない場合は空文字列）
    """
    # === 方法1: よくあるパスを直接試す（キーワード + HTML構造を同時チェック）===
    for path in COMMON_CONTACT_PATHS:
        candidate_url = urljoin(base_url, path)
        if browser_navigate(port, candidate_url, timeout=10):
            time.sleep(2)  # JavaScript読み込み待機
            # キーワード検証とHTML構造検証を同時に実行（効率化）
            combined_script = """(function() {
                const title = document.title.toLowerCase();
                const body = document.body.innerText.toLowerCase();

                // キーワード検証
                const hasContactKeyword = title.includes('contact') || title.includes('問い合わせ') ||
                                         title.includes('お問い合わせ') || title.includes('inquiry') ||
                                         body.includes('お問い合わせ') || body.includes('contact') ||
                                         body.includes('問い合わせ') || body.includes('form') ||
                                         body.includes('ご相談') || body.includes('資料請求');

                // HTML構造検証
                const hasForm = !!document.querySelector('form');
                const hasEmailInput = !!document.querySelector('input[type="email"]');
                const hasSubmitButton = !!document.querySelector('button[type="submit"], input[type="submit"]');
                const hasTextarea = !!document.querySelector('textarea');
                const hasFormStructure = (hasForm && hasSubmitButton) || (hasEmailInput && hasTextarea && hasSubmitButton);

                // いずれかがtrueなら問い合わせフォームと判定
                return hasContactKeyword || hasFormStructure;
            })()"""
            result = browser_evaluate(port, combined_script, timeout=10)
            if result == 'true':
                print(f"  [DEBUG] Method 1 (common paths): {candidate_url}")
                return candidate_url

    # === 方法2: トップページからリンクを探す ===
    if not browser_navigate(port, base_url):
        return ''

    time.sleep(5)  # JavaScript動的生成リンク対応のため待機延長

    # 問い合わせリンクを検出するスクリプト
    script = """(function() {
        const links = document.querySelectorAll('a');
        const contactPatterns = [
            /お問い?合わ?せ/i,
            /contact/i,
            /inquiry/i,
            /ご相談/i,
            /資料請求/i,
            /お見積/i,
            /無料相談/i,
        ];

        // ベースドメイン取得（www.を除去、.co.jp等のTLD対応）
        const baseDomain = window.location.hostname.replace(/^www\./, '');

        for (const link of links) {
            const text = link.textContent.trim();
            const href = link.href;

            // パターンマッチ
            for (const pattern of contactPatterns) {
                if (pattern.test(text) || pattern.test(href)) {
                    // 同一ドメイン or サブドメインなら許可（例: form.company.com）
                    try {
                        const linkDomain = new URL(href).hostname;
                        if (linkDomain === baseDomain || linkDomain.endsWith('.' + baseDomain)) {
                            return href;
                        }
                    } catch(e) {
                        // URL解析エラーは無視
                    }
                }
            }
        }

        return '';
    })()"""

    result = browser_evaluate(port, script)
    if result and result != '':
        # JSON文字列の場合はパース
        try:
            parsed = json.loads(result)
            if isinstance(parsed, str) and parsed:
                print(f"  [DEBUG] Method 2 (link search): {parsed}")
                return parsed
        except json.JSONDecodeError:
            pass
        # 文字列として直接返す
        if isinstance(result, str) and result.startswith('http'):
            print(f"  [DEBUG] Method 2 (link search): {result}")
            return result

    # === 方法3: フッターやヘッダーから検出 ===
    footer_script = """(function() {
        const footer = document.querySelector('footer, .footer, #footer');
        const header = document.querySelector('header, .header, #header');
        const nav = document.querySelector('nav, .nav, #nav, .navigation');

        const searchIn = [footer, header, nav].filter(x => x);

        // ベースドメイン取得（www.を除去、.co.jp等のTLD対応）
        const baseDomain = window.location.hostname.replace(/^www\./, '');

        for (const section of searchIn) {
            if (!section) continue;

            const links = section.querySelectorAll('a');
            for (const link of links) {
                const text = link.textContent.toLowerCase();
                const href = link.href;

                if ((text.includes('contact') || text.includes('問い合わせ') || text.includes('お問い合わせ') ||
                     text.includes('お問合せ') || text.includes('ご相談') || text.includes('資料請求'))) {
                    // 同一ドメイン or サブドメインなら許可
                    try {
                        const linkDomain = new URL(href).hostname;
                        if (linkDomain === baseDomain || linkDomain.endsWith('.' + baseDomain)) {
                            return href;
                        }
                    } catch(e) {
                        // URL解析エラーは無視
                    }
                }
            }
        }

        return '';
    })()"""

    result = browser_evaluate(port, footer_script)
    if result and result != '':
        try:
            parsed = json.loads(result)
            if isinstance(parsed, str) and parsed:
                print(f"  [DEBUG] Method 3 (footer/header): {parsed}")
                return parsed
        except json.JSONDecodeError:
            pass
        if isinstance(result, str) and result.startswith('http'):
            print(f"  [DEBUG] Method 3 (footer/header): {result}")
            return result

    # 見つからなかった
    print(f"  [DEBUG] Form URL not found for {base_url}")
    return ''


def is_valid_contact_url(url: str) -> bool:
    """
    問い合わせフォームURLとして妥当かチェック

    Args:
        url: チェック対象URL

    Returns:
        True: 妥当, False: 不適切
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)

        # 問い合わせフォームらしいパス
        path_lower = parsed.path.lower()
        contact_indicators = ['contact', 'inquiry', 'toiawase', 'form', 'お問い合わせ']

        if any(indicator in path_lower for indicator in contact_indicators):
            return True

        return False
    except:
        return False
