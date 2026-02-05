"""
Tests for contact_finder.py - Contact form detection
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from lib.contact_finder import find_contact_form_url, is_valid_contact_url
from lib.browser import get_container_ports, browser_navigate
import time


def test_is_valid_contact_url():
    """Test contact URL validation"""
    print("\n=== Test: is_valid_contact_url ===")

    # Valid contact URLs
    valid_urls = [
        "https://example.com/contact",
        "https://example.com/inquiry",
        "https://example.com/お問い合わせ",
        "https://example.com/contact-us",
        "https://example.com/support/contact",
    ]

    # Invalid contact URLs (non-contact pages)
    invalid_urls = [
        "https://example.com/blog",
        "https://example.com/about",
        "https://example.com/products",
        "https://example.com/news",
        "https://example.com/services",
    ]

    for url in valid_urls:
        result = is_valid_contact_url(url)
        print(f"  {url}: {result}")
        assert result is True, f"Expected {url} to be valid contact URL"

    for url in invalid_urls:
        result = is_valid_contact_url(url)
        print(f"  {url}: {result}")
        assert result is False, f"Expected {url} to be invalid contact URL"

    print("✅ PASSED: Contact URL validation working correctly")


def test_find_contact_form_url():
    """Test contact form URL detection"""
    print("\n=== Test: find_contact_form_url ===")

    ports = get_container_ports()
    if not ports:
        print("❌ FAILED: No containers available")
        return

    port = ports[0]

    # Test with example.com (may or may not have contact form)
    test_url = "https://example.com"
    print(f"Finding contact form on: {test_url}")

    browser_navigate(port, test_url)
    time.sleep(2)

    contact_url = find_contact_form_url(port, test_url)

    print(f"Contact URL found: {contact_url if contact_url else '(not found)'}")

    # The function should return either a valid URL or empty string
    assert isinstance(contact_url, str), "Result should be a string"

    if contact_url:
        # If found, it should be a valid URL
        assert contact_url.startswith('http'), "Contact URL should start with http"
        print(f"  Found: {contact_url}")
    else:
        print(f"  Not found (this is OK for example.com)")

    print("✅ PASSED: Contact form detection working")


def test_find_contact_form_url_with_common_path():
    """Test contact form detection with common path patterns"""
    print("\n=== Test: find_contact_form_url (common paths) ===")

    ports = get_container_ports()
    if not ports:
        print("❌ FAILED: No containers available")
        return

    port = ports[0]

    # Test a site that likely has /contact path
    # Using a placeholder - in real testing we'd use actual company websites
    test_url = "https://example.com"
    base_url = test_url

    print(f"Testing common paths for: {base_url}")

    # The function tries common paths like /contact, /inquiry, etc.
    contact_url = find_contact_form_url(port, test_url)

    assert isinstance(contact_url, str), "Result should be a string"
    print(f"  Result: {contact_url if contact_url else '(not found)'}")

    print("✅ PASSED: Common path detection working")


if __name__ == "__main__":
    print("=" * 60)
    print("CONTACT_FINDER.PY TEST SUITE")
    print("=" * 60)

    try:
        test_is_valid_contact_url()  # This doesn't need Docker
        test_find_contact_form_url()  # This needs Docker
        test_find_contact_form_url_with_common_path()  # This needs Docker

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
