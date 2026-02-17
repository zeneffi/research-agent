---
name: form-sales
description: 問い合わせフォームから営業文を自動送信。企業情報に応じて営業文を自動生成（4パターン）。レート制限・CAPTCHA検出・送信ログで安全に運用。
---

# フォーム営業スキル

## 概要

問い合わせフォームから営業文を自動送信するスキルです。

**主な機能**:
- フォーム項目の自動検出
- 企業情報に応じた営業文の自動生成（4パターン）
- レート制限（3分間隔、100件/日）
- CAPTCHA自動検出・スキップ
- 送信ログ・レポート自動生成

**安全対策**:
- レート制限で過負荷を防止
- CAPTCHA検出時は自動スキップ
- 全送信を記録（成功/失敗/スキップ）

## 環境セットアップ（初回のみ）

### 1. Dockerコンテナ起動

```bash
cd docker
docker compose up -d
cd ..
```

### 2. Python仮想環境を有効化

```bash
source projects/sales-automation/venv/bin/activate
```

### 3. LLMで営業文を生成する場合（オプション）

```bash
export OPENAI_API_KEY="your-api-key"
```

---

## 前提条件

### 1. 営業リストが作成済み

`sales-list-creation` スキルで営業リストを作成してください。

```bash
python projects/sales-automation/scripts/create_sales_list.py "東京 IT企業" --max-companies 50
```

### 2. 送信者情報を設定

`projects/sales-automation/config/sales_automation.json` を編集:

```json
{
  "form_sales": {
    "sender_info": {
      "company_name": "株式会社あなたの会社",
      "contact_name": "山田太郎",
      "email": "info@yourcompany.com",
      "phone": "03-1234-5678"
    }
  }
}
```

## 実行手順

### 1. 送信者情報を設定

```bash
vim projects/sales-automation/config/sales_automation.json
```

または

```bash
nano projects/sales-automation/config/sales_automation.json
```

**設定内容**:
```json
{
  "form_sales": {
    "sender_info": {
      "company_name": "株式会社あなたの会社",
      "contact_name": "山田太郎",
      "email": "info@yourcompany.com",
      "phone": "03-1234-5678"
    },
    "rate_limit": {
      "delay_seconds": 180,
      "daily_limit": 100
    }
  }
}
```

### 2. テスト送信（少数）

```bash
python projects/sales-automation/scripts/send_sales_form.py \
  projects/sales-automation/output/sales_list_20260204_2034.json \
  --max-sends 3
```

**推奨**: 最初は3〜5社でテストしてください。

### 3. 本番送信

```bash
python projects/sales-automation/scripts/send_sales_form.py \
  projects/sales-automation/output/sales_list_20260204_2034.json
```

デフォルトで100件/日まで送信されます。

### 一気通貫（リスト作成→送信）

```bash
./projects/sales-automation/scripts/run_pipeline.sh "東京 IT企業" 50 30
```
※ 検索クエリ、収集企業数、送信上限を指定

### 4. 結果確認

```bash
cat projects/sales-automation/output/send_report.md
```

送信レポートが自動生成されます。

## パラメータ

| パラメータ | 説明 | デフォルト |
|----------|------|-----------|
| 営業リストファイル | 送信対象のJSONファイル | 必須 |
| --max-sends | 最大送信件数 | 100 |
| --delay | 送信間隔（秒） | 180（3分） |

## 営業文生成パターン

企業情報に応じて4つのパターンから自動選択します。

### パターン1: スタートアップ向け

**条件**: `custom_field_1` に "シリーズA", "シリーズB", "資金調達" が含まれる場合

```
件名: 【貴社事業拡大のお手伝い】

シリーズAで5億円の調達おめでとうございます。

事業拡大フェーズでのリソース不足をサポートさせていただけないでしょうか。
弊社はIT分野での実績が豊富で、貴社の成長に貢献できると考えております。

詳細は以下よりご確認ください。
https://yourcompany.com

株式会社あなたの会社
山田太郎
info@yourcompany.com
03-1234-5678
```

### パターン2: IT企業向け

**条件**: `custom_field_1` に "React", "TypeScript", "Python", "技術スタック" が含まれる場合

```
件名: 【技術面でのお手伝い】

貴社がReact, TypeScriptを活用されていることを拝見しました。

弊社も同技術での実績が豊富で、Web制作分野での貴社の事業に
技術面でお力添えできればと考えております。

ぜひ一度お話させていただけないでしょうか。

株式会社あなたの会社
山田太郎
info@yourcompany.com
03-1234-5678
```

### パターン3: 製造業向け

**条件**: `industry` に "製造", `custom_field_3` に "ISO" が含まれる場合

```
件名: 【製造業向けソリューションのご提案】

ISO9001認証取得されている貴社の品質管理体制に感銘を受けました。

弊社の製造業向けソリューションが、貴社の更なる効率化に
貢献できると考えております。

詳細は以下よりご確認ください。
https://yourcompany.com

株式会社あなたの会社
山田太郎
info@yourcompany.com
03-1234-5678
```

### パターン4: 汎用

**条件**: 上記に該当しない場合

```
件名: 【ビジネスのお手伝い】

貴社のWebサイトを拝見し、ご連絡させていただきました。

弊社のサービスが貴社の事業にお役に立てるのではないかと考えております。

ぜひ一度お話させていただけないでしょうか。

株式会社あなたの会社
山田太郎
info@yourcompany.com
03-1234-5678
```

## 安全機能

### レート制限

**目的**: サーバーへの過負荷を防止

- **送信間隔**: 3分（180秒）
- **日次上限**: 100件
- **管理方法**: `send_log.json` で自動チェック

**上限に達した場合**:
```
レート制限に達しました。明日再実行してください。
今日の送信件数: 100/100
```

### CAPTCHA検出

**対応**:
- reCAPTCHA自動検出
- hCaptcha自動検出
- 検出時は自動スキップ
- ログに記録

**ログ例**:
```json
{
  "company_name": "株式会社Example",
  "status": "skipped",
  "reason": "CAPTCHA detected",
  "timestamp": "2026-02-04 20:45:00"
}
```

### 送信ログ

**ログファイル**: `projects/sales-automation/output/send_log.json`

全送信を記録:
- 成功: `status: "success"`
- 失敗: `status: "failed"` + エラーメッセージ
- スキップ: `status: "skipped"` + スキップ理由

**ログ例**:
```json
[
  {
    "company_name": "株式会社Example1",
    "website_url": "https://example1.com",
    "contact_form_url": "https://example1.com/contact",
    "status": "success",
    "timestamp": "2026-02-04 20:30:00"
  },
  {
    "company_name": "株式会社Example2",
    "website_url": "https://example2.com",
    "contact_form_url": "https://example2.com/contact",
    "status": "failed",
    "error": "Timeout: Page load timeout",
    "timestamp": "2026-02-04 20:33:00"
  },
  {
    "company_name": "株式会社Example3",
    "website_url": "https://example3.com",
    "contact_form_url": "https://example3.com/contact",
    "status": "skipped",
    "reason": "CAPTCHA detected",
    "timestamp": "2026-02-04 20:36:00"
  }
]
```

## 実行例

### 例1: テスト送信（3社）

```
/form-sales output/sales_list_20260204_2034.json --max-sends 3
```

**結果**:
- 3社に送信
- 送信ログ生成
- 送信レポート生成

### 例2: 本番送信（100社）

```
/form-sales output/sales_list_20260204_2034.json
```

**結果**:
- 最大100社に送信（レート制限）
- 3分間隔で送信
- CAPTCHA検出時は自動スキップ
- 送信完了後にレポート生成

### 例3: カスタム送信（50社、5分間隔）

```
/form-sales output/sales_list_20260204_2034.json --max-sends 50 --delay 300
```

**結果**:
- 50社に送信
- 5分間隔で送信

## トラブルシューティング

### 問題: 送信者情報が設定されていない

**エラー**:
```
Error: 送信者情報が設定されていません。
config/sales_automation.json を編集してください。
```

**解決策**:
```bash
vim projects/sales-automation/config/sales_automation.json
```

送信者情報を追加:
```json
{
  "form_sales": {
    "sender_info": {
      "company_name": "株式会社あなたの会社",
      "contact_name": "山田太郎",
      "email": "info@yourcompany.com",
      "phone": "03-1234-5678"
    }
  }
}
```

### 問題: レート制限に達した

**エラー**:
```
レート制限に達しました。明日再実行してください。
今日の送信件数: 100/100
```

**解決策**:
- 翌日に再実行
- または `send_log.json` を削除してリセット（非推奨）

### 問題: CAPTCHAでスキップが多い

**確認**:
```bash
cat projects/sales-automation/output/send_report.md
```

**対策**:
- CAPTCHA非搭載の企業を優先的に選定
- 手動でCAPTCHA搭載企業に連絡

### 問題: フォーム検出が失敗する

**原因**:
- 問い合わせフォームURLが間違っている
- フォームが動的生成（JavaScript）

**解決策**:
- 営業リストのURLを手動修正
- フォーム検出スクリプトを改善

### 問題: 送信が失敗する

**確認**:
```bash
cat projects/sales-automation/output/send_log.json
```

**よくある原因**:
- タイムアウト: ページ読み込みが遅い
- フォーム項目の検出失敗: フォーム構造が特殊
- ネットワークエラー: 一時的な接続問題

**解決策**:
- タイムアウト時間を延長（スクリプト編集）
- 失敗した企業のみ再実行
- ネットワーク接続を確認

## パイプライン実行

営業リスト作成からフォーム送信までを一連で実行:

```bash
# 1. 営業リスト作成
/sales-list-creation "東京 IT企業" --max-companies 100

# 2. 送信者情報設定
vim projects/sales-automation/config/sales_automation.json

# 3. テスト送信
/form-sales output/sales_list_*.json --max-sends 5

# 4. 結果確認
cat projects/sales-automation/output/send_report.md

# 5. 本番送信
/form-sales output/sales_list_*.json
```

## 送信レポート例

`projects/sales-automation/output/send_report.md`:

```markdown
# フォーム送信レポート

## サマリー

- **送信対象**: 50社
- **送信成功**: 35社
- **送信失敗**: 10社
- **スキップ**: 5社（CAPTCHA検出）
- **成功率**: 70%

## 送信成功

1. 株式会社Example1 - https://example1.com/contact
2. 株式会社Example2 - https://example2.com/contact
...

## 送信失敗

1. 株式会社FailExample1 - Timeout: Page load timeout
2. 株式会社FailExample2 - Form detection failed
...

## スキップ

1. 株式会社SkipExample1 - CAPTCHA detected
2. 株式会社SkipExample2 - CAPTCHA detected
...

## 次のステップ

- 送信失敗企業を手動確認
- CAPTCHA搭載企業に手動連絡
- 成功企業からの返信を待つ
```

## 次のステップ

送信完了後:
1. **送信レポート確認**: 成功率をチェック
2. **失敗企業の対応**: 手動確認・再送信
3. **返信管理**: メールで返信を受け取る
4. **効果測定**: 返信率を計測

## 参考ファイル

- スクリプト: `projects/sales-automation/scripts/send_sales_form.py`
- 設定ファイル: `projects/sales-automation/config/sales_automation.json`
- 送信ログ: `projects/sales-automation/output/send_log.json`
- ドキュメント: `projects/sales-automation/README.md`
