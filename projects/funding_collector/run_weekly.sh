#!/bin/bash
# 週次資金調達企業収集スクリプト
# cron設定例: 0 9 * * 1 /path/to/run_weekly.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOCKER_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)/docker"
LOG_FILE="$SCRIPT_DIR/logs/collect_$(date +%Y%m%d).log"

mkdir -p "$SCRIPT_DIR/logs"

echo "=== 資金調達企業収集開始: $(date) ===" >> "$LOG_FILE"

# Dockerコンテナ起動
cd "$DOCKER_DIR"
docker compose up -d --scale browser=10 >> "$LOG_FILE" 2>&1

# 起動待ち
sleep 20

# 収集実行
cd "$SCRIPT_DIR"
python collect_multi_source.py >> "$LOG_FILE" 2>&1

# コンテナ停止
cd "$DOCKER_DIR"
docker compose down >> "$LOG_FILE" 2>&1

echo "=== 収集完了: $(date) ===" >> "$LOG_FILE"

# Slack通知（オプション）
# curl -X POST -H 'Content-type: application/json' \
#   --data "{\"text\":\"資金調達企業収集完了: $(date)\"}" \
#   "$SLACK_WEBHOOK_URL"
