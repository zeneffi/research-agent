"""
フォーム検出・入力・送信機能

auto_contact.py からの移植版（Playwright → browser_evaluate 変換）
v2: 検出精度向上版
"""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime
from pathlib import Path
from .browser import browser_navigate, browser_evaluate


def detect_form_fields(port: int, url: str) -> Optional[Dict[str, str]]:
    """
    フォーム項目を自動検出（v2: 精度向上版）

    検出戦略:
    1. name/id属性のパターンマッチ
    2. placeholder属性のパターンマッチ
    3. aria-label属性のパターンマッチ
    4. label要素からの特定（for属性 or 内包）
    5. 親要素のテキストからの推定

    Args:
        port: ブラウザコンテナのポート
        url: フォームページURL

    Returns:
        {'company': 'selector', 'name': 'selector', 'email': 'selector',
         'phone': 'selector', 'message': 'selector'}
        または None（フォームが見つからない場合）
    """
    script = """
    (function() {
        // フィールド検出パターン（優先度順）
        const patterns = {
            name: {
                namePatterns: ['name', 'fullname', 'your-name', 'yourname', 'contact-name', 'contactname', 'shimei', '氏名', 'namae', '名前'],
                placeholderPatterns: ['お名前', '氏名', '名前', 'ご担当者', '担当者名', 'フルネーム', 'your name', 'full name'],
                labelPatterns: ['お名前', '氏名', '名前', 'ご担当者', '担当者', 'ご芳名', '御名前']
            },
            email: {
                namePatterns: ['email', 'mail', 'e-mail', 'メール', 'メールアドレス'],
                placeholderPatterns: ['メールアドレス', 'メール', 'email', 'e-mail', 'your email', 'ご連絡先'],
                labelPatterns: ['メールアドレス', 'メール', 'E-mail', 'email', 'ご連絡先メール'],
                typePatterns: ['email']
            },
            phone: {
                namePatterns: ['tel', 'phone', 'telephone', 'mobile', '電話', '携帯', 'denwa'],
                placeholderPatterns: ['電話番号', '電話', 'お電話', '携帯番号', 'phone', 'tel', '000-0000-0000', '03-'],
                labelPatterns: ['電話番号', 'お電話番号', '電話', 'TEL', 'ご連絡先電話']
            },
            company: {
                namePatterns: ['company', 'organization', 'corp', 'firm', '会社', '法人', '企業', '所属', 'kaisha', 'shozoku'],
                placeholderPatterns: ['会社名', '法人名', '企業名', 'ご所属', '組織名', 'company', 'organization', '株式会社'],
                labelPatterns: ['会社名', '御社名', '貴社名', '法人名', '企業名', 'ご所属', '組織名']
            },
            message: {
                namePatterns: ['message', 'content', 'body', 'inquiry', 'comment', 'detail', 'description', '内容', '本文', 'naiyou', 'メッセージ', 'お問い合わせ'],
                placeholderPatterns: ['お問い合わせ内容', 'ご質問', 'メッセージ', '内容', '本文', 'ご要望', 'ご相談内容', 'message'],
                labelPatterns: ['お問い合わせ内容', 'ご質問内容', 'メッセージ', '内容', 'ご用件', 'ご要望', 'ご相談']
            }
        };

        const result = {};
        const usedElements = new Set();

        // ヘルパー: 要素が可視かチェック
        function isVisible(el) {
            if (!el) return false;
            const style = window.getComputedStyle(el);
            return el.offsetParent !== null && 
                   style.display !== 'none' && 
                   style.visibility !== 'hidden' &&
                   style.opacity !== '0';
        }

        // ヘルパー: 文字列にパターンが含まれるかチェック（大文字小文字無視）
        function matchesPattern(text, patterns) {
            if (!text) return false;
            const lowerText = text.toLowerCase();
            return patterns.some(p => lowerText.includes(p.toLowerCase()));
        }

        // ヘルパー: ユニークなセレクタを生成
        function getSelector(el) {
            if (el.id) return '#' + el.id;
            if (el.name) return '[name="' + el.name + '"]';
            // フォールバック: タグ + 属性の組み合わせ
            const tag = el.tagName.toLowerCase();
            if (el.type) return tag + '[type="' + el.type + '"]';
            return tag;
        }

        // 戦略1: name/id属性でマッチ
        function findByNameOrId(fieldName, config) {
            const inputs = document.querySelectorAll('input, textarea, select');
            for (const input of inputs) {
                if (usedElements.has(input) || !isVisible(input)) continue;
                const name = (input.name || '').toLowerCase();
                const id = (input.id || '').toLowerCase();
                if (matchesPattern(name, config.namePatterns) || matchesPattern(id, config.namePatterns)) {
                    usedElements.add(input);
                    return getSelector(input);
                }
            }
            return null;
        }

        // 戦略2: type属性でマッチ（email用）
        function findByType(fieldName, config) {
            if (!config.typePatterns) return null;
            for (const type of config.typePatterns) {
                const input = document.querySelector('input[type="' + type + '"]');
                if (input && !usedElements.has(input) && isVisible(input)) {
                    usedElements.add(input);
                    return getSelector(input);
                }
            }
            return null;
        }

        // 戦略3: placeholder属性でマッチ
        function findByPlaceholder(fieldName, config) {
            const inputs = document.querySelectorAll('input, textarea');
            for (const input of inputs) {
                if (usedElements.has(input) || !isVisible(input)) continue;
                const placeholder = input.placeholder || '';
                if (matchesPattern(placeholder, config.placeholderPatterns)) {
                    usedElements.add(input);
                    return getSelector(input);
                }
            }
            return null;
        }

        // 戦略4: label要素から特定
        function findByLabel(fieldName, config) {
            const labels = document.querySelectorAll('label');
            for (const label of labels) {
                const labelText = label.textContent || '';
                if (!matchesPattern(labelText, config.labelPatterns)) continue;

                // for属性から検索
                if (label.htmlFor) {
                    const input = document.getElementById(label.htmlFor);
                    if (input && !usedElements.has(input) && isVisible(input)) {
                        usedElements.add(input);
                        return getSelector(input);
                    }
                }

                // label内の入力要素を検索
                const innerInput = label.querySelector('input, textarea, select');
                if (innerInput && !usedElements.has(innerInput) && isVisible(innerInput)) {
                    usedElements.add(innerInput);
                    return getSelector(innerInput);
                }

                // labelの次の兄弟要素を検索
                let sibling = label.nextElementSibling;
                while (sibling) {
                    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(sibling.tagName)) {
                        if (!usedElements.has(sibling) && isVisible(sibling)) {
                            usedElements.add(sibling);
                            return getSelector(sibling);
                        }
                        break;
                    }
                    // div/span等に包まれてる場合
                    const nestedInput = sibling.querySelector('input, textarea, select');
                    if (nestedInput && !usedElements.has(nestedInput) && isVisible(nestedInput)) {
                        usedElements.add(nestedInput);
                        return getSelector(nestedInput);
                    }
                    sibling = sibling.nextElementSibling;
                }
            }
            return null;
        }

        // 戦略5: aria-label属性でマッチ
        function findByAriaLabel(fieldName, config) {
            const inputs = document.querySelectorAll('input, textarea');
            for (const input of inputs) {
                if (usedElements.has(input) || !isVisible(input)) continue;
                const ariaLabel = input.getAttribute('aria-label') || '';
                if (matchesPattern(ariaLabel, config.labelPatterns)) {
                    usedElements.add(input);
                    return getSelector(input);
                }
            }
            return null;
        }

        // messageフィールドは特別扱い（パターンマッチを優先、textareaはフォールバック）
        function findMessageField(config) {
            // まずパターンマッチで検索
            const patternResult = 
                findByNameOrId('message', config) || 
                findByPlaceholder('message', config) || 
                findByLabel('message', config) ||
                findByAriaLabel('message', config);
            
            if (patternResult) return patternResult;
            
            // パターンマッチで見つからなければtextareaをフォールバック
            const textareas = document.querySelectorAll('textarea');
            for (const ta of textareas) {
                if (!usedElements.has(ta) && isVisible(ta)) {
                    usedElements.add(ta);
                    return getSelector(ta);
                }
            }
            return null;
        }

        // 各フィールドを検出（優先度順）
        for (const [fieldName, config] of Object.entries(patterns)) {
            if (fieldName === 'message') {
                result[fieldName] = findMessageField(config);
            } else {
                // 複数の戦略を順に試す
                result[fieldName] = 
                    findByNameOrId(fieldName, config) ||
                    findByType(fieldName, config) ||
                    findByPlaceholder(fieldName, config) ||
                    findByLabel(fieldName, config) ||
                    findByAriaLabel(fieldName, config);
            }
        }

        // メッセージフィールドがない場合はnull
        if (!result.message) {
            return JSON.stringify(null);
        }

        // nullのフィールドを除外
        const cleanResult = {};
        for (const [k, v] of Object.entries(result)) {
            if (v !== null) cleanResult[k] = v;
        }

        return JSON.stringify(cleanResult);
    })()
    """

    result_str = browser_evaluate(port, script)
    if not result_str or result_str == 'null':
        return None

    try:
        result = json.loads(result_str)
        if not result or not result.get('message'):
            return None
        return result
    except json.JSONDecodeError as e:
        print(f"[WARN] Form fields response parse failed: {e}")
        return None


def detect_captcha(port: int) -> bool:
    """
    CAPTCHA存在を検出（reCAPTCHA/hCaptcha/Turnstile）

    Args:
        port: ブラウザコンテナのポート

    Returns:
        True if CAPTCHA detected, False otherwise
    """
    script = """
    (function() {
        return !!(
            // reCAPTCHA
            document.querySelector('.g-recaptcha') ||
            document.querySelector('[data-sitekey]') ||
            document.querySelector('iframe[src*="recaptcha"]') ||
            document.querySelector('iframe[src*="google.com/recaptcha"]') ||
            // hCaptcha
            document.querySelector('.h-captcha') ||
            document.querySelector('iframe[src*="hcaptcha"]') ||
            // Cloudflare Turnstile
            document.querySelector('.cf-turnstile') ||
            document.querySelector('iframe[src*="turnstile"]') ||
            // 一般的なCAPTCHA
            document.querySelector('img[src*="captcha"]') ||
            document.querySelector('input[name*="captcha"]')
        );
    })()
    """

    result = browser_evaluate(port, script)
    return result == 'true'


def fill_and_submit_form(port: int, form_fields: Dict[str, str],
                         form_data: Dict[str, str],
                         timeout: int = 120) -> Dict[str, Any]:
    """
    フォーム入力・送信（v2: 確認画面対応版）

    Args:
        port: ブラウザコンテナのポート
        form_fields: detect_form_fields() で取得したフィールド情報
        form_data: 入力データ
        timeout: タイムアウト（秒）

    Returns:
        {'status': 'success'|'failed'|'skipped', 'error': str, 'screenshot': str}
    """
    fields_json = json.dumps(form_fields)
    data_json = json.dumps(form_data)

    script = f"""
    (function() {{
        try {{
            const fields = {fields_json};
            const data = {data_json};

            // セレクタをエスケープする関数
            function safeQuerySelector(selector) {{
                try {{
                    return document.querySelector(selector);
                }} catch(e) {{
                    // 特殊文字を含むセレクタの場合、IDとして試す
                    if (selector.startsWith('#')) {{
                        const id = selector.slice(1);
                        return document.getElementById(id);
                    }}
                    // name属性として試す
                    if (selector.startsWith('[name=')) {{
                        const match = selector.match(/\[name=["']?([^"'\]]+)["']?\]/);
                        if (match) {{
                            return document.querySelector('[name="' + CSS.escape(match[1]) + '"]');
                        }}
                    }}
                    return null;
                }}
            }}

            // 1. フォーム入力（React対応版）
            // React/Next.jsフォームでは直接value設定だけでは状態が更新されない
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
            
            function setReactValue(el, value) {{
                if (el.tagName === 'TEXTAREA') {{
                    nativeTextAreaValueSetter.call(el, value);
                }} else {{
                    nativeInputValueSetter.call(el, value);
                }}
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                el.dispatchEvent(new Event('blur', {{ bubbles: true }}));
            }}
            
            for (const [field, selector] of Object.entries(fields)) {{
                if (!data[field]) continue;

                // セレクタで要素を検索（エスケープ対応）
                const el = safeQuerySelector(selector);

                if (el) {{
                    setReactValue(el, data[field]);
                }}
            }}

            // 1.5. 同意チェックボックスを検出してチェック
            const agreePatterns = [
                'input[type="checkbox"][name*="agree"]',
                'input[type="checkbox"][name*="consent"]',
                'input[type="checkbox"][name*="privacy"]',
                'input[type="checkbox"][name*="policy"]',
                'input[type="checkbox"][name*="terms"]',
                'input[type="checkbox"][name*="同意"]',
                'input[type="checkbox"][id*="agree"]',
                'input[type="checkbox"][id*="consent"]',
                'input[type="checkbox"][id*="privacy"]',
            ];
            
            // パターンマッチで同意チェックボックスを探す
            for (const sel of agreePatterns) {{
                const checkbox = document.querySelector(sel);
                if (checkbox && !checkbox.checked) {{
                    checkbox.checked = true;
                    checkbox.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }}
            
            // ラベルテキストで同意チェックボックスを探す
            const allCheckboxes = document.querySelectorAll('input[type="checkbox"]');
            for (const cb of allCheckboxes) {{
                const label = document.querySelector('label[for="' + cb.id + '"]') || cb.closest('label');
                if (label) {{
                    const labelText = label.textContent || '';
                    if (labelText.includes('同意') || labelText.includes('個人情報') || 
                        labelText.includes('プライバシー') || labelText.includes('利用規約') ||
                        labelText.includes('agree') || labelText.includes('consent')) {{
                        if (!cb.checked) {{
                            cb.checked = true;
                            cb.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                }}
            }}
            
            // カスタムUIチェックボックス対応（button role="checkbox"）
            // Radix UI等のカスタムコンポーネントはmousedown/mouseup/clickイベントが必要
            const customCheckboxes = document.querySelectorAll('button[role="checkbox"][aria-checked="false"]');
            for (const btn of customCheckboxes) {{
                // 親要素のテキストで同意関連かを判定
                const parent = btn.closest('div') || btn.parentElement;
                const parentText = parent ? (parent.textContent || '') : '';
                if (parentText.includes('同意') || parentText.includes('個人情報') ||
                    parentText.includes('プライバシー') || parentText.includes('利用規約') ||
                    parentText.includes('agree') || parentText.includes('consent')) {{
                    // 完全なクリックシーケンスを発火
                    btn.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true, view: window }}));
                    btn.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true, view: window }}));
                    btn.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window }}));
                }}
            }}

            // 2. 送信ボタン検出（拡充版）
            const submitPatterns = [
                // type属性
                'button[type="submit"]',
                'input[type="submit"]',
                // value属性
                'input[value*="送信"]',
                'input[value*="確認"]',
                'input[value*="問い合わせ"]',
                'input[value*="申し込"]',
                'input[value*="完了"]',
                'input[value*="Submit"]',
                'input[value*="Send"]',
                // class属性
                '.submit-btn',
                '.submit-button',
                '.btn-submit',
                '.btn-primary',
                '.contact-submit',
                // id属性
                '#submit',
                '#submitBtn',
                '#send',
                // form内のbutton
                'form button:not([type="button"]):not([type="reset"])',
            ];

            const buttonTexts = [
                '送信', '送信する', '確認', '確認する', '確認画面へ', '次へ',
                '問い合わせ', 'お問い合わせ', '問い合わせる', '申し込む', '申込',
                '完了', '完了する', '入力内容を確認', '内容を確認',
                'Submit', 'Send', 'Confirm', 'Next'
            ];

            // セレクタでボタン検索
            for (const sel of submitPatterns) {{
                const btn = document.querySelector(sel);
                if (btn && btn.offsetParent !== null) {{
                    btn.click();
                    return JSON.stringify({{status: 'success', step: 'first'}});
                }}
            }}

            // テキスト内容でボタン検索
            const allButtons = document.querySelectorAll('button, input[type="button"], a.btn, a.button, [role="button"]');
            for (const btn of allButtons) {{
                if (btn.offsetParent === null) continue;
                const text = (btn.textContent || btn.value || '').trim();
                for (const pattern of buttonTexts) {{
                    if (text === pattern || text.includes(pattern)) {{
                        btn.click();
                        return JSON.stringify({{status: 'success', step: 'first'}});
                    }}
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

        # 確認画面対応: firstステップの場合、次の送信ボタンも押す
        if result.get('status') == 'success' and result.get('step') == 'first':
            # 2秒待って確認画面の送信ボタンを押す
            confirm_script = """
            (function() {
                return new Promise(resolve => {
                    setTimeout(() => {
                        const confirmTexts = ['送信', '送信する', '完了', 'Submit', 'Send'];
                        const buttons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                        for (const btn of buttons) {
                            if (btn.offsetParent === null) continue;
                            const text = (btn.textContent || btn.value || '').trim();
                            for (const pattern of confirmTexts) {
                                if (text === pattern || text.includes(pattern)) {
                                    btn.click();
                                    resolve(JSON.stringify({status: 'success', step: 'confirmed'}));
                                    return;
                                }
                            }
                        }
                        resolve(JSON.stringify({status: 'success', step: 'first_only'}));
                    }, 2000);
                });
            })()
            """
            confirm_result = browser_evaluate(port, confirm_script, timeout=30)
            if confirm_result:
                try:
                    result = json.loads(confirm_result)
                except json.JSONDecodeError as e:
                    # 確認画面のレスポンス解析失敗はログして続行
                    print(f"[WARN] Confirm screen response parse failed: {e}")

        result['screenshot'] = None
        return result
    except json.JSONDecodeError as e:
        return {'status': 'failed', 'error': f'Failed to parse response: {e}', 'screenshot': None}


def take_screenshot(port: int, output_path: str) -> bool:
    """
    エラー時のスクリーンショット保存

    Note: ブラウザAPIにスクリーンショット機能がないため、
    現在は未実装。

    Args:
        port: ブラウザコンテナのポート
        output_path: 保存先パス

    Returns:
        True if successful, False otherwise
    """
    return False
