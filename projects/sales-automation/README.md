# Sales Automation（営業自動化）

営業リスト作成とフォーム営業を自動化するプロジェクト。

## 概要

### 1. sales-list-creation（営業リスト作成）
- DuckDuckGo検索で企業情報を自動収集（15コンテナ並列）
- 企業名、URL、問い合わせフォームURLを抽出
- カスタム項目に対応（業種に応じた情報収集）
- JSON/CSV/Markdown 3形式で出力

### 2. form-sales（フォーム営業）✅ **実装完了**
- 問い合わせフォームの自動検出・入力・送信（5コンテナ並列）
- カスタム項目に基づく営業文パーソナライゼーション
- CAPTCHA検出・レート制限（3分間隔、1日100件）
- 送信ログ・レポート生成

## 使い方

### 1. 営業リスト作成
```bash
cd projects/sales-automation
python3 scripts/create_sales_list.py "東京 IT企業" --max-companies 100
```

**出力:**
- `output/sales_list_YYYYMMDD_HHMM.json` - JSON形式
- `output/sales_list_YYYYMMDD_HHMM.csv` - CSV形式（スプレッドシート用）
- `output/sales_list_YYYYMMDD_HHMM.md` - Markdownレポート

### 2. フォーム自動送信 ✅ NEW

**設定編集:**
`config/sales_automation.json` で送信者情報を設定:
```json
{
  "form_sales": {
    "sender_info": {
      "company_name": "株式会社Example",
      "contact_name": "山田太郎",
      "email": "info@example.com",
      "phone": "03-1234-5678"
    }
  }
}
```

**実行:**
```bash
cd projects/sales-automation
python3 scripts/send_sales_form.py output/sales_list_20260204_2034.json --max-sends 10
```

**出力:**
- `output/send_log.json` - 送信ログ（JSON形式）
- `output/send_report.md` - 送信レポート（Markdown形式）

**主な機能:**
- ✅ フォーム項目の自動検出
- ✅ CAPTCHA検出（検出時は自動スキップ）
- ✅ 企業タイプ別の営業文生成（スタートアップ/IT/製造業/汎用）
- ✅ レート制限（3分間隔、1日100件）
- ✅ 詳細な送信ログ・レポート

## プロジェクト構造
```
projects/sales-automation/
├── README.md
├── config/
│   └── sales_automation.json      # 設定ファイル
├── scripts/
│   ├── create_sales_list.py       # 営業リスト作成
│   ├── send_sales_form.py         # フォーム自動送信 ✅ NEW
│   └── lib/
│       ├── browser.py             # ブラウザ操作
│       ├── search.py              # DuckDuckGo検索
│       ├── extractor.py           # 企業情報抽出
│       ├── contact_finder.py      # 問い合わせフォーム検出
│       ├── normalizer.py          # データ正規化
│       ├── output.py              # 出力処理
│       ├── form_handler.py        # フォーム操作 ✅ NEW
│       ├── message_generator.py   # 営業文生成 ✅ NEW
│       └── rate_limiter.py        # レート制限管理 ✅ NEW
├── tests/                         # テストコード ✅ NEW
│   ├── test_form_handler.py
│   ├── test_message_generator.py
│   └── test_rate_limiter.py
└── output/                        # 調査結果・送信ログ
    ├── sales_list_*.json
    ├── send_log.json              # ✅ NEW
    └── send_report.md             # ✅ NEW
```

## 技術仕様

### 検索エンジン
- **DuckDuckGo専用**（Googleは使用しない）
- URL: `https://duckduckgo.com/?q=検索クエリ`

### カスタム項目
業種に応じて自動的に以下の情報を抽出：
- **IT**: 技術スタック、開発実績、エンジニア数
- **製造業**: 主要製品、工場所在地、ISO認証
- **スタートアップ**: 調達ラウンド、調達額、調達日

### 並列処理
- 最大15コンテナで並列実行
- ThreadPoolExecutor使用

## 営業文の自動生成 ✅ NEW

企業タイプに応じて営業文を自動生成（200-300文字）:

| 企業タイプ | 判定条件 | メッセージ内容 |
|----------|---------|--------------|
| **スタートアップ** | custom_field_1に「シリーズ」「調達」等 | 資金調達に言及し、成長支援を提案 |
| **IT企業** | custom_field_1に技術名（React, Python等） | 技術スタックに言及し、技術支援を提案 |
| **製造業** | custom_field_3に「ISO」 | ISO認証・品質へのこだわりに言及 |
| **汎用** | その他 | 標準的なテンプレート |

## レート制限 ✅ NEW

- **送信間隔**: 3分（180秒）自動待機
- **日次上限**: 100件
- **並列度**: 5コンテナ（大量送信によるサーバー負荷を軽減）

## 注意事項

### 倫理的配慮 ⚠️ 重要

- **スパム行為禁止**: 無差別な大量送信は行わないでください
- **レート制限遵守**: 相手サーバーに負荷をかけないよう、適切な間隔を空けてください
- **オプトアウト対応**: 配信停止の要望があった場合は速やかに対応
- **個人情報保護**: 収集した情報は適切に管理

### テスト実施推奨

本番運用前に必ず以下を実施:

1. **少数でテスト**: まずは3-5社で動作確認
2. **送信内容確認**: 生成される営業文を事前確認
3. **CAPTCHA対応**: CAPTCHA検出時の動作確認

## 開発状況

### 営業リスト作成
- [x] Phase 1: プロジェクト構造
- [x] Phase 2: search.py 基本実装
- [x] Phase 3: extractor.py 基本実装
- [x] Phase 4: output.py（JSON/CSV/Markdown）
- [x] Phase 5: create_sales_list.py メイン処理
- [x] Phase 6: テスト（10社）

### フォーム自動送信 ✅ NEW
- [x] Phase 1: form_handler.py（フォーム検出・入力・送信）
- [x] Phase 2: message_generator.py（営業文生成）
- [x] Phase 3: rate_limiter.py（レート制限管理）
- [x] Phase 4: send_sales_form.py（メインスクリプト）
- [x] Phase 5: 単体テスト作成
- [ ] Phase 6: 統合テスト（実際のフォームでテスト）
