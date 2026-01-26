#!/bin/bash
# 調査実行スクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== プロジェクト調査開始 ==="
echo "Project: $PROJECT_DIR"

# ここに調査ロジックを記載

echo "=== 完了 ==="
