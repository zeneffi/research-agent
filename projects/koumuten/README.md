# 工務店業界調査・営業プロジェクト

## 概要

関東圏の工務店業界の市場調査および、LP制作サービスの営業自動化プロジェクト。

## プロジェクト構成

```
koumuten/
├── README.md
├── scripts/
│   ├── collect/              # データ収集
│   │   ├── collect_chiba_koumuten.py
│   │   ├── collect_final.py
│   │   ├── enrich_data.py
│   │   ├── extract_ibaraki.py
│   │   ├── finalize_output.py
│   │   ├── scrape_details.py
│   │   ├── scrape_koumuten.py
│   │   ├── search_urls.py
│   │   └── search_urls2.py
│   ├── process/              # データ加工
│   │   ├── clean_koumuten_data.py
│   │   ├── merge_lists.py
│   │   └── parse_koumuten.py
│   └── output/               # 出力生成
│       ├── auto_contact.py   # 自動問い合わせ
│       └── create_pptx.py    # パワポ生成
└── output/
    ├── companies/            # 企業リスト（都道府県別）
    │   ├── all_kanto.json    # 関東統合版
    │   ├── chiba.json
    │   ├── gunma.json
    │   ├── ibaraki.json
    │   ├── kanagawa.json
    │   ├── saitama.json
    │   ├── tochigi.json
    │   └── tokyo.json
    ├── koumuten_industry_report.md   # 業界調査レポート
    ├── koumuten_lp_sales_deck.pptx   # 営業パワポ
    ├── kanagawa_koumuten_report.md   # 神奈川調査レポート
    ├── tochigi_koumuten_report.md    # 栃木調査レポート
    ├── sales_deck_content.md         # パワポ内容（Markdown）
    └── sales_templates.md            # 営業文章テンプレート
```

## 成果物

### 1. 企業リスト
`output/companies/` - 関東7県の工務店リスト

| ファイル | 内容 |
|---------|------|
| all_kanto.json | 関東全県統合 |
| tokyo.json | 東京都 |
| kanagawa.json | 神奈川県 |
| chiba.json | 千葉県 |
| saitama.json | 埼玉県 |
| gunma.json | 群馬県 |
| tochigi.json | 栃木県 |
| ibaraki.json | 茨城県 |

### 2. 調査レポート
- `output/koumuten_industry_report.md` - 業界全体の調査レポート
- `output/kanagawa_koumuten_report.md` - 神奈川県調査レポート
- `output/tochigi_koumuten_report.md` - 栃木県調査レポート

### 3. 営業資料
- `output/koumuten_lp_sales_deck.pptx` - 営業パワポ（12スライド）
- `output/sales_deck_content.md` - パワポ内容（Markdown版）
- `output/sales_templates.md` - 問い合わせ・DM文章テンプレート

## スクリプト

### データ収集 (`scripts/collect/`)
| スクリプト | 用途 |
|-----------|------|
| scrape_koumuten.py | 工務店リスト収集（汎用） |
| scrape_details.py | 詳細情報スクレイピング |
| enrich_data.py | データ拡充 |
| collect_chiba_koumuten.py | 千葉県専用収集 |
| extract_ibaraki.py | 茨城県データ抽出 |
| search_urls.py | URL検索 |

### データ加工 (`scripts/process/`)
| スクリプト | 用途 |
|-----------|------|
| clean_koumuten_data.py | データクレンジング |
| parse_koumuten.py | データパース |
| merge_lists.py | リスト統合 |

### 出力生成 (`scripts/output/`)

#### 自動問い合わせ
```bash
# ドライラン（送信しない）
python scripts/output/auto_contact.py --list output/companies/all_kanto.json --dry-run --limit 5

# 実行
python scripts/output/auto_contact.py --list output/companies/all_kanto.json --execute --limit 10
```

#### パワポ生成
```bash
python scripts/output/create_pptx.py
```

## 企業リストフォーマット

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
