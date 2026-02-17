---
name: sales-list-creation
description: 営業ターゲット企業のリストを自動作成。DuckDuckGo検索で企業を収集し、問い合わせフォームを自動検出。
---

# 営業リスト作成スキル

## 概要

検索クエリから営業ターゲット企業を収集し、問い合わせフォームURLを自動検出する。
15コンテナ並列でWeb調査を実行。

## 前提条件

```bash
# 1. リポジトリに移動
cd ~/repos/research-agent

# 2. Dockerコンテナ起動（初回 or 停止中の場合）
cd docker && docker compose up -d && cd ..

# 3. Python仮想環境を有効化
source projects/sales-automation/venv/bin/activate
```

## 基本的な使い方

```bash
cd ~/repos/research-agent

# 基本実行（50社収集）
python projects/sales-automation/scripts/create_sales_list.py \
  "東京 システム開発会社 受託" \
  --max-companies 50
```

### パラメータ

| パラメータ | 説明 | デフォルト |
|-----------|------|-----------|
| 第1引数 | 検索クエリ | 必須 |
| --max-companies | 収集する企業数 | 100 |

## 一気通貫（リスト作成→フォーム送信）

```bash
cd ~/repos/research-agent

# 検索クエリ、収集企業数、送信上限を指定
./projects/sales-automation/scripts/run_pipeline.sh "東京 IT企業" 50 30
```

## 出力

```
projects/sales-automation/output/
├── sales_list_YYYYMMDD_HHMM.json  # JSON形式
├── sales_list_YYYYMMDD_HHMM.csv   # CSV形式（スプレッドシート用）
└── sales_list_YYYYMMDD_HHMM.md    # Markdownレポート
```

### JSON出力形式

```json
{
  "companies": [
    {
      "company_name": "株式会社〇〇",
      "company_url": "https://example.com",
      "contact_form_url": "https://example.com/contact",
      "location": "東京都渋谷区",
      "business": "システム開発",
      "custom_field_1": "React, Python, AWS",
      "custom_field_2": "エンジニア30名",
      "custom_field_3": ""
    }
  ]
}
```

## カスタム項目（業種別自動抽出）

| 業種 | 抽出項目 |
|------|---------|
| IT | 技術スタック、エンジニア数、開発実績 |
| 製造業 | 主要製品、工場所在地、ISO認証 |
| スタートアップ | 調達ラウンド、調達額、調達日 |

## 検索エンジン

**DuckDuckGo専用**（Googleは使用しない）
- CAPTCHA回避のため
- URL: `https://duckduckgo.com/?q=検索クエリ`

## 除外ドメイン

以下のドメインは自動的に除外：
- SNS（facebook, twitter, instagram, youtube）
- 大手EC（amazon, rakuten）
- 求人サイト（indeed, wantedly）
- wikipedia

## 処理時間目安

| 規模 | 時間 |
|------|------|
| 10社 | 約3分 |
| 50社 | 約15分 |
| 100社 | 約30分 |

## トラブルシューティング

### Dockerコンテナが起動していない

```bash
cd ~/repos/research-agent/docker
docker compose up -d
docker compose ps  # 確認
```

### モジュールが見つからない

```bash
# venvを有効化しているか確認
source projects/sales-automation/venv/bin/activate
```

### 企業が見つからない

- 検索クエリを調整（より具体的に or より一般的に）
- 地域名を追加（「東京」「大阪」など）

## 関連スキル

- [form-sales](../form-sales/SKILL.md) - 作成したリストにフォーム送信
