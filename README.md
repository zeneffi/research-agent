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
│   └── snapshot.py             # セッション保存
├── data/
│   ├── sessions/               # セッション状態
│   ├── screenshots/            # スクリーンショット
│   └── results/                # 調査結果
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

### その他のコマンド

```bash
# ステータス確認
python -m src.cli status

# セッション一覧
python -m src.cli list

# セッション再開
python -m src.cli resume セッション名

# コンテナ停止
python -m src.cli stop
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
