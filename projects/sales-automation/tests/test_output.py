#!/usr/bin/env python
"""
output.py のテストスクリプト
"""
import sys
import os
import json
import csv
import tempfile

# ライブラリのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from lib.output import (
    generate_json_output,
    generate_csv_output,
    generate_markdown_report,
    get_custom_field_labels,
    calculate_contact_form_rate
)


# テスト用サンプルデータ
SAMPLE_COMPANIES = [
    {
        "company_name": "株式会社サンプルA",
        "company_url": "https://sample-a.co.jp",
        "contact_form_url": "https://sample-a.co.jp/contact",
        "location": "東京都渋谷区",
        "business": "Webサービス開発",
        "custom_field_1": "React, Node.js",
        "custom_field_2": "50名",
        "custom_field_3": "大手ECサイト開発",
        "source_query": "東京 IT企業",
    },
    {
        "company_name": "株式会社サンプルB",
        "company_url": "https://sample-b.co.jp",
        "contact_form_url": "",  # 未検出
        "location": "大阪府大阪市",
        "business": "製造業DX支援",
        "custom_field_1": "Python, AWS",
        "custom_field_2": "30名",
        "custom_field_3": "",
        "source_query": "大阪 製造業",
    },
    {
        "company_name": "スタートアップC",
        "company_url": "https://startup-c.com",
        "contact_form_url": "https://startup-c.com/inquiry",
        "location": "東京都港区",
        "business": "AIプラットフォーム",
        "custom_field_1": "シリーズA",
        "custom_field_2": "3億円",
        "custom_field_3": "2025年1月",
        "source_query": "スタートアップ 資金調達",
    },
]


def test_get_custom_field_labels():
    """カスタム項目ラベル取得のテスト"""
    print("\n[TEST] get_custom_field_labels()")

    tests = [
        ("IT", {"custom_field_1": "技術スタック", "custom_field_2": "エンジニア数", "custom_field_3": "開発実績"}),
        ("Manufacturing", {"custom_field_1": "主要製品", "custom_field_2": "工場所在地", "custom_field_3": "ISO認証"}),
        ("Startup", {"custom_field_1": "調達ラウンド", "custom_field_2": "調達額", "custom_field_3": "調達日"}),
        ("General", {"custom_field_1": "カスタム項目1", "custom_field_2": "カスタム項目2", "custom_field_3": "カスタム項目3"}),
    ]

    passed = 0
    failed = 0

    for context, expected in tests:
        result = get_custom_field_labels(context)
        if result == expected:
            print(f"  ✓ {context}: {result['custom_field_1']}, {result['custom_field_2']}, {result['custom_field_3']}")
            passed += 1
        else:
            print(f"  ✗ {context}: 期待と異なる")
            failed += 1

    print(f"  結果: {passed} passed, {failed} failed")
    return failed == 0


def test_calculate_contact_form_rate():
    """問い合わせフォーム検出率計算のテスト"""
    print("\n[TEST] calculate_contact_form_rate()")

    rate = calculate_contact_form_rate(SAMPLE_COMPANIES)
    expected_rate = 2 / 3 * 100  # 3社中2社が検出

    if abs(rate - expected_rate) < 0.01:
        print(f"  ✓ 検出率: {rate:.1f}% (期待: {expected_rate:.1f}%)")
        return True
    else:
        print(f"  ✗ 検出率: {rate:.1f}% (期待: {expected_rate:.1f}%)")
        return False


def test_generate_json_output():
    """JSON出力のテスト"""
    print("\n[TEST] generate_json_output()")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        output_path = f.name

    try:
        generate_json_output(SAMPLE_COMPANIES, output_path, "IT")

        # ファイルが作成されたか確認
        if not os.path.exists(output_path):
            print(f"  ✗ JSONファイルが作成されていない")
            return False

        # JSONを読み込んで検証
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 構造チェック
        if "metadata" not in data or "companies" not in data:
            print(f"  ✗ JSON構造が不正")
            return False

        if data["metadata"]["total_count"] != len(SAMPLE_COMPANIES):
            print(f"  ✗ 企業数が一致しない")
            return False

        if data["metadata"]["search_context"] != "IT":
            print(f"  ✗ search_contextが一致しない")
            return False

        print(f"  ✓ JSON出力成功: {len(data['companies'])}社")
        return True

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_generate_csv_output():
    """CSV出力のテスト"""
    print("\n[TEST] generate_csv_output()")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        output_path = f.name

    try:
        generate_csv_output(SAMPLE_COMPANIES, output_path, "IT")

        # ファイルが作成されたか確認
        if not os.path.exists(output_path):
            print(f"  ✗ CSVファイルが作成されていない")
            return False

        # CSVを読み込んで検証
        with open(output_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if len(rows) != len(SAMPLE_COMPANIES):
            print(f"  ✗ 行数が一致しない: {len(rows)} (期待: {len(SAMPLE_COMPANIES)})")
            return False

        # ヘッダーチェック
        expected_headers = [
            'company_name', 'company_url', 'contact_form_url',
            'location', 'business', 'custom_field_1', 'custom_field_2',
            'custom_field_3', 'source_query', 'collected_at'
        ]
        if list(rows[0].keys()) != expected_headers:
            print(f"  ✗ ヘッダーが不正")
            return False

        print(f"  ✓ CSV出力成功: {len(rows)}行")
        return True

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def test_generate_markdown_report():
    """Markdown出力のテスト"""
    print("\n[TEST] generate_markdown_report()")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        output_path = f.name

    try:
        generate_markdown_report(SAMPLE_COMPANIES, output_path, "IT")

        # ファイルが作成されたか確認
        if not os.path.exists(output_path):
            print(f"  ✗ Markdownファイルが作成されていない")
            return False

        # Markdownを読み込んで検証
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 必須セクションのチェック
        required_sections = [
            "# 営業リスト",
            "エグゼクティブサマリー",
            "カスタム項目定義",
            "企業リスト",
        ]

        missing = []
        for section in required_sections:
            if section not in content:
                missing.append(section)

        if missing:
            print(f"  ✗ 以下のセクションが見つからない: {missing}")
            return False

        # 企業数のチェック
        if f"{len(SAMPLE_COMPANIES)}社" not in content:
            print(f"  ✗ 企業数が記載されていない")
            return False

        print(f"  ✓ Markdown出力成功: {len(content)}文字")
        return True

    finally:
        if os.path.exists(output_path):
            os.remove(output_path)


def main():
    print("=" * 60)
    print("output.py テストスクリプト")
    print("=" * 60)

    results = []

    results.append(("get_custom_field_labels", test_get_custom_field_labels()))
    results.append(("calculate_contact_form_rate", test_calculate_contact_form_rate()))
    results.append(("generate_json_output", test_generate_json_output()))
    results.append(("generate_csv_output", test_generate_csv_output()))
    results.append(("generate_markdown_report", test_generate_markdown_report()))

    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    total_passed = sum(1 for _, passed in results if passed)
    total = len(results)

    print(f"\n  合計: {total_passed}/{total} passed")

    if total_passed == total:
        print("\n  🎉 全テスト成功！")
        return 0
    else:
        print(f"\n  ⚠️  {total - total_passed}件のテストが失敗")
        return 1


if __name__ == "__main__":
    sys.exit(main())
