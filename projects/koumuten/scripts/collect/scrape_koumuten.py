import requests
import re
import json
import time
import os
from urllib.parse import urljoin

BASE_URL = "https://suumo.jp"
GUNMA_LIST_URL = "https://suumo.jp/chumon/tn_gumma/"

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_company_list_from_page(url):
    """Get company names and links from a single page"""
    try:
        response = requests.get(url, headers=headers, timeout=30)
        html = response.text

        # Extract company links with class main_cassette-title_link
        pattern = r'<a href="([^"]*)"[^>]*class="main_cassette-title_link"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html)

        companies = []
        for link, name in matches:
            full_url = urljoin(BASE_URL, link)
            companies.append({
                'name': name.strip(),
                'suumo_url': full_url
            })

        # Check for next page
        next_page_match = re.search(r'<link rel="next" href="([^"]+)"', html)
        next_page = next_page_match.group(1) if next_page_match else None
        if next_page:
            next_page = urljoin(BASE_URL, next_page)

        return companies, next_page
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return [], None

def get_company_details(url, name):
    """Get details from company page"""
    try:
        response = requests.get(url, headers=headers, timeout=30)
        html = response.text

        details = {
            'name': name,
            'suumo_url': url,
            'homepage': None,
            'contact_url': None,
            'instagram': None,
            'location': None,
            'features': []
        }

        # Try to find official website
        hp_match = re.search(r'公式ホームページ[^<]*<a[^>]*href="([^"]*)"', html)
        if hp_match:
            details['homepage'] = hp_match.group(1)

        # Try to find location info
        loc_match = re.search(r'所在地[^<]*</dt>[^<]*<dd[^>]*>([^<]+)', html)
        if loc_match:
            details['location'] = loc_match.group(1).strip()

        # Try to find features/keywords
        feature_patterns = [
            r'キーワード[^<]*</dt>[^<]*<dd[^>]*>([^<]+)',
            r'こだわり[^<]*</dt>[^<]*<dd[^>]*>([^<]+)',
        ]
        for pattern in feature_patterns:
            feat_match = re.search(pattern, html)
            if feat_match:
                details['features'].append(feat_match.group(1).strip())

        return details
    except Exception as e:
        print(f"Error fetching details for {name}: {e}")
        return {
            'name': name,
            'suumo_url': url,
            'homepage': None,
            'contact_url': None,
            'instagram': None,
            'location': None,
            'features': []
        }

def main():
    all_companies = []
    seen_names = set()

    # Collect from multiple pages
    current_url = GUNMA_LIST_URL
    page_num = 1

    while current_url and page_num <= 10:  # Limit to 10 pages
        print(f"Fetching page {page_num}: {current_url}")
        companies, next_url = get_company_list_from_page(current_url)

        for company in companies:
            if company['name'] not in seen_names:
                seen_names.add(company['name'])
                all_companies.append(company)
                print(f"  Found: {company['name']}")

        current_url = next_url
        page_num += 1
        time.sleep(1)  # Rate limiting

    print(f"\nTotal unique companies found: {len(all_companies)}")

    # Get details for each company (limited to first 50 for speed)
    detailed_companies = []
    for i, company in enumerate(all_companies[:50]):
        print(f"Getting details for {company['name']} ({i+1}/{min(50, len(all_companies))})")
        details = get_company_details(company['suumo_url'], company['name'])
        detailed_companies.append(details)
        time.sleep(0.5)

    # Save results
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    output_path = os.path.join(project_dir, 'output', 'koumuten_list.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(detailed_companies, f, ensure_ascii=False, indent=2)

    print(f"\nResults saved to {output_path}")
    return detailed_companies

if __name__ == "__main__":
    main()
