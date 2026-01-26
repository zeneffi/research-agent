#!/bin/bash
set -e

# ログディレクトリ作成
mkdir -p /var/log/supervisor

# 環境変数のデフォルト値設定
export DISPLAY="${DISPLAY:-:99}"
export VNC_PORT="${VNC_PORT:-5900}"
export NOVNC_PORT="${NOVNC_PORT:-6080}"
export API_PORT="${API_PORT:-3000}"

echo "Starting browser container..."
echo "  DISPLAY: $DISPLAY"
echo "  VNC_PORT: $VNC_PORT"
echo "  NOVNC_PORT: $NOVNC_PORT"
echo "  API_PORT: $API_PORT"

# コマンド実行
exec "$@"
