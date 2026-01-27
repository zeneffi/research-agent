# Daytona Agent

並列ブラウザ調査AIエージェント - 最大15個のブラウザを同時に起動してWeb調査を行う

## 概要

Daytona Agentは、Dockerコンテナ内で複数のブラウザを並列起動し、効率的にWeb調査を行うためのツールです。

### 特徴

- **並列ブラウザ**: 最大15個のブラウザを同時に起動
- **VNC対応**: noVNCでブラウザ操作を可視化
- **セッション管理**: 調査の中断・再開が可能
- **スクリーンショット**: 各ステップの画面を保存
- **結果エクスポート**: JSON/Markdown形式で結果を保存
- **エージェントプロファイル**: ログイン状態を保存・復元（毎回ログイン不要）

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│  CLI (Python)                                                    │
│  └── Orchestrator                                                │
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│ Browser #1    │       │ Browser #2    │  ...  │ Browser #15   │
│ (Docker)      │       │ (Docker)      │       │ (Docker)      │
│ ├── Playwright│       │ ├── Playwright│       │ ├── Playwright│
│ └── VNC/NoVNC │       │ └── VNC/NoVNC │       │ └── VNC/NoVNC │
└───────────────┘       └───────────────┘       └───────────────┘
```

## ディレクトリ構成

```
daytona-agent/
├── docker/
│   ├── Dockerfile              # Playwright + VNC環境
│   ├── docker-compose.yaml     # 並列コンテナ管理
│   ├── supervisord.conf        # プロセス管理
│   ├── entrypoint.sh           # 起動スクリプト
│   └── browser-api/            # ブラウザ操作API
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── index.ts        # APIサーバー
│           └── browserManager.ts
├── src/
│   ├── __init__.py
│   ├── cli.py                  # CLIエントリポイント
│   ├── orchestrator.py         # タスク管理
│   ├── browser_pool.py         # コンテナプール管理
│   ├── task_parser.py          # クエリ解析
│   ├── snapshot.py             # セッション保存
│   └── agent_registry.py       # エージェント管理
├── config/
│   ├── agents.json             # エージェント定義
│   └── agents.example.json     # サンプル
├── data/
│   ├── sessions/               # セッション状態
│   ├── screenshots/            # スクリーンショット
│   ├── profiles/               # エージェントプロファイル（ログイン情報）
│   └── results/                # 調査結果
├── docs/
│   └── AGENT_PROFILE.md        # エージェント機能の詳細
├── requirements.txt
└── README.md
```

## セットアップ

### 前提条件

- Docker Desktop
- Python 3.10以上

### インストール

```bash
# リポジトリをクローン
cd daytona-agent

# Dockerイメージをビルド
cd docker
docker-compose build
cd ..

# Python依存関係をインストール
pip install -r requirements.txt
```

## 使用方法

### 基本的な調査

```bash
python -m src.cli research "調査したいトピック"
```

### オプション

```bash
# 並列数を指定（デフォルト: 5）
python -m src.cli research "AI最新動向" --parallel 10

# スクリーンショットを保存
python -m src.cli research "技術比較" --screenshot

# セッション名を指定
python -m src.cli research "市場調査" --session my-research

# 出力ディレクトリを指定
python -m src.cli research "競合分析" --output ./results
```

### エージェント管理（ログイン状態の保存）

```bash
# エージェントを登録
python -m src agent register "Google検索Agent" \
  --type search \
  --file projects/example/search.py \
  --description "Google検索エージェント"

# エージェントを使って調査（ログイン状態が自動保存される）
python -m src research "検索クエリ" --agent "Google検索Agent"

# エージェント一覧
python -m src agent list

# エージェント削除（プロファイルも削除する場合は --delete-profile）
python -m src agent delete "Google検索Agent"
```

詳細は [docs/AGENT_PROFILE.md](docs/AGENT_PROFILE.md) を参照。

### その他のコマンド

```bash
# ステータス確認
python -m src status

# セッション一覧
python -m src list

# セッション再開
python -m src resume セッション名

# コンテナ停止
python -m src stop
```

## 出力ファイル

- `data/results/{session}.json` - 構造化された調査結果
- `data/results/{session}.md` - Markdownサマリー
- `data/screenshots/{session}/` - スクリーンショット
- `data/sessions/{session}.json` - セッション状態

## 開発

### テスト実行

```bash
pytest
```

### コードフォーマット

```bash
black src/
ruff check src/
```

### 型チェック

```bash
mypy src/
```

## ライセンス

MIT License
