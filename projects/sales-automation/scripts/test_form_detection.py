#!/usr/bin/env python3
"""
フォーム検出 + テスト送信（送信はしない）のテストスクリプト

⚠️ 安全策:
- 送信ボタンは絶対にクリックしない
- フォーム入力 → バリデーション確認まで
"""
import sys
import os
import json
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.browser import get_container_ports, browser_navigate, browser_evaluate
from lib.contact_finder import find_contact_form_url


def test_form_detection(port: int, company_url: str, company_name: str) -> dict:
    """
    1社のフォーム検出テスト
    
    Returns:
        {
            'company_name': str,
            'company_url': str,
            'form_url': str,
            'form_found': bool,
            'fields_detected': list,
            'can_fill': bool,
        }
    """
    result = {
        'company_name': company_name,
        'company_url': company_url,
        'form_url': '',
        'form_found': False,
        'fields_detected': [],
        'can_fill': False,
    }
    
    # フォームURL検出
    form_url = find_contact_form_url(port, company_url)
    if not form_url:
        return result
    
    result['form_url'] = form_url
    result['form_found'] = True
    
    # フォームページに移動
    if not browser_navigate(port, form_url, timeout=15):
        return result
    
    time.sleep(3)
    
    # フォームフィールドを検出
    detect_script = """(function() {
        const fields = [];
        const form = document.querySelector('form');
        if (!form) return JSON.stringify({fields: [], has_form: false});
        
        // 入力フィールド検出
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            const type = input.type || input.tagName.toLowerCase();
            const name = input.name || input.id || '';
            const placeholder = input.placeholder || '';
            const label = '';
            
            // ラベル検出
            let labelText = '';
            if (input.id) {
                const labelElem = document.querySelector(`label[for="${input.id}"]`);
                if (labelElem) labelText = labelElem.textContent.trim();
            }
            
            fields.push({
                type: type,
                name: name,
                placeholder: placeholder,
                label: labelText,
                required: input.required
            });
        });
        
        // 送信ボタン検出
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        
        return JSON.stringify({
            fields: fields,
            has_form: true,
            has_submit: !!submitBtn
        });
    })()"""
    
    detect_result = browser_evaluate(port, detect_script, timeout=10)
    if detect_result:
        try:
            data = json.loads(detect_result)
            result['fields_detected'] = data.get('fields', [])
            result['can_fill'] = data.get('has_form', False) and len(data.get('fields', [])) > 0
        except:
            pass
    
    return result


def test_form_fill_dry_run(port: int, form_url: str) -> dict:
    """
    フォーム入力テスト（送信なし）
    
    ⚠️ 送信ボタンは絶対にクリックしない
    
    Returns:
        {
            'fill_success': bool,
            'filled_fields': list,
            'validation_errors': list,
        }
    """
    result = {
        'fill_success': False,
        'filled_fields': [],
        'validation_errors': [],
    }
    
    if not browser_navigate(port, form_url, timeout=15):
        return result
    
    time.sleep(3)
    
    # テストデータでフォーム入力（送信はしない）
    fill_script = """(function() {
        const filled = [];
        const errors = [];
        const form = document.querySelector('form');
        if (!form) return JSON.stringify({success: false, filled: [], errors: ['フォームが見つかりません']});
        
        // テストデータ
        const testData = {
            email: 'test@example.com',
            name: 'テスト 太郎',
            company: 'テスト株式会社',
            tel: '03-1234-5678',
            phone: '03-1234-5678',
            message: 'これはテストメッセージです。送信はされません。',
            subject: 'お問い合わせテスト',
        };
        
        // 各フィールドに入力
        const inputs = form.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            const type = input.type || 'text';
            const name = (input.name || input.id || '').toLowerCase();
            
            // 入力不要なタイプはスキップ
            if (['submit', 'button', 'hidden', 'checkbox', 'radio', 'file'].includes(type)) {
                return;
            }
            
            let value = '';
            
            // フィールド名から適切な値を選択
            if (type === 'email' || name.includes('email') || name.includes('mail')) {
                value = testData.email;
            } else if (name.includes('name') || name.includes('氏名') || name.includes('名前')) {
                value = testData.name;
            } else if (name.includes('company') || name.includes('会社') || name.includes('社名')) {
                value = testData.company;
            } else if (name.includes('tel') || name.includes('phone') || name.includes('電話')) {
                value = testData.tel;
            } else if (name.includes('message') || name.includes('内容') || name.includes('body') || input.tagName === 'TEXTAREA') {
                value = testData.message;
            } else if (name.includes('subject') || name.includes('件名')) {
                value = testData.subject;
            } else if (type === 'text') {
                value = 'テスト入力';
            }
            
            if (value) {
                input.value = value;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
                filled.push({name: name || type, value: value.substring(0, 20)});
            }
        });
        
        // バリデーションチェック（送信せずに）
        const invalidInputs = form.querySelectorAll(':invalid');
        invalidInputs.forEach(input => {
            errors.push({
                name: input.name || input.id || 'unknown',
                message: input.validationMessage || '入力エラー'
            });
        });
        
        return JSON.stringify({
            success: filled.length > 0,
            filled: filled,
            errors: errors
        });
    })()"""
    
    fill_result = browser_evaluate(port, fill_script, timeout=10)
    if fill_result:
        try:
            data = json.loads(fill_result)
            result['fill_success'] = data.get('success', False)
            result['filled_fields'] = data.get('filled', [])
            result['validation_errors'] = data.get('errors', [])
        except:
            pass
    
    return result


def main():
    """メイン処理"""
    # 最新のリストを読み込み
    output_dir = '/private/tmp/research-agent/projects/sales-automation/output'
    json_files = sorted([f for f in os.listdir(output_dir) if f.endswith('.json')])
    if not json_files:
        print("エラー: 営業リストが見つかりません")
        return
    
    latest_file = os.path.join(output_dir, json_files[-1])
    print(f"リストファイル: {latest_file}")
    
    with open(latest_file) as f:
        data = json.load(f)
    
    companies = data.get('companies', [])
    print(f"企業数: {len(companies)}")
    print("=" * 70)
    
    ports = get_container_ports()
    if not ports:
        print("エラー: コンテナが起動していません")
        return
    
    # 最初の10社でテスト
    test_companies = companies[:10]
    
    results = {
        'total': len(test_companies),
        'form_found': 0,
        'fill_success': 0,
        'details': []
    }
    
    for i, company in enumerate(test_companies, 1):
        port = ports[i % len(ports)]
        name = company.get('company_name', 'Unknown')
        url = company.get('company_url', '')
        
        print(f"\n[{i}/{len(test_companies)}] {name[:30]}")
        print(f"  URL: {url}")
        
        # フォーム検出
        detection = test_form_detection(port, url, name)
        
        if detection['form_found']:
            results['form_found'] += 1
            print(f"  ✓ フォーム検出: {detection['form_url'][:60]}")
            print(f"    フィールド数: {len(detection['fields_detected'])}")
            
            # フォーム入力テスト（送信なし）
            if detection['can_fill']:
                fill_result = test_form_fill_dry_run(port, detection['form_url'])
                
                if fill_result['fill_success']:
                    results['fill_success'] += 1
                    print(f"  ✓ 入力テスト成功")
                    for f in fill_result['filled_fields'][:3]:
                        print(f"      - {f['name']}: {f['value']}")
                    if fill_result['validation_errors']:
                        print(f"    ⚠ バリデーションエラー: {len(fill_result['validation_errors'])}件")
                else:
                    print(f"  ✗ 入力テスト失敗")
                
                detection['fill_result'] = fill_result
        else:
            print(f"  ✗ フォーム未検出")
        
        results['details'].append(detection)
        time.sleep(1)
    
    # サマリー
    print("\n" + "=" * 70)
    print("【サマリー】")
    print(f"  テスト企業数: {results['total']}")
    print(f"  フォーム検出: {results['form_found']}/{results['total']} ({results['form_found']/results['total']*100:.1f}%)")
    print(f"  入力テスト成功: {results['fill_success']}/{results['form_found']} ({results['fill_success']/max(results['form_found'],1)*100:.1f}%)" if results['form_found'] > 0 else "  入力テスト: N/A")
    print("=" * 70)
    
    # 結果保存
    result_file = os.path.join(output_dir, 'form_test_result.json')
    with open(result_file, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n結果保存: {result_file}")


if __name__ == "__main__":
    main()
