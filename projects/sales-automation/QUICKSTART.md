# Form-Sales クイックスタートガイド

## 5分で始める自動フォーム送信

### Step 1: 送信者情報を設定（1分）

```bash
vim config/sales_automation.json
```

以下を編集:
```json
{
  "form_sales": {
    "sender_info": {
      "company_name": "あなたの会社名",
      "contact_name": "あなたの名前",
      "email": "your-email@example.com",
      "phone": "000-0000-0000"
    }
  }
}
```

### Step 2: 営業リストを準備（1分）

既存の営業リストを使用:
```bash
ls output/sales_list_*.json
```

または新規作成:
```bash
python3 scripts/create_sales_list.py "東京 IT企業" --max-companies 10
```

### Step 3: テスト実行（3分）

**重要**: まず3社でテスト!

```bash
python3 scripts/send_sales_form.py output/sales_list_*.json --max-sends 3
```

実行中の表示例:
```
==============================================================
フォーム営業スクリプト
==============================================================

[1/5] 営業リスト読み込み中...
  読み込み完了: 100社

送信者情報: あなたの会社名 / あなたの名前

[2/5] ブラウザコンテナ確認中...
  利用可能なブラウザコンテナ: 5個

[3/5] フォーム送信中...
  レート制限: 180秒間隔、1日100件

  ✓ 株式会社Example1 - success
  180秒待機中...
  ⊘ 株式会社Example2 - skipped (CAPTCHA detected)
  180秒待機中...
  ✓ 株式会社Example3 - success

[4/5] レポート生成中...
  レポート生成完了

[5/5] 完了サマリー
  - 総数: 3社
  - 成功: 2社
  - 失敗: 0社
  - スキップ: 1社

==============================================================
完了!
==============================================================
  - 送信ログ: output/send_log.json
  - レポート: output/send_report.md
```

### Step 4: 結果確認（1分）

```bash
# レポート確認
cat output/send_report.md

# ログ確認
cat output/send_log.json
```

## 送信結果の見方

### send_report.md

```markdown
# フォーム営業 送信結果レポート

実行日時: 2026年2月5日 10:30

## サマリー

| 指標 | 値 |
|-----|-----|
| **総数** | 3社 |
| **成功** | 2社 |
| **失敗** | 0社 |
| **スキップ** | 1社 |
| **成功率** | 66.7% |

---

## 送信成功

### 1. 株式会社Example1

- **URL**: https://example1.com/contact
- **送信日時**: 2026-02-05T10:05:00Z
- **検出フィールド**: company, name, email, message
- **メッセージ**: 突然のご連絡失礼いたします。シリーズAで5億円の調達おめでとう...

### 2. 株式会社Example3

- **URL**: https://example3.com/contact
- **送信日時**: 2026-02-05T10:11:00Z
- **検出フィールド**: name, email, phone, message
- **メッセージ**: 貴社がReact, Pythonを活用されていることを拝見しました...

---

## スキップ

### 1. 株式会社Example2

- **URL**: https://example2.com/contact
- **理由**: CAPTCHA detected
- **日時**: 2026-02-05T10:08:00Z
```

## よくある質問

### Q1. 送信間隔を変更したい

`config/sales_automation.json` を編集:

```json
{
  "form_sales": {
    "rate_limit": {
      "interval_seconds": 300  // 5分に変更（デフォルト: 180秒）
    }
  }
}
```

### Q2. 1日の送信上限を変更したい

```json
{
  "form_sales": {
    "rate_limit": {
      "daily_limit": 50  // 50件に変更（デフォルト: 100件）
    }
  }
}
```

### Q3. 送信がスキップされる理由は?

以下の場合、自動的にスキップされます:

- **CAPTCHA検出**: reCAPTCHA/hCaptchaが存在
- **フォーム未検出**: 問い合わせフォームが見つからない
- **URL無し**: contact_form_urlが空

### Q4. 送信速度を上げたい

並列度を上げても、レート制限（3分間隔）があるため、速度はあまり変わりません。

**計算例:**
- 100社送信 = 3分 × 100 ÷ 5コンテナ = 約60分（1時間）
- 間隔を1分に短縮 = 1分 × 100 ÷ 5コンテナ = 約20分

⚠️ **注意**: 間隔を短くしすぎると、サーバー負荷が高まり、CAPTCHA検出される可能性が高まります。

### Q5. エラーで停止した場合は?

ログを確認:
```bash
cat output/send_log.json
```

エラー内容に応じて対応:
- **Navigation failed**: URLが無効、またはサイトがダウン
- **Timeout**: サイトの応答が遅い（120秒でタイムアウト）
- **Form not detected**: フォーム構造が特殊（手動確認が必要）

## 本番運用のヒント

### 1. 時間帯を考慮

営業時間内（9-18時）に送信することを推奨:

```bash
# cronで平日9時に実行（例）
0 9 * * 1-5 cd /path/to/sales-automation && python3 scripts/send_sales_form.py output/sales_list.json --max-sends 20
```

### 2. 送信数を分散

一度に大量送信するのではなく、少しずつ:

```bash
# 朝: 10社
python3 scripts/send_sales_form.py output/sales_list.json --max-sends 10

# 昼: 10社
python3 scripts/send_sales_form.py output/sales_list.json --max-sends 10

# 夕方: 10社
python3 scripts/send_sales_form.py output/sales_list.json --max-sends 10
```

### 3. 送信履歴の管理

`send_log.json` をバックアップ:

```bash
# 日付別にバックアップ
cp output/send_log.json output/send_log_$(date +%Y%m%d).json
```

### 4. 成功率の監視

```bash
# 成功率を確認
python3 -c "
import json
with open('output/send_log.json') as f:
    data = json.load(f)
    s = data['summary']
    print(f'成功率: {s[\"success\"]/s[\"total\"]*100:.1f}%')
    print(f'成功: {s[\"success\"]}社')
    print(f'失敗: {s[\"failed\"]}社')
    print(f'スキップ: {s[\"skipped\"]}社')
"
```

## トラブルシューティング

### Dockerコンテナが起動していない

```bash
cd docker
docker compose up -d
docker compose ps  # 確認
```

### モジュールが見つからない

```bash
# 正しいディレクトリで実行しているか確認
pwd
# /Users/.../research-agent であるべき

cd projects/sales-automation
python3 scripts/send_sales_form.py ...
```

### 設定ファイルが見つからない

```bash
# 設定ファイルの存在確認
ls config/sales_automation.json

# 存在しない場合は作成
cp config/sales_automation.json.example config/sales_automation.json
```

## 倫理的配慮 ⚠️

**必ず守ってください:**

1. **スパム禁止**: 無差別な大量送信は絶対に行わない
2. **オプトアウト対応**: 配信停止の要望には即座に対応
3. **レート制限遵守**: サーバーに負荷をかけない
4. **個人情報保護**: 収集データを適切に管理

**推奨事項:**

- 送信前に営業文の内容を確認
- 相手企業のビジネスに関連する提案のみ
- 初回は少数（3-5社）でテスト
- 返信率・反応を確認しながら調整

## サポート

問題が発生した場合:

1. `IMPLEMENTATION_SUMMARY.md` を確認
2. `README.md` の詳細ドキュメントを確認
3. `output/send_log.json` でエラー内容を確認

---

**Happy Automation! 🚀**
