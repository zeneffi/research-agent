"""
出力処理（JSON/CSV/Markdown）
"""
import json
import csv
from datetime import datetime
from typing import List, Dict, Any


def generate_json_output(companies: List[Dict[str, Any]], output_path: str, search_context: str = 'General'):
    """
    JSON形式で出力

    Args:
        companies: 企業情報のリスト
        output_path: 出力ファイルパス
        search_context: 業種コンテキスト
    """
    output = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_count": len(companies),
            "search_context": search_context,
        },
        "companies": companies
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def generate_csv_output(companies: List[Dict[str, Any]], output_path: str, search_context: str = 'General'):
    """
    CSV形式で出力

    Args:
        companies: 企業情報のリスト
        output_path: 出力ファイルパス
        search_context: 業種コンテキスト
    """
    # CSV列定義
    fieldnames = [
        'company_name',
        'company_url',
        'contact_form_url',
        'location',
        'business',
        'custom_field_1',
        'custom_field_2',
        'custom_field_3',
        'source_query',
        'collected_at',
    ]

    with open(output_path, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for company in companies:
            # 空のフィールドを埋める
            row = {field: company.get(field, '') for field in fieldnames}
            row['collected_at'] = datetime.now().strftime('%Y-%m-%d %H:%M')
            writer.writerow(row)


def generate_markdown_report(companies: List[Dict[str, Any]], output_path: str, search_context: str = 'General'):
    """
    Markdown形式でレポート生成

    Args:
        companies: 企業情報のリスト
        output_path: 出力ファイルパス
        search_context: 業種コンテキスト
    """
    today = datetime.now().strftime("%Y年%m月%d日 %H:%M")

    # カスタム項目のラベル定義
    custom_labels = get_custom_field_labels(search_context)

    md = f"""# 営業リスト

**作成日**: {today}
**収集企業数**: {len(companies)}社
**業種コンテキスト**: {search_context}

---

## エグゼクティブサマリー

| 指標 | 値 |
|-----|-----|
| 総企業数 | {len(companies)}社 |
| 問い合わせフォーム検出率 | {calculate_contact_form_rate(companies):.1f}% |

### カスタム項目定義

| 項目 | 説明 |
|-----|-----|
| custom_field_1 | {custom_labels['custom_field_1']} |
| custom_field_2 | {custom_labels['custom_field_2']} |
| custom_field_3 | {custom_labels['custom_field_3']} |

---

## 企業リスト

"""

    for i, company in enumerate(companies, 1):
        md += f"""### {i}. {company.get('company_name', 'Unknown')}

| 項目 | 内容 |
|-----|------|
| **企業名** | {company.get('company_name', '不明')} |
| **URL** | {company.get('company_url', '不明')} |
| **問い合わせフォーム** | {company.get('contact_form_url', '未検出')} |
| **所在地** | {company.get('location', '不明')} |
| **事業内容** | {company.get('business', '不明')} |
| **{custom_labels['custom_field_1']}** | {company.get('custom_field_1', '-')} |
| **{custom_labels['custom_field_2']}** | {company.get('custom_field_2', '-')} |
| **{custom_labels['custom_field_3']}** | {company.get('custom_field_3', '-')} |

"""

    # フッター
    md += """---

## データ収集について

このリストは自動収集により作成されました。以下の点にご注意ください：

- **問い合わせフォームURL**: 3段階検出（よくあるパス、トップページリンク、フッター/ヘッダー）
- **カスタム項目**: 業種コンテキストに基づいて動的に抽出
- **重複排除**: 企業名の正規化により重複を排除

"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)


def get_custom_field_labels(search_context: str) -> Dict[str, str]:
    """
    業種コンテキストに応じたカスタム項目ラベルを取得

    Args:
        search_context: 業種コンテキスト

    Returns:
        {custom_field_1: label, ...}
    """
    labels = {
        'IT': {
            'custom_field_1': '技術スタック',
            'custom_field_2': 'エンジニア数',
            'custom_field_3': '開発実績',
        },
        'Manufacturing': {
            'custom_field_1': '主要製品',
            'custom_field_2': '工場所在地',
            'custom_field_3': 'ISO認証',
        },
        'Startup': {
            'custom_field_1': '調達ラウンド',
            'custom_field_2': '調達額',
            'custom_field_3': '調達日',
        },
        'General': {
            'custom_field_1': 'カスタム項目1',
            'custom_field_2': 'カスタム項目2',
            'custom_field_3': 'カスタム項目3',
        }
    }

    return labels.get(search_context, labels['General'])


def calculate_contact_form_rate(companies: List[Dict[str, Any]]) -> float:
    """
    問い合わせフォーム検出率を計算

    Args:
        companies: 企業情報のリスト

    Returns:
        検出率（%）
    """
    if not companies:
        return 0.0

    detected = sum(1 for c in companies if c.get('contact_form_url', ''))
    return (detected / len(companies)) * 100
