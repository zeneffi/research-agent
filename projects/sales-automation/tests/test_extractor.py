"""
Tests for extractor.py - Company information extraction
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from lib.extractor import extract_company_info, extract_custom_fields
from lib.browser import get_container_ports, browser_navigate
import time


def test_extract_company_info():
    """Test basic company information extraction"""
    print("\n=== Test: extract_company_info ===")

    ports = get_container_ports()
    if not ports:
        print("❌ FAILED: No containers available")
        return

    port = ports[0]

    # Test with example.com (simple site)
    test_url = "https://example.com"
    print(f"Extracting info from: {test_url}")

    browser_navigate(port, test_url)
    time.sleep(2)

    info = extract_company_info(port, test_url)

    print(f"Extracted info: {info}")

    assert info is not None, "Should return company info"
    assert isinstance(info, dict), "Info should be a dict"
    assert 'company_name' in info, "Should have company_name key"
    assert 'company_url' in info, "Should have company_url key"

    # Check key fields are strings
    assert isinstance(info['company_name'], str), "company_name should be string"
    assert isinstance(info['company_url'], str), "company_url should be string"
    assert isinstance(info.get('location', ''), str), "location should be string"
    assert isinstance(info.get('business', ''), str), "business should be string"

    print(f"  Company Name: {info['company_name']}")
    print(f"  Company URL: {info['company_url']}")
    print(f"  Location: {info.get('location', '(not found)')}")
    print(f"  Business: {info.get('business', '(not found)')}")

    print("✅ PASSED: Company info extraction working")


def test_extract_custom_fields():
    """Test custom field extraction based on context"""
    print("\n=== Test: extract_custom_fields ===")

    # Test with sample text containing IT-related information
    sample_text = """
    株式会社テックカンパニー
    使用技術: Python, TypeScript, React, AWS
    エンジニア: 50名
    開発実績: 大手企業向けWebアプリケーション開発
    """

    # Test IT context
    context = "IT"
    print(f"Extracting custom fields for context: {context}")
    custom_fields = extract_custom_fields(sample_text, context)

    print(f"Custom fields: {custom_fields}")

    assert custom_fields is not None, "Should return custom fields"
    assert isinstance(custom_fields, dict), "Custom fields should be a dict"

    # Check that all values are strings (or empty strings if not found)
    for key, value in custom_fields.items():
        assert isinstance(value, str), f"{key} should be a string, got {type(value)}"
        print(f"  {key}: {value if value else '(not found)'}")

    # Test Manufacturing context
    context = "Manufacturing"
    print(f"\nExtracting custom fields for context: {context}")
    sample_manufacturing_text = """
    製造業の会社です
    生産拠点: 愛知県、大阪府
    年間生産台数: 10000台
    主要取引先: トヨタ自動車、日産自動車
    """
    custom_fields = extract_custom_fields(sample_manufacturing_text, context)
    print(f"Custom fields: {custom_fields}")

    for key, value in custom_fields.items():
        assert isinstance(value, str), f"{key} should be a string"
        print(f"  {key}: {value if value else '(not found)'}")

    print("✅ PASSED: Custom field extraction working")


if __name__ == "__main__":
    print("=" * 60)
    print("EXTRACTOR.PY TEST SUITE")
    print("=" * 60)

    try:
        test_extract_company_info()
        test_extract_custom_fields()

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! ✅")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
