---
name: sales-list-creation
description: 営業ターゲット企業のリストを自動作成。DuckDuckGo検索で企業を収集し、カスタム項目（技術スタック、資金調達情報など）を自動抽出。JSON/CSV/Markdown形式で出力。
---

# 営業リスト作成スキル

## 概要

営業ターゲット企業のリストを自動で作成するスキルです。

**主な機能**:
- DuckDuckGo検索で企業情報を収集
- 企業情報の自動抽出（会社名、URL、問い合わせフォーム）
- カスタム項目の自動判定と抽出
- JSON/CSV/Markdown形式での出力

**カスタム項目の自動判定**:
- **IT企業**: 技術スタック、開発実績、エンジニア数
- **製造業**: 主要製品、工場所在地、ISO認証
- **スタートアップ**: 調達ラウンド、調達額、調達日
- **その他**: 業種に応じて柔軟に判定

## 実行手順

### 1. Dockerコンテナ起動

```bash
cd docker
docker compose up -d --scale browser=15
```

### 2. スキル実行

```
/sales-list-creation "検索クエリ" --max-companies 100
```

**例**:
```
/sales-list-creation "東京 IT企業"
/sales-list-creation "大阪 Web制作会社" --max-companies 50
/sales-list-creation "AI スタートアップ 資金調達" --max-companies 30
```

### 3. 出力確認

```bash
ls -l projects/sales-automation/output/
# sales_list_YYYYMMDD_HHMM.json
# sales_list_YYYYMMDD_HHMM.csv
# sales_list_YYYYMMDD_HHMM.md
```

## パラメータ

| パラメータ | 説明 | デフォルト |
|----------|------|-----------|
| 検索クエリ | DuckDuckGoで検索するキーワード | 必須 |
| --max-companies | 目標収集件数 | 100 |
| --containers | 並列実行コンテナ数 | 15 |

## 出力形式

### JSON (`sales_list.json`)

プログラムから利用しやすい形式。

```json
[
  {
    "company_name": "株式会社Example",
    "website_url": "https://example.com",
    "contact_form_url": "https://example.com/contact",
    "industry": "Web制作",
    "employees": 50,
    "custom_field_1": "React, TypeScript",
    "custom_field_2": "ECサイト開発10件以上",
    "custom_field_3": "エンジニア15名"
  }
]
```

### CSV (`sales_list.csv`)

スプレッドシートで管理しやすい形式。

```csv
company_name,website_url,contact_form_url,industry,employees,custom_field_1,custom_field_2,custom_field_3
株式会社Example,https://example.com,https://example.com/contact,Web制作,50,React, TypeScript,ECサイト開発10件以上,エンジニア15名
```

### Markdown (`sales_list.md`)

レポート形式で読みやすい。

```markdown
# 営業リスト

## 株式会社Example

- **Website**: https://example.com
- **問い合わせフォーム**: https://example.com/contact
- **業種**: Web制作
- **従業員数**: 50名
- **技術スタック**: React, TypeScript
- **開発実績**: ECサイト開発10件以上
- **エンジニア数**: 15名
```

## カスタム項目の自動抽出

業種に応じて自動的に適切な項目を抽出します。

### IT企業の場合

- **custom_field_1**: 技術スタック（React, TypeScript, Pythonなど）
- **custom_field_2**: 開発実績（ECサイト、SaaS、モバイルアプリなど）
- **custom_field_3**: エンジニア数

### 製造業の場合

- **custom_field_1**: 主要製品（自動車部品、電子部品など）
- **custom_field_2**: 工場所在地
- **custom_field_3**: ISO認証（ISO9001、ISO14001など）

### スタートアップの場合

- **custom_field_1**: 調達ラウンド（シリーズA、シリーズBなど）
- **custom_field_2**: 調達額（5億円、10億円など）
- **custom_field_3**: 調達日（2023年4月など）

## 実行例

### 例1: IT企業の営業リスト作成

```
/sales-list-creation "東京 IT企業 Web制作" --max-companies 50
```

**結果**:
- 50社のIT企業リスト
- 技術スタック、開発実績、エンジニア数を自動抽出
- JSON/CSV/Markdown形式で出力

### 例2: スタートアップの営業リスト作成

```
/sales-list-creation "AI スタートアップ シリーズA" --max-companies 30
```

**結果**:
- 30社のAIスタートアップリスト
- 調達ラウンド、調達額、調達日を自動抽出
- 問い合わせフォームが存在する企業のみ収集

### 例3: 製造業の営業リスト作成

```
/sales-list-creation "大阪 製造業 自動車部品"
```

**結果**:
- 100社の製造業リスト（デフォルト）
- 主要製品、工場所在地、ISO認証を自動抽出

## トラブルシューティング

### 問題: Dockerコンテナが起動しない

**解決策**:
```bash
cd docker
docker compose down
docker compose up -d --scale browser=15
```

### 問題: 検索結果が少ない

**解決策**:
- 検索クエリを見直す（より一般的なキーワードに変更）
- 並列コンテナ数を増やす（`--containers 20`など）

### 問題: カスタム項目が抽出されない

**解決策**:
- 企業のWebサイトに情報が掲載されていない可能性があります
- 検索クエリにキーワードを追加（例: "技術スタック", "資金調達"）

### 問題: 出力ファイルが見つからない

**確認**:
```bash
ls -la projects/sales-automation/output/
```

出力ディレクトリが存在しない場合:
```bash
mkdir -p projects/sales-automation/output
```

## 次のステップ

営業リスト作成後、以下の作業が可能です:

1. **手動確認**: CSVファイルをスプレッドシートで開いて確認
2. **フィルタリング**: 不要な企業を削除
3. **フォーム送信**: `/form-sales` スキルで自動営業

## 参考ファイル

- スクリプト: `projects/sales-automation/scripts/create_sales_list.py`
- 設定ファイル: `projects/sales-automation/config/sales_automation.json`
- ドキュメント: `projects/sales-automation/README.md`
