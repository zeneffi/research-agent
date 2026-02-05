# フォーム検出テストガイド

## 概要

`test_form_detection.py` は、営業リストの企業に対してフォーム検出のみを実行するテストスクリプトです。実際の送信は行わず、以下をテストします:

- 問い合わせフォームの検出
- フォーム項目の認識
- CAPTCHA の検出

## 目的

本番送信前に以下を確認するために使用します:

1. ✅ フォーム項目が正しく検出されるか
2. ✅ CAPTCHA検出が正しく動作するか
3. ✅ エラーハンドリングが適切か
4. ✅ 検出失敗の原因特定

## 使い方

### 基本的な使用方法

```bash
# Dockerコンテナを起動（プロジェクトルートからの相対パス）
cd ../../docker
docker compose up -d

# sales-automationディレクトリに移動
cd ../projects/sales-automation

# 最大10社をテスト（デフォルト）
python3 scripts/test_form_detection.py output/sales_list_20260204_2034.json

# 最大5社のみテスト
python3 scripts/test_form_detection.py output/sales_list_20260204_2034.json --max-tests 5

# 全社をテスト
python3 scripts/test_form_detection.py output/sales_list_20260204_2034.json --max-tests 100
```

### オプション

| オプション | 説明 | デフォルト |
|----------|------|----------|
| `list_file` | 営業リストのJSONファイルパス | 必須 |
| `--max-tests` | 最大テスト件数 | 10 |

## 出力

### 実行中の表示

```
============================================================
フォーム検出テスト
============================================================

[1/4] 営業リスト読み込み中...
  総数: 50社
  フォームURL有り: 45社

[2/4] ブラウザコンテナ確認中...
  利用可能: 15個

[3/4] フォーム検出テスト中（最大10社）...
  [1/10] 株式会社サンプル... ✓ detected
  [2/10] テスト工務店... ⚠ has_captcha
  [3/10] 例示株式会社... ✗ not_detected
  ...

[4/4] レポート生成中...
  レポート: output/form_detection_test_20260204_2130.md

============================================================
完了!
============================================================
  検出成功: 7社
  CAPTCHA検出: 2社
  検出失敗: 1社

⚠️  注意: このテストは検出のみで、実際の送信は行っていません
```

### ステータス記号

| 記号 | ステータス | 意味 |
|-----|----------|------|
| ✓ | detected | フォーム検出成功 |
| ⚠ | has_captcha | CAPTCHA検出（フォームは検出済み） |
| ✗ | not_detected / failed | フォーム検出失敗またはエラー |
| ⊘ | skipped | スキップ（フォームURLなし） |

### レポートファイル

実行後、`output/form_detection_test_YYYYMMDD_HHMM.md` が生成されます。

レポートの構成:

1. **サマリー**: 検出成功率、CAPTCHA検出率などの統計
2. **検出成功**: フィールド一覧と詳細
3. **CAPTCHA検出**: CAPTCHA有りの企業一覧
4. **検出失敗**: 失敗理由を含む一覧

## レポート例

```markdown
# フォーム検出テスト結果

実行日時: 2026年02月04日 21:30

## サマリー

| 項目 | 件数 | 割合 |
|-----|------|------|
| **総数** | 10社 | 100.0% |
| **検出成功** | 7社 | 70.0% |
| **CAPTCHA検出** | 2社 | 20.0% |
| **検出失敗** | 1社 | 10.0% |
| **エラー** | 0社 | 0.0% |
| **スキップ** | 0社 | 0.0% |

---

## 検出成功

### 1. 株式会社サンプル

- **URL**: https://example.com/contact
- **検出フィールド**: company, name, email, phone, message
- **CAPTCHA**: なし

...
```

## トラブルシューティング

### Dockerコンテナが起動していない

```
エラー: Dockerコンテナが起動していません
docker compose up -d で起動してください
```

**解決方法:**
```bash
cd ../../docker
docker compose up -d
```

### フォーム検出が失敗する

**原因:**
- フォーム構造が特殊（JavaScript動的生成など）
- ページ読み込みが完了していない
- アクセス制限（IP制限、地域制限など）

**対策:**
- レポートの「検出失敗」セクションで理由を確認
- 実際にブラウザで該当URLを開いて構造を確認
- タイムアウト時間を延長（`browser.py`のtimeout調整）

### CAPTCHA検出される

CAPTCHA検出は正常な動作です。本番送信時は自動的にスキップされます。

## 次のステップ

フォーム検出テストで問題がなければ:

1. **送信者情報を更新**
   ```bash
   # config/sales_automation.json を編集
   vi config/sales_automation.json
   ```

2. **少数で実際の送信テスト**
   ```bash
   # 3社のみ送信テスト
   python3 scripts/send_sales_form.py output/sales_list_20260204_2034.json --max-sends 3
   ```

3. **本番運用開始**
   ```bash
   # 全社送信（レート制限あり）
   python3 scripts/send_sales_form.py output/sales_list_20260204_2034.json
   ```

## 注意事項

### 重要

- ⚠️ **このスクリプトは検出のみを実行し、実際の送信は行いません**
- ⚠️ **実際の送信は `send_sales_form.py` を使用してください**
- ⚠️ **CAPTCHA検出された企業は、本番送信時に自動スキップされます**

### テスト範囲

- デフォルトで最大10社をテストします
- 全社テストする場合は `--max-tests` で件数を指定してください
- 1コンテナのみを使用するため、処理は順次実行されます

### レート制限

このテストスクリプトにはレート制限がありません。本番送信時のみレート制限（3分間隔、1日100件）が適用されます。

## 技術詳細

### 使用モジュール

- `lib/browser.py` - get_container_ports(), browser_navigate()
- `lib/form_handler.py` - detect_form_fields(), detect_captcha()

### 検出ロジック

1. **ページナビゲート**: 30秒タイムアウト
2. **CAPTCHA検出**: reCAPTCHA/hCaptcha/data-sitekey属性をチェック
3. **フォーム項目検出**:
   - name属性パターンマッチング
   - 可視性チェック（display: none等を除外）
   - 最低限messageフィールドが必要

### 検出フィールド

| フィールド | セレクタ例 |
|-----------|-----------|
| company | `input[name*="company"]`, `input[name*="会社"]` |
| name | `input[name*="name"]`, `input[name*="氏名"]` |
| email | `input[type="email"]`, `input[name*="mail"]` |
| phone | `input[name*="tel"]`, `input[name*="phone"]` |
| message | `textarea`, `textarea[name*="message"]` |

## 関連ドキュメント

- [営業自動化システム要件](../../docs/SALES_AUTOMATION_REQUIREMENTS.md)
- [send_sales_form.py](scripts/send_sales_form.py) - 本番送信スクリプト
- [form_handler.py](scripts/lib/form_handler.py) - フォーム処理モジュール
