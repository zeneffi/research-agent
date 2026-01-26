"""
各県の工務店リストを統合するスクリプト
"""

import json
from pathlib import Path

def load_json(filepath):
    """JSONファイルを読み込む"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def normalize_company(company, prefecture):
    """会社データを正規化する"""
    if not isinstance(company, dict):
        return None

    # 異なるキー名を統一（日本語キーにも対応）
    normalized = {
        "company_name": (
            company.get("company_name") or
            company.get("name") or
            company.get("会社名", "")
        ),
        "prefecture": prefecture,
        "location": (
            company.get("location") or
            company.get("city") or
            company.get("所在地", "")
        ),
        "website_url": (
            company.get("official_url") or
            company.get("official_hp") or
            company.get("website_url") or
            company.get("url") or
            company.get("公式HP", "")
        ),
        "contact_url": (
            company.get("contact_form_url") or
            company.get("contact_url") or
            company.get("問い合わせフォームURL", "")
        ),
        "instagram_url": (
            company.get("instagram_url") or
            company.get("instagram") or
            company.get("InstagramURL", "")
        ),
        "features": company.get("features") or company.get("特徴", []),
        "rating": company.get("rating")
    }

    # features が文字列の場合はリストに変換
    if isinstance(normalized["features"], str):
        normalized["features"] = [normalized["features"]] if normalized["features"] else []

    return normalized

def main():
    companies_dir = Path("projects/koumuten/output/companies")
    all_companies = []

    prefecture_map = {
        "tokyo.json": "東京都",
        "kanagawa.json": "神奈川県",
        "saitama.json": "埼玉県",
        "chiba.json": "千葉県",
        "ibaraki.json": "茨城県",
        "tochigi.json": "栃木県",
        "gunma.json": "群馬県"
    }

    stats = {}

    for filename, prefecture in prefecture_map.items():
        filepath = companies_dir / filename
        if not filepath.exists():
            print(f"ファイルが見つかりません: {filepath}")
            continue

        data = load_json(filepath)

        # データ構造に応じて処理
        if isinstance(data, list):
            companies = data
        elif isinstance(data, dict):
            # metadataがある場合
            if "koumuten_list" in data:
                companies = data["koumuten_list"]
            elif "companies" in data:
                companies = data["companies"]
            elif "工務店リスト" in data:
                companies = data["工務店リスト"]
            else:
                # 最初のリスト値を探す
                for v in data.values():
                    if isinstance(v, list):
                        companies = v
                        break
                else:
                    companies = []
        else:
            companies = []

        count = len(companies)
        stats[prefecture] = count

        for company in companies:
            normalized = normalize_company(company, prefecture)
            if normalized and normalized["company_name"]:  # 空でないものだけ追加
                all_companies.append(normalized)

        print(f"{prefecture}: {count}社")

    # 重複除去（会社名ベース）
    seen = set()
    unique_companies = []
    for company in all_companies:
        name = company["company_name"]
        if name not in seen:
            seen.add(name)
            unique_companies.append(company)

    print(f"\n合計: {len(all_companies)}社")
    print(f"重複除去後: {len(unique_companies)}社")

    # 統合ファイルを保存
    output = {
        "metadata": {
            "created_date": "2026-01-26",
            "total_count": len(unique_companies),
            "stats_by_prefecture": stats
        },
        "companies": unique_companies
    }

    output_path = companies_dir / "all_kanto.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n統合ファイルを保存しました: {output_path}")

if __name__ == "__main__":
    main()
