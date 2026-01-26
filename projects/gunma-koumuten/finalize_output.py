import json

def finalize_output():
    # Load enriched data
    with open('/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/projects/gunma-koumuten/output/koumuten_enriched.json', 'r', encoding='utf-8') as f:
        companies = json.load(f)

    # Final output format
    final_output = {
        "metadata": {
            "description": "群馬県の工務店・ハウスメーカー一覧",
            "source": "SUUMO",
            "total_count": len(companies),
            "collection_date": "2026-01-26"
        },
        "companies": []
    }

    for company in companies:
        # Clean up features
        features = list(set(company.get('features', [])))

        # Derive feature summary
        feature_summary = None
        if features:
            if '自然素材' in features or '無垢材' in features:
                feature_summary = '自然素材住宅'
            elif 'ローコスト' in features:
                feature_summary = 'ローコスト住宅'
            elif 'デザイン住宅' in features:
                feature_summary = 'デザイン住宅'
            elif '高気密・高断熱' in features or '高性能' in features:
                feature_summary = '高性能住宅'
            elif '輸入住宅' in features:
                feature_summary = '輸入住宅'
            elif '平屋' in features:
                feature_summary = '平屋住宅'
            elif features:
                feature_summary = features[0]

        formatted_company = {
            "company_name": company['name'],
            "location": company.get('location') or "群馬県",
            "official_hp": company.get('homepage'),
            "contact_url": company.get('contact_url'),
            "instagram_url": company.get('instagram'),
            "features": features,
            "feature_summary": feature_summary,
            "suumo_url": company['suumo_url']
        }

        final_output['companies'].append(formatted_company)

    # Save final output
    output_path = '/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/projects/gunma-koumuten/output/gunma_koumuten_final.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    print(f"Final output saved to {output_path}")
    print(f"Total companies: {len(final_output['companies'])}")

    # Stats
    with_hp = sum(1 for c in final_output['companies'] if c.get('official_hp'))
    with_loc = sum(1 for c in final_output['companies'] if c.get('location') and c.get('location') != "群馬県")
    with_features = sum(1 for c in final_output['companies'] if c.get('features'))

    print(f"Companies with official HP: {with_hp}")
    print(f"Companies with specific location: {with_loc}")
    print(f"Companies with features: {with_features}")

    return final_output

if __name__ == "__main__":
    finalize_output()
