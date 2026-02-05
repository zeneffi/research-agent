#!/usr/bin/env python
"""
normalizer.py のテストスクリプト
"""
import sys
import os

# ライブラリのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts'))

from lib.normalizer import (
    normalize_company_name,
    deduplicate_companies,
    clean_text,
    validate_company_data
)


def test_normalize_company_name():
    """企業名正規化のテスト"""
    print("\n[TEST] normalize_company_name()")

    tests = [
        ("株式会社サンプル企業", "サンプル企業"),
        ("有限会社 Test Company", "testcompany"),
        ("合同会社ABC", "abc"),
        ("株式会社   スペース   多い", "スペース多い"),
        ("Test Inc.", "testinc."),
    ]

    passed = 0
    failed = 0

    for input_val, expected in tests:
        result = normalize_company_name(input_val)
        if result == expected:
            print(f"  ✓ '{input_val}' -> '{result}'")
            passed += 1
        else:
            print(f"  ✗ '{input_val}' -> '{result}' (期待: '{expected}')")
            failed += 1

    print(f"  結果: {passed} passed, {failed} failed")
    return failed == 0


def test_deduplicate_companies():
    """重複排除のテスト"""
    print("\n[TEST] deduplicate_companies()")

    companies = [
        {"company_name": "株式会社ABC", "company_url": "https://abc.co.jp"},
        {"company_name": "ABC", "company_url": "https://abc.co.jp"},  # 重複
        {"company_name": "株式会社DEF", "company_url": "https://def.co.jp"},
        {"company_name": "株式会社ABC", "company_url": "https://abc-different.co.jp"},  # 重複
        {"company_name": "GHI Corp", "company_url": "https://ghi.com"},
    ]

    result = deduplicate_companies(companies)

    print(f"  入力: {len(companies)}社")
    print(f"  出力: {len(result)}社")

    # 期待: 3社（ABC, DEF, GHI）
    if len(result) == 3:
        print(f"  ✓ 重複排除成功（3社に削減）")
        return True
    else:
        print(f"  ✗ 期待: 3社, 実際: {len(result)}社")
        return False


def test_clean_text():
    """テキストクリーニングのテスト"""
    print("\n[TEST] clean_text()")

    tests = [
        ("改行\nタブ\tあり", "改行 タブ あり"),
        ("  前後空白  ", "前後空白"),
        ("複数  空白    あり", "複数 空白 あり"),
        ("a" * 250, "a" * 200 + "..."),  # 最大文字数
    ]

    passed = 0
    failed = 0

    for input_val, expected in tests:
        result = clean_text(input_val, max_length=200)
        if result == expected:
            print(f"  ✓ クリーニング成功")
            passed += 1
        else:
            print(f"  ✗ 入力: '{input_val[:30]}...'")
            print(f"    出力: '{result[:30]}...'")
            print(f"    期待: '{expected[:30]}...'")
            failed += 1

    print(f"  結果: {passed} passed, {failed} failed")
    return failed == 0


def test_validate_company_data():
    """データバリデーションのテスト"""
    print("\n[TEST] validate_company_data()")

    tests = [
        ({"company_name": "Test", "company_url": "https://test.com"}, True, "正常なデータ"),
        ({"company_name": "", "company_url": "https://test.com"}, False, "企業名が空"),
        ({"company_name": "Test", "company_url": ""}, False, "URLが空"),
        ({"company_name": "Test", "company_url": "not-a-url"}, False, "不正なURL"),
        ({"company_name": "Test"}, False, "URLフィールドなし"),
    ]

    passed = 0
    failed = 0

    for data, expected, description in tests:
        result = validate_company_data(data)
        if result == expected:
            print(f"  ✓ {description}: {result}")
            passed += 1
        else:
            print(f"  ✗ {description}: {result} (期待: {expected})")
            failed += 1

    print(f"  結果: {passed} passed, {failed} failed")
    return failed == 0


def main():
    print("=" * 60)
    print("normalizer.py テストスクリプト")
    print("=" * 60)

    results = []

    results.append(("normalize_company_name", test_normalize_company_name()))
    results.append(("deduplicate_companies", test_deduplicate_companies()))
    results.append(("clean_text", test_clean_text()))
    results.append(("validate_company_data", test_validate_company_data()))

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
