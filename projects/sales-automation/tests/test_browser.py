"""
Tests for browser.py - Docker container communication
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from lib.browser import get_container_ports, browser_navigate, browser_evaluate, browser_get_content
import time


def test_get_container_ports():
    """Test that we can get 15 container ports"""
    print("\n=== Test: get_container_ports ===")
    ports = get_container_ports()

    print(f"Found {len(ports)} containers")
    print(f"Ports: {ports[:3]}..." if len(ports) > 3 else f"Ports: {ports}")

    assert len(ports) == 15, f"Expected 15 containers, got {len(ports)}"
    assert all(isinstance(p, int) for p in ports), "All ports should be integers"
    print("✅ PASSED: get_container_ports returned 15 valid ports")


def test_browser_navigate():
    """Test navigation to a URL"""
    print("\n=== Test: browser_navigate ===")
    ports = get_container_ports()

    if not ports:
        print("❌ FAILED: No containers available")
        return

    port = ports[0]
    test_url = "https://example.com"

    print(f"Navigating to {test_url} on port {port}...")
    result = browser_navigate(port, test_url)

    print(f"Result: {result}")
    assert result is True, f"Navigation failed"
    print(f"✅ PASSED: Successfully navigated to {test_url}")


def test_browser_evaluate():
    """Test JavaScript execution"""
    print("\n=== Test: browser_evaluate ===")
    ports = get_container_ports()

    if not ports:
        print("❌ FAILED: No containers available")
        return

    port = ports[0]

    # First navigate to a page
    browser_navigate(port, "https://example.com")
    time.sleep(2)

    # Test JavaScript evaluation
    script = "document.title"
    print(f"Evaluating: {script}")
    result = browser_evaluate(port, script)

    print(f"Result: {result}")
    assert result is not None, "Evaluation failed - result is None"
    assert isinstance(result, str), "Result should be a string"
    print(f"Page title: {result}")
    print("✅ PASSED: Successfully evaluated JavaScript")


def test_browser_get_content():
    """Test getting page content"""
    print("\n=== Test: browser_get_content ===")
    ports = get_container_ports()

    if not ports:
        print("❌ FAILED: No containers available")
        return

    port = ports[0]

    # First navigate to a page
    browser_navigate(port, "https://example.com")
    time.sleep(2)

    # Get page content
    print("Getting page content...")
    result = browser_get_content(port)

    assert result is not None, "Content retrieval failed - result is None"
    assert isinstance(result, dict), "Result should be a dict"

    # The result has 'html', 'text', 'url', 'title' keys
    html = result.get("html", "")
    text = result.get("text", "")
    title = result.get("title", "")
    url = result.get("url", "")

    print(f"Title: {title}")
    print(f"URL: {url}")
    print(f"HTML length: {len(html)} characters")
    print(f"Text length: {len(text)} characters")
    print(f"Text preview: {text[:100]}...")

    assert html, "HTML should not be empty"
    assert text, "Text should not be empty"
    assert "Example Domain" in text or "example" in text.lower(), "Text should contain 'Example'"
    print("✅ PASSED: Successfully retrieved page content")


if __name__ == "__main__":
    print("=" * 60)
    print("BROWSER.PY TEST SUITE")
    print("=" * 60)

    try:
        test_get_container_ports()
        test_browser_navigate()
        test_browser_evaluate()
        test_browser_get_content()

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
