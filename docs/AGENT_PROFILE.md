# エージェントプロファイル機能

エージェントごとにブラウザのログイン状態（Cookie、セッション）を保存・復元できます。

## 使い方

### 1. エージェントを登録

```bash
python -m src agent register "Google検索Agent" \
  --type search \
  --file projects/example/search.py \
  --description "Google検索を実行するエージェント"
```

これにより以下が作成されます：
- エージェント定義: `config/agents.json`
- プロファイルディレクトリ: `data/profiles/google検索agent/`

### 2. エージェントを使って調査実行

```bash
python -m src research "検索クエリ" --agent "Google検索Agent"
```

初回実行時：
- ブラウザが起動
- 手動でログイン操作を行う
- 調査完了後、自動的にCookie/セッションが保存される

2回目以降：
- 保存されたCookie/セッションを使ってログイン状態で開始
- 毎回ログインする必要なし

### 3. エージェント一覧を確認

```bash
python -m src agent list
```

出力例：
```
Name              Type      Profile Dir
Google検索Agent   search    data/profiles/google検索agent
Twitter調査Agent  scraper   data/profiles/twitter調査agent
```

### 4. エージェントを削除

```bash
# エージェント定義のみ削除
python -m src agent delete "Google検索Agent"

# プロファイル（ログイン情報）も削除
python -m src agent delete "Google検索Agent" --delete-profile
```

## プロファイルの保存内容

`data/profiles/<agent-name>/state.json` に以下が保存されます：

- Cookie
- LocalStorage
- SessionStorage
- IndexedDB（一部）

## 注意点

1. **セキュリティ**: プロファイルにはログイン情報が含まれるため、`data/profiles/` は `.gitignore` に追加推奨
2. **有効期限**: Cookieの有効期限が切れた場合は再ログインが必要
3. **複数ブラウザ**: 現在は1つのプロファイルを複数のコンテナで共有使用

## 技術詳細

### 仕組み

1. コンテナ起動時に `data/profiles/<agent-name>` をマウント
2. Playwright の `storageState` 機能で Cookie/セッション復元
3. コンテナ終了時に最新の状態を保存

### 実装箇所

- `src/agent_registry.py`: エージェント登録・管理
- `src/browser_pool.py`: プロファイルディレクトリのマウント
- `docker/browser-api/src/browserManager.ts`: storageState の保存・復元
