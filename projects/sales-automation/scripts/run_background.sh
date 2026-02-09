#!/bin/bash
# 営業リスト作成 バックグラウンド実行スクリプト
# 使い方: ./run_background.sh "検索クエリ" [件数]
#
# 実行例:
#   ./run_background.sh "東京 SaaS企業" 50
#   nohup ./run_background.sh "AI スタートアップ" 100 &

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$(dirname "$PROJECT_DIR")")"

QUERY="${1:-東京 IT企業}"
MAX_COMPANIES="${2:-50}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$PROJECT_DIR/logs"
OUTPUT_DIR="$PROJECT_DIR/output"
LOG_FILE="$LOG_DIR/run_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"
mkdir -p "$OUTPUT_DIR"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Slack通知（clawdbotのメッセージツール経由）
notify() {
    local msg="$1"
    # clawdbotが動いていればSlack通知（なければスキップ）
    if command -v clawdbot &> /dev/null; then
        clawdbot message send --channel slack --target "channel:C0ACWUVSRR9" --message "$msg" 2>/dev/null || true
    fi
}

log "======================================"
log "営業リスト作成 開始"
log "クエリ: $QUERY"
log "目標件数: $MAX_COMPANIES"
log "======================================"

notify "🚀 営業リスト作成開始: \`$QUERY\` (${MAX_COMPANIES}社)"

cd "$REPO_DIR"

# venv有効化
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 環境変数確認
if [ -z "$OPENAI_API_KEY" ]; then
    if [ -f "$HOME/.config/clawdbot-secrets/openai-api-key" ]; then
        export OPENAI_API_KEY=$(cat "$HOME/.config/clawdbot-secrets/openai-api-key")
    fi
fi

# メイン実行
log "リスト作成実行中..."
if python "$SCRIPT_DIR/create_sales_list.py" "$QUERY" --max-companies "$MAX_COMPANIES" 2>&1 | tee -a "$LOG_FILE"; then
    # 成功
    RESULT_FILE=$(ls -t "$OUTPUT_DIR"/sales_list_*.json 2>/dev/null | head -1)
    
    if [ -n "$RESULT_FILE" ] && [ -f "$RESULT_FILE" ]; then
        COMPANY_COUNT=$(python3 -c "import json; data=json.load(open('$RESULT_FILE')); print(len(data.get('companies', data)) if isinstance(data, dict) else len(data))" 2>/dev/null || echo "?")
        FORM_COUNT=$(python3 -c "import json; data=json.load(open('$RESULT_FILE')); companies=data.get('companies', data) if isinstance(data, dict) else data; print(len([c for c in companies if c.get('contact_form_url')]))" 2>/dev/null || echo "?")
        
        log "======================================"
        log "✅ 完了"
        log "収集企業数: $COMPANY_COUNT"
        log "フォーム検出: $FORM_COUNT"
        log "出力: $RESULT_FILE"
        log "======================================"
        
        notify "✅ 営業リスト作成完了
• クエリ: \`$QUERY\`
• 収集: **${COMPANY_COUNT}社**
• フォーム検出: **${FORM_COUNT}件**
• ファイル: \`$(basename "$RESULT_FILE")\`"
    else
        log "⚠️ 出力ファイルが見つかりません"
        notify "⚠️ 営業リスト作成: 出力ファイルが見つかりません"
    fi
else
    # 失敗
    log "❌ エラーが発生しました"
    notify "❌ 営業リスト作成失敗: \`$QUERY\`
詳細はログを確認: \`$LOG_FILE\`"
    exit 1
fi
