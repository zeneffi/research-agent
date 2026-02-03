# 資金調達企業収集システム

受託開発の営業リスト作成のため、資金調達直後のスタートアップ企業を自動収集するシステム。

---

## クイックスタート

```bash
# 1. Dockerコンテナ起動（リポジトリルートから）
cd docker
docker compose up -d --scale browser=10

# 2. 収集実行
cd projects/funding_collector
python collect_multi_source.py

# 3. コンテナ停止
cd ../../docker
docker compose down
```

---

## 100社集めるためのTips

### 1. 定期収集で蓄積する（最重要）

1回の収集では50-80社程度が限界。**週次で定期実行し、データを蓄積**することで100社以上を達成できる。

```bash
# crontab設定（毎週月曜9時）
0 9 * * 1 /path/to/funding_collector/run_weekly.sh
```

### 2. 検索キーワードを増やす

`collect_multi_source.py`の`PRTIMES_KEYWORDS`に追加：

```python
PRTIMES_KEYWORDS = [
    "資金調達",
    "シリーズA 調達",
    "シリーズB 調達",
    "第三者割当増資",
    "スタートアップ 億円",
    # 追加キーワード
    "エクイティ調達",
    "デット調達",
    "ファイナンス完了",
    "増資 完了",
    "累計調達",
]
```

### 3. 時間範囲を広げる

直近3ヶ月→6ヶ月→12ヶ月に拡大すると対象企業が増える。

```python
CONFIG = {
    "months_back": 12,  # 1年間
}
```

### 4. 複数ソースを活用

PR TIMESだけでなく、以下のソースも追加：

| ソース | URL | 特徴 |
|--------|-----|------|
| INITIAL | <https://initial.inc> | 有料だが網羅的 |
| STARTUP DB | <https://startup-db.com> | 無料プランあり |
| BRIDGE | <https://thebridge.jp> | スタートアップ特化メディア |
| TechCrunch Japan | <https://jp.techcrunch.com> | 大型調達中心 |

### 5. 手動追加との併用

自動収集で漏れた企業は手動でJSONに追加：

```json
{
  "company": "〇〇株式会社",
  "amount": 5,
  "round": "シリーズA",
  "business": "〇〇サービス",
  "url": "https://example.com",
  "source_url": "https://prtimes.jp/..."
}
```

### 6. ノイズフィルタリング

収集後に以下を除外：

- 調達額200億円超（ユニコーン以外は怪しい）
- 「シリーズ」が書籍やTV番組の場合
- 海外企業（日本拠点がない）

---

## ファイル構成

```
funding_collector/
├── README.md                    # このファイル
├── collect_funding.py           # 基本版スクリプト
├── collect_funding_v2.py        # 改良版
├── collect_multi_source.py      # マルチソース版（推奨）
├── run_weekly.sh                # 週次実行スクリプト
├── funding_list_master.json     # 統合データ
├── funding_list_final.md        # 最終レポート
└── logs/                        # 実行ログ
```

---

## 出力形式

### JSON

```json
{
  "metadata": {
    "created_at": "2026-02-04T07:31:00",
    "total_count": 74
  },
  "companies": [
    {
      "company": "CommerceXホールディングス",
      "amount": 17.3,
      "round": "シリーズA",
      "business": "リテールDXインフラ",
      "location": "大阪府吹田市",
      "ceo": "佐藤秀平",
      "url": "https://commercex.co.jp/",
      "investors": "ニッセイ・キャピタル、DUAL BRIDGE CAPITAL...",
      "source_url": "https://prtimes.jp/..."
    }
  ]
}
```

### Markdown

企業をカテゴリ別・優先度別に整理したレポート。

---

## 営業活用Tips

### 1. 最適なタイミング

資金調達発表から**2週間〜2ヶ月**がゴールデンタイム。

- 2週間以内: 社内体制整備中で忙しい
- 2ヶ月以降: 開発チーム採用が進んでいる可能性

### 2. アプローチ優先順位

1. **シリーズA（3-15億円）**: 開発投資フェーズ、外注ニーズ最大
2. **プレシリーズA/シード**: 予算少なめだが意思決定早い
3. **シリーズB以降**: 内製化志向強いが大型案件の可能性

### 3. 提案のポイント

| 企業フェーズ | 刺さる提案 |
|-------------|-----------|
| シードA | MVP開発、技術選定支援 |
| シリーズA | 機能拡張、スケーラビリティ対応 |
| シリーズB | 技術負債解消、リアーキテクチャ |
| シリーズC以降 | セキュリティ強化、内製支援 |

### 4. 事前調査必須項目

- [ ] 技術スタック（Wantedly、GitHubから推測）
- [ ] エンジニア採用状況（求人ページ確認）
- [ ] 投資家（VCネットワークで紹介可能か）
- [ ] 競合との差別化ポイント

### 5. 連絡方法の優先順位

1. **VC経由紹介**: 最も効果的
2. **LinkedIn**: CTO/VPoEへ直接
3. **採用ページ「カジュアル面談」**: ハードル低い
4. **問い合わせフォーム**: 返信率低め

---

## トラブルシューティング

### コンテナが起動しない

```bash
docker compose down
docker rm -f $(docker ps -aq)  # 全コンテナ削除
docker compose up -d --scale browser=10
```

### 収集数が少ない

- ページ数を増やす（1-15 → 1-30）
- キーワードを追加
- DuckDuckGo検索も併用

### タイムアウトエラー

- `timeout`パラメータを増やす
- コンテナ数を減らす（10→5）

---

## 今後の改善案

1. **INITIAL API連携**: 有料だが網羅的なデータ取得
2. **Slack/メール通知**: 新規調達企業の即時通知
3. **CRM連携**: Salesforce/HubSpotへの自動登録
4. **重複排除の強化**: 会社名の表記ゆれ対応
5. **スコアリング**: 営業優先度の自動算出

---

## 参考リンク

- [PR TIMES](https://prtimes.jp/)
- [INITIAL](https://initial.inc/)
- [STARTUP DB](https://startup-db.com/)
- [BRIDGE](https://thebridge.jp/)

---

*Last updated: 2026-02-04*
