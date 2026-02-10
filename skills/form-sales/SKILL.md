---
name: form-sales
description: 問い合わせフォームから営業文を自動送信。企業情報に応じてLLMで営業文を生成し、フォームに自動入力・送信。
---

# フォーム営業スキル

## 概要

営業リストの企業に対して、問い合わせフォームから営業文を自動送信する。
LLM（GPT-4o-mini）で企業ごとにカスタマイズした営業文を生成。

## 使い方

```bash
cd ~/repos/research-agent
source .venv/bin/activate

# リストからフォーム送信
python projects/sales-automation/scripts/send_forms.py \
  --input projects/sales-automation/output/companies_YYYYMMDD.json \
  --max-send 30

# または一気通貫（リスト作成→送信）
./projects/sales-automation/scripts/run_pipeline.sh "東京 システム開発会社" 50 30
```

## 営業文テンプレート

設定ファイル: `projects/sales-automation/config/sales_automation.json`

```json
{
  "sender": {
    "name": "藤崎俊平",
    "company": "ゼネフィ合同会社",
    "email": "shumpei.fujisaki@zeneffi.co.jp",
    "phone": "070-1317-2700"
  },
  "llm": {
    "model": "gpt-4o-mini",
    "system_prompt": "..."
  }
}
```

## 営業コンセプト

**紹介パートナー募集**
- リソース不足でお断りしている受託案件を紹介してほしい
- 還元率30%（500万案件なら150万還元）
- 商談同席不要、メールで繋ぐだけでOK

## レート制限

| 設定 | 値 |
|------|-----|
| 送信間隔 | 10秒 |
| 1日上限 | 100件 |
| 理由 | スパム判定回避 |

## 対応フォーム

- 標準HTMLフォーム ✓
- React/Next.jsフォーム ✓（nativeValueSetter対応）
- Radix UIチェックボックス ✓（MouseEvent対応）

## 出力

```
projects/sales-automation/output/
├── send_log.json      # 送信ログ（成功/失敗）
└── send_report.md     # サマリーレポート
```

## 処理時間目安

| 規模 | 時間 |
|------|------|
| 10件 | 約5分 |
| 30件 | 約15分 |
| 50件 | 約25分 |

## 関連

- [sales-list-creation](../sales-list-creation/SKILL.md) - 営業リスト作成
