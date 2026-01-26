# 工務店業界調査・営業プロジェクト

## 概要

工務店業界の市場調査および、LP制作サービスの営業自動化プロジェクト

## プロジェクト構成

```
koumuten/
├── README.md                      # このファイル
├── scripts/
│   ├── create_pptx.py            # パワポ生成スクリプト
│   └── auto_contact.py           # 自動問い合わせスクリプト
└── output/
    ├── koumuten_industry_report.md  # 業界調査レポート
    ├── sales_templates.md           # 営業文章テンプレート
    ├── sales_deck_content.md        # パワポ内容（Markdown）
    ├── koumuten_lp_sales_deck.pptx  # 営業パワポ
    └── companies/                   # 企業リスト（JSON）
```

## 成果物

### 1. 業界調査レポート
`output/koumuten_industry_report.md`
- 工務店業界の市場規模
- ビジネスモデル・収益構造
- 業界の課題
- LP制作サービス提案のポイント

### 2. 営業文章テンプレート
`output/sales_templates.md`
- 問い合わせフォーム用（3パターン）
- Instagram DM用（3パターン）
- フォローアップメール

### 3. 営業資料（パワポ）
`output/koumuten_lp_sales_deck.pptx`
- 12スライド構成
- 課題提起 → 解決策 → 実績 → 料金 → CTA

### 4. 自動問い合わせスクリプト
`scripts/auto_contact.py`

#### 使用方法
```bash
# ドライラン（実際には送信しない）
python scripts/auto_contact.py --list output/companies/all.json --dry-run --limit 5

# 実行（実際に送信）
python scripts/auto_contact.py --list output/companies/all.json --execute --limit 10
```

#### オプション
| オプション | 説明 |
|-----------|------|
| `--list` | 企業リストJSONファイルパス（必須） |
| `--dry-run` | 送信せずにテスト（デフォルト） |
| `--execute` | 実際に送信 |
| `--limit N` | N社まで処理 |
| `--headed` | ブラウザを表示 |

## 企業リストのフォーマット

```json
[
  {
    "name": "株式会社○○工務店",
    "prefecture": "東京都",
    "city": "渋谷区",
    "url": "https://example.com",
    "contact_url": "https://example.com/contact",
    "instagram": "https://instagram.com/xxx",
    "features": ["高性能住宅", "自然素材"]
  }
]
```

## 注意事項

- 問い合わせフォームへの自動送信は、相手サーバーへの負荷を考慮し適度な間隔を空けてください
- 送信内容がスパムにならないよう、適切な内容で送信してください
- 大量送信は法的リスクがあるため、送信先の規約を確認してください

---

*作成日: 2026年1月26日*
