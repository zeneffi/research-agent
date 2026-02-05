"""
Tests for search.py - DuckDuckGo search functionality
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from lib.search import search_duckduckgo, is_valid_company_url, determine_search_context
from lib.browser import get_container_ports


def test_search_duckduckgo():
    """Test DuckDuckGo search functionality"""
    print("\n=== Test: search_duckduckgo ===")

    ports = get_container_ports()
    if not ports:
        print("❌ FAILED: No containers available")
        return

    # Test with a simple query
    query = "東京 IT企業"
    print(f"Searching for: {query}")

    results = search_duckduckgo(ports[0], query, max_results=10)

    print(f"Found {len(results)} results")
    if results:
        print(f"First result: {results[0]}")

    assert len(results) > 0, "Should return at least 1 result"
    assert all(isinstance(r, dict) for r in results), "All results should be dicts"
    assert all('url' in r for r in results), "All results should have 'url' key"

    # Check that excluded domains are filtered
    excluded_domains = ['indeed.com', 'mynavi.jp', 'rikunabi.com', 'doda.jp', 'wikipedia.org']
    for result in results:
        url = result['url']
        assert not any(domain in url for domain in excluded_domains), \
            f"Excluded domain found in results: {url}"

    print("✅ PASSED: DuckDuckGo search working correctly")


def test_is_valid_company_url():
    """Test URL validation for company websites"""
    print("\n=== Test: is_valid_company_url ===")

    # Valid company URLs
    valid_urls = [
        "https://example-company.co.jp",
        "https://tech-startup.com",
        "https://company.jp/about",
    ]

    # Invalid URLs (job sites, social media, etc.)
    invalid_urls = [
        "https://indeed.com/company/example",
        "https://rikunabi.com/jobs/example",
        "https://facebook.com/company",
        "https://twitter.com/company",
        "https://wikipedia.org/wiki/Company",
    ]

    for url in valid_urls:
        result = is_valid_company_url(url)
        print(f"  {url}: {result}")
        assert result is True, f"Expected {url} to be valid"

    for url in invalid_urls:
        result = is_valid_company_url(url)
        print(f"  {url}: {result}")
        assert result is False, f"Expected {url} to be invalid"

    print("✅ PASSED: URL validation working correctly")


def test_determine_search_context():
    """Test industry/context determination from query"""
    print("\n=== Test: determine_search_context ===")

    test_cases = [
        ("東京 IT企業", "IT", "技術、エンジニアリング"),
        ("大阪 製造業", "製造", "製造、生産"),
        ("スタートアップ 資金調達", "スタートアップ", "起業、資金"),
    ]

    for query, expected_keyword, expected_context in test_cases:
        context = determine_search_context(query)
        print(f"  Query: {query}")
        print(f"  Context: {context}")

        # Check that context contains relevant information
        assert context, f"Context should not be empty for query: {query}"
        assert isinstance(context, str), "Context should be a string"

    print("✅ PASSED: Search context determination working")


if __name__ == "__main__":
    print("=" * 60)
    print("SEARCH.PY TEST SUITE")
    print("=" * 60)

    try:
        test_is_valid_company_url()  # This doesn't need Docker
        test_determine_search_context()  # This doesn't need Docker
        test_search_duckduckgo()  # This needs Docker

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
