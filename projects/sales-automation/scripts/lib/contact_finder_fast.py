"""
問い合わせフォーム検出機能（高速版）

改善点:
- 順序逆転: まずトップページからリンク検出（最速）
- パス削減: 40→10パス
- 待機短縮: 2秒→1秒
- iframe対応追加
"""
import json
import time
from urllib.parse import urljoin, urlparse
from typing import Optional, Tuple
from .browser import browser_navigate, browser_evaluate


# よくある問い合わせフォームパス（削減版: 10パス）
COMMON_CONTACT_PATHS = [
    '/contact',
    '/contact/',
    '/inquiry',
    '/inquiry/',
    '/contact.html',
    '/toiawase',
    '/form',
    '/お問い合わせ',
    '/contact-us',
    '/otoiawase',
]


def find_contact_form_url_fast(port: int, base_url: str, debug: bool = False) -> Tuple[str, str]:
    """
    問い合わせフォームURLを高速検出

    Args:
        port: ブラウザコンテナのポート
        base_url: 企業サイトのベースURL
        debug: デバッグ出力

    Returns:
        (form_url, detection_method)
    """
    def log(msg):
        if debug:
            print(f"  [DEBUG] {msg}")

    # === 方法1: トップページからリンクを探す（最速）===
    if not browser_navigate(port, base_url, timeout=15):
        return '', 'navigation_failed'

    time.sleep(1)  # 短縮

    # 問い合わせリンク + フォーム検出を一括実行
    combined_script = """(function() {
        const result = {
            contact_link: '',
            has_form_on_page: false,
            iframe_src: ''
        };
        
        // ベースドメイン取得
        const baseDomain = window.location.hostname.replace(/^www\\./, '');
        
        // パターン
        const contactPatterns = [
            /お問い?合わ?せ/i,
            /contact/i,
            /inquiry/i,
            /ご相談/i,
            /資料請求/i,
            /CONTACT/i,
        ];
        
        // 1. リンクを探す
        const links = document.querySelectorAll('a');
        for (const link of links) {
            const text = link.textContent.trim();
            const href = link.href;
            
            for (const pattern of contactPatterns) {
                if (pattern.test(text) || pattern.test(href)) {
                    try {
                        const linkDomain = new URL(href).hostname.replace(/^www\\./, '');
                        // 同一ドメイン or サブドメイン
                        if (linkDomain === baseDomain || 
                            linkDomain.endsWith('.' + baseDomain) ||
                            baseDomain.endsWith('.' + linkDomain)) {
                            result.contact_link = href;
                            break;
                        }
                    } catch(e) {}
                }
            }
            if (result.contact_link) break;
        }
        
        // 2. 現在ページにフォームがあるか
        const form = document.querySelector('form');
        const submitBtn = document.querySelector('button[type="submit"], input[type="submit"]');
        const emailInput = document.querySelector('input[type="email"]');
        const textarea = document.querySelector('textarea');
        
        if (form && submitBtn) {
            result.has_form_on_page = true;
        } else if (emailInput && textarea) {
            result.has_form_on_page = true;
        }
        
        // 3. iframe内にフォームがあるか（src確認のみ）
        const iframes = document.querySelectorAll('iframe');
        for (const iframe of iframes) {
            const src = iframe.src || '';
            if (src && (src.includes('form') || src.includes('contact') || src.includes('inquiry'))) {
                result.iframe_src = src;
                break;
            }
        }
        
        return JSON.stringify(result);
    })()"""

    result = browser_evaluate(port, combined_script, timeout=10)
    
    if result:
        try:
            data = json.loads(result)
            
            # トップページにフォームがあればそのまま返す
            if data.get('has_form_on_page'):
                log(f"Method 1 (top page form): {base_url}")
                return base_url, 'top_page_form'
            
            # contactリンクが見つかった
            contact_link = data.get('contact_link', '')
            if contact_link:
                # contactページに遷移してフォーム確認
                if browser_navigate(port, contact_link, timeout=10):
                    time.sleep(1)
                    
                    form_check = """(function() {
                        const form = document.querySelector('form');
                        const submitBtn = document.querySelector('button[type="submit"], input[type="submit"]');
                        const emailInput = document.querySelector('input[type="email"], input[name*="mail"], input[name*="email"]');
                        const textarea = document.querySelector('textarea');
                        const textInputs = document.querySelectorAll('input[type="text"]');
                        
                        // iframe内フォームもチェック（大文字小文字区別なし）
                        const iframes = document.querySelectorAll('iframe');
                        let iframeSrc = '';
                        for (const iframe of iframes) {
                            const src = (iframe.src || '').toLowerCase();
                            if (src && (src.includes('form') || src.includes('mail') || src.includes('contact') || src.includes('inquiry'))) {
                                iframeSrc = iframe.src;
                                break;
                            }
                        }
                        
                        // iframeが1つでもあればsrcを取得（フォールバック）
                        if (!iframeSrc && iframes.length > 0 && iframes[0].src) {
                            iframeSrc = iframes[0].src;
                        }
                        
                        return JSON.stringify({
                            has_form: !!(form && submitBtn) || !!(emailInput && (textarea || textInputs.length > 1)),
                            iframe_src: iframeSrc
                        });
                    })()"""
                    
                    form_result = browser_evaluate(port, form_check, timeout=5)
                    if form_result:
                        try:
                            form_data = json.loads(form_result)
                            if form_data.get('has_form'):
                                log(f"Method 1 (contact link form): {contact_link}")
                                return contact_link, 'contact_link_form'
                            
                            # iframe内にフォームがある場合
                            iframe_src = form_data.get('iframe_src', '')
                            if iframe_src:
                                # iframeを確認
                                if browser_navigate(port, iframe_src, timeout=10):
                                    time.sleep(1)
                                    iframe_form_check = browser_evaluate(port, 
                                        "!!document.querySelector('form, input[type=email], textarea')", timeout=5)
                                    # True/true両方対応
                                    if iframe_form_check and str(iframe_form_check).lower() == 'true':
                                        log(f"Method 1 (iframe form): {contact_link}")
                                        return contact_link, 'iframe_form'
                            
                            # iframe srcがなくても、ページ内の全iframeをチェック
                            all_iframe_script = """(function() {
                                const iframes = document.querySelectorAll('iframe');
                                for (const iframe of iframes) {
                                    if (iframe.src && iframe.src.startsWith('http')) {
                                        return iframe.src;
                                    }
                                }
                                return '';
                            })()"""
                            any_iframe = browser_evaluate(port, all_iframe_script, timeout=5)
                            if any_iframe and any_iframe.startswith('http'):
                                if browser_navigate(port, any_iframe, timeout=10):
                                    time.sleep(1)
                                    iframe_form_check = browser_evaluate(port, 
                                        "!!document.querySelector('form, input[type=email], textarea')", timeout=5)
                                    if iframe_form_check and str(iframe_form_check).lower() == 'true':
                                        log(f"Method 1 (any iframe form): {contact_link}")
                                        return contact_link, 'iframe_form'
                        except:
                            pass
            
        except json.JSONDecodeError:
            pass

    # === 方法2: よくあるパスを試す（削減版）===
    for path in COMMON_CONTACT_PATHS:
        candidate_url = urljoin(base_url, path)
        if browser_navigate(port, candidate_url, timeout=8):
            time.sleep(1)
            
            check_script = """(function() {
                const form = document.querySelector('form');
                const submitBtn = document.querySelector('button[type="submit"], input[type="submit"]');
                const emailInput = document.querySelector('input[type="email"], input[name*="mail"]');
                const textarea = document.querySelector('textarea');
                
                // フォーム構造があるか
                if (form && submitBtn) return true;
                if (emailInput && textarea && submitBtn) return true;
                
                // タイトルやURLに contact/問い合わせ が含まれ、入力欄がある
                const title = document.title.toLowerCase();
                const hasContactTitle = title.includes('contact') || title.includes('問い合わせ');
                const hasInputs = emailInput || textarea;
                if (hasContactTitle && hasInputs) return true;
                
                return false;
            })()"""
            
            result = browser_evaluate(port, check_script, timeout=5)
            if result and str(result).lower() == 'true':
                log(f"Method 2 (common path): {candidate_url}")
                return candidate_url, 'common_path_form'

    # === 方法3: 外部フォームサービス ===
    if browser_navigate(port, base_url, timeout=10):
        external_script = """(function() {
            const services = ['forms.gle', 'typeform.com', 'formrun.com', 'tayori.com', 'form.run'];
            
            const links = document.querySelectorAll('a');
            for (const link of links) {
                for (const service of services) {
                    if (link.href.includes(service)) return link.href;
                }
            }
            
            const iframes = document.querySelectorAll('iframe');
            for (const iframe of iframes) {
                for (const service of services) {
                    if (iframe.src && iframe.src.includes(service)) return iframe.src;
                }
            }
            
            return '';
        })()"""
        
        result = browser_evaluate(port, external_script, timeout=5)
        if result and result.startswith('http'):
            log(f"Method 3 (external form): {result}")
            return result, 'external_form'

    log(f"Form not found for {base_url}")
    return '', 'not_found'


def has_form_on_page(port: int, url: str) -> bool:
    """
    指定URLにフォームがあるか確認（送信前チェック用）
    """
    if not browser_navigate(port, url, timeout=10):
        return False
    
    time.sleep(1)
    
    check_script = """(function() {
        const form = document.querySelector('form');
        const submitBtn = document.querySelector('button[type="submit"], input[type="submit"]');
        return !!(form && submitBtn);
    })()"""
    
    result = browser_evaluate(port, check_script, timeout=5)
    return result and str(result).lower() == 'true'
