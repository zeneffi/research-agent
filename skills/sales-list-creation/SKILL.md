---
name: sales-list-creation
description: 営業ターゲット企業のリストを自動作成。DuckDuckGo検索で企業を収集し、問い合わせフォームを自動検出。
---

# 営業リスト作成スキル

## 概要

検索クエリから営業ターゲット企業を収集し、問い合わせフォームURLを自動検出する。

## 使い方

```bash
cd ~/repos/research-agent
source .venv/bin/activate

# 基本実行（50社収集、フォーム30件まで検出）
python projects/sales-automation/scripts/create_list.py \
  --query "東京 システム開発会社 受託" \
  --max-companies 50 \
  --max-forms 30

# 出力先
# projects/sales-automation/output/companies_YYYYMMDD_HHMMSS.json
```

## パラメータ

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| --query | 検索クエリ | 必須 |
| --max-companies | 収集する企業数 | 50 |
| --max-forms | フォーム検出の上限 | 30 |

## 出力形式

```json
{
  "companies": [
    {
      "name": "株式会社〇〇",
      "url": "https://example.com",
      "contact_url": "https://example.com/contact",
      "form_fields": {
        "company": "#company",
        "name": "#name",
        "email": "#email",
        "message": "#message"
      }
    }
  ]
}
```

## 処理時間目安

| 規模 | 時間 |
|------|------|
| 10社 | 約3分 |
| 50社 | 約15分 |
| 100社 | 約30分 |

## 必要環境

- Python 3.11+
- Dockerブラウザ起動済み（`docker compose up -d`）
- DuckDuckGo検索API（キー不要）

## 関連

- [form-sales](../form-sales/SKILL.md) - 作成したリストにフォーム送信
