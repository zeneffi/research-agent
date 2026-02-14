#!/bin/bash
# 営業パイプライン cron用ランチャー
# cronジョブから呼ばれて、パイプラインをバックグラウンドで起動する
#
# 使い方:
#   ./cron_launcher.sh "検索クエリ" [リスト件数] [送信上限]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"

QUERY="${1:-東京 システム開発会社 受託}"
MAX_COMPANIES="${2:-20}"
MAX_SENDS="${3:-15}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/tmp/pipeline_${TIMESTAMP}.log"

cd "$REPO_DIR"

# venv有効化
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# バックグラウンドで起動
nohup "$SCRIPT_DIR/run_pipeline.sh" "$QUERY" "$MAX_COMPANIES" "$MAX_SENDS" --cleanup > "$LOG_FILE" 2>&1 &
PID=$!

echo "✅ パイプラインをバックグラウンドで起動しました"
echo "   PID: $PID"
echo "   ログ: $LOG_FILE"
echo "   結果は後ほどSlackに通知されます"
