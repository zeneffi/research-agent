---
name: form-sales
description: 問い合わせフォームから営業文を自動送信。企業情報に応じてLLMで営業文を生成し、フォームに自動入力・送信。
---

# フォーム営業スキル

## 概要

営業リストの企業に対して、問い合わせフォームから営業文を自動送信する。
企業タイプに応じてカスタマイズした営業文を生成（テンプレート or LLM）。

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

### 営業リストからフォーム送信

```bash
cd ~/repos/research-agent

# 10社に送信（テスト推奨）
python projects/sales-automation/scripts/send_sales_form.py \
  projects/sales-automation/output/sales_list_YYYYMMDD_HHMM.json \
  --max-sends 10
```

### 一気通貫（リスト作成→送信）

```bash
cd ~/repos/research-agent

# 検索クエリ、収集企業数、送信上限を指定
./projects/sales-automation/scripts/run_pipeline.sh "東京 システム開発会社" 50 30
```

## 設定ファイル

`projects/sales-automation/config/sales_automation.json`

```json
{
  "form_sales": {
    "sender_info": {
      "company_name": "ゼネフィ合同会社",
      "contact_name": "藤崎俊平",
      "contact_name_kana": "フジサキ シュンペイ",
      "email": "shumpei.fujisaki@zeneffi.co.jp",
      "phone": "070-1317-2700"
    },
    "rate_limit": {
      "interval_seconds": 10,
      "daily_limit": 100
    },
    "message_generation": {
      "use_llm": false
    }
  }
}
```

### LLMで営業文を生成する場合

```json
{
  "form_sales": {
    "message_generation": {
      "use_llm": true,
      "model": "gpt-4o-mini",
      "system_prompt": "あなたは営業文を作成するアシスタントです..."
    }
  }
}
```

※ `OPENAI_API_KEY` 環境変数が必要

## 営業コンセプト

**紹介パートナー募集**
- リソース不足でお断りしている受託案件を紹介してほしい
- 還元率30%（500万案件なら150万還元）
- 商談同席不要、メールで繋ぐだけでOK

## 企業タイプ別の営業文

| 企業タイプ | 判定条件 | メッセージ内容 |
|----------|---------|--------------|
| スタートアップ | 「シリーズ」「調達」等 | 資金調達に言及し、成長支援を提案 |
| IT企業 | React, Python等の技術名 | 技術スタックに言及し、技術支援を提案 |
| 製造業 | 「ISO」 | ISO認証・品質へのこだわりに言及 |
| 汎用 | その他 | 標準的なテンプレート |

## レート制限

- **送信間隔**: 10秒（デフォルト）
- **1日上限**: 100件
- **並列度**: 1コンテナ

## 対応フォーム

- 標準HTMLフォーム ✅
- React/Next.jsフォーム ✅（nativeValueSetter対応）
- Radix UIチェックボックス ✅（MouseEvent対応）
- CAPTCHA検出 → 自動スキップ

## 出力

```
projects/sales-automation/output/
├── send_log.json      # 送信ログ（成功/失敗/スキップ）
└── send_report.md     # サマリーレポート
```

## 処理時間目安

| 規模 | 時間（10秒間隔の場合） |
|------|----------------------|
| 10件 | 約2分 |
| 30件 | 約5分 |
| 100件 | 約17分 |

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

### 送信がスキップされる

- CAPTCHA検出: reCAPTCHA/hCaptchaが存在
- フォーム未検出: 問い合わせフォームが見つからない
- URL無し: contact_form_urlが空

## 関連スキル

- [sales-list-creation](../sales-list-creation/SKILL.md) - 営業リスト作成
