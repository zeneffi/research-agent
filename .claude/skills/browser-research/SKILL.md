---
name: browser-research
description: Dockerコンテナで起動した並列ブラウザを使用してWeb調査を行う。複数の調査対象を並列で処理し、結果を統合する。「○○社を比較調査」「複数サイトから情報収集」などのタスクで使用する。
---

# Browser Research Skill

Dockerコンテナで起動した並列ブラウザを使用してWeb調査を行う。

## 概要

`daytona-agent/docker`のコンテナを起動し、browser-api（HTTP API）を通じて複数のブラウザを並列操作する。

---

## マルチアクション実行ルール

### タスク分解の原則

**1項目につき1コンテナ** - 調査対象ごとにコンテナを割り当てる

| リクエスト例 | タスク分解 |
|-------------|-----------|
| 「競合他社5社を比較」 | 企業ごとに1コンテナ（計5コンテナ） |
| 「10カ国の原子力発電を調査」 | 国ごとに1コンテナ（計10コンテナ） |
| 「AI、量子、バイオの最新動向」 | 分野ごとに1コンテナ（計3コンテナ） |
| 「製品A, B, Cの価格比較」 | 製品ごとに1コンテナ（計3コンテナ） |

### マルチアクション実行フロー

```
1. クエリ解析 → 調査項目を抽出（例: 5社、10カ国、3製品）
2. 項目数に応じてコンテナを起動（--scale browser=N）
3. 各コンテナに1項目を割り当て → 並列でナビゲート
4. 全コンテナから結果を収集
5. 統合タスク: 結果を比較/分析してまとめる
```

### 判定基準

**並列実行する場合（マルチアクション）:**

- 個別にリサーチすべき項目が3つ以上ある
- 比較分析（XとYとZを比較）
- データ収集（複数ソースからの情報収集）

**単一実行する場合:**

- 単一トピックの深掘り（「量子コンピューティングについて詳しく」）
- 単純な事実確認、定義の検索
- フォローアップ質問

---

## 前提条件

- Docker Desktopが起動していること
- `daytona-agent/docker`でイメージがビルド済みであること

## 実行手順

### 1. Dockerコンテナの起動/接続

```bash
cd /Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/docker
docker compose up -d --scale browser=5
```

### 2. コンテナのポート確認

```bash
docker compose ps
```

各コンテナのAPIポート（3000番台）を確認する。

### 3. ブラウザ操作（HTTP API）

各コンテナのbrowser-apiに対してHTTPリクエストを送信：

#### ページナビゲーション

```bash
curl -X POST http://localhost:<port>/browser/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

#### スナップショット取得（ページ内容）

```bash
curl -X POST http://localhost:<port>/browser/snapshot
```

#### スクリーンショット

```bash
curl -X POST http://localhost:<port>/browser/screenshot \
  -H "Content-Type: application/json" \
  -d '{"fullPage": true}'
```

#### クリック

```bash
curl -X POST http://localhost:<port>/browser/click \
  -H "Content-Type: application/json" \
  -d '{"text": "クリックするテキスト"}'
```

#### テキスト入力

```bash
curl -X POST http://localhost:<port>/browser/type \
  -H "Content-Type: application/json" \
  -d '{"selector": "input[name=q]", "text": "検索クエリ", "submit": true}'
```

#### ページコンテンツ取得

```bash
curl -X POST http://localhost:<port>/browser/content
```

### 4. 並列調査の実行フロー

1. **タスク分解**: 調査クエリを複数のURLに分解
2. **並列実行**: 各コンテナに異なるURLを割り当てて同時にナビゲート
3. **結果収集**: 各コンテナからスナップショット/コンテンツを取得
4. **集約**: 結果をMarkdown/JSONにまとめる

## noVNCでブラウザ画面を確認

各コンテナの6080番ポートでnoVNCにアクセス可能：

```
http://localhost:<novnc_port>
```

### 気を効かせたクエリ解析

- ユーザの伝えたクエリをそのまま使わずに、検索可能なワードに分解/変換する
- 最終出力を想定しながら、考える。不明な点はユーザに尋ねる。
- 本日の時間を意識してクエリを使う。(dateコマンドを使用する)

### タスク分解の原則

**1項目につき1コンテナ** - 調査対象ごとにコンテナを割り当てる

| リクエスト例 | タスク分解 |
|-------------|-----------|
| 「競合他社5社を比較」 | 企業ごとに1コンテナ（計5コンテナ） |
| 「10カ国の原子力発電を調査」 | 国ごとに1コンテナ（計10コンテナ） |
| 「AI、量子、バイオの最新動向」 | 分野ごとに1コンテナ（計3コンテナ） |
| 「製品A, B, Cの価格比較」 | 製品ごとに1コンテナ（計3コンテナ） |

### 検索能力

デフォルトの検索は絶対に使わない

- playwright
- WebSearch
を使わない

### サンドボックス思考

- サンドボックスをうまく使うことで、検索を行う
- 必要に応じて、pythonやnode.jsを使って適切なビジュアライゼーションをしてOK
- データ分析などの操作も勿論OK
- sandbox-operationsのスキルを使っても良い

### 100%理解できる出力

- 出力内容はただの結果の羅列ではなくて、インサイトを含む内容であるべき
- とにかくわかりやすい内容であるべき
- マークダウンファイルとして出力すること。
