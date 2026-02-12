#!/bin/bash
# 営業パイプライン: リスト作成 → フォーム送信
# 夜中に仕掛けて朝結果を見る用
#
# 使い方:
#   ./run_pipeline.sh "検索クエリ" [リスト件数] [送信上限]
#   nohup ./run_pipeline.sh "東京 SaaS企業" 50 30 &

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
REPO_DIR="$(dirname "$(dirname "$PROJECT_DIR")")"

QUERY="${1:-東京 IT企業}"
MAX_COMPANIES="${2:-50}"
MAX_SENDS="${3:-30}"

# 設定（環境変数で上書き可能）
SLACK_CHANNEL="${SLACK_CHANNEL:-C0ACWUVSRR9}"
OPENAI_KEY_PATH="${OPENAI_KEY_PATH:-$HOME/.config/clawdbot-secrets/openai-api-key}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="$PROJECT_DIR/logs"
OUTPUT_DIR="$PROJECT_DIR/output"
LOG_FILE="$LOG_DIR/pipeline_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"
mkdir -p "$OUTPUT_DIR"

# ログ関数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Slack通知
notify() {
    local msg="$1"
    if command -v clawdbot &> /dev/null; then
        clawdbot message send --channel slack --target "channel:$SLACK_CHANNEL" --message "$msg" 2>/dev/null || true
    fi
}

log "======================================"
log "営業パイプライン 開始"
log "クエリ: $QUERY"
log "リスト目標: $MAX_COMPANIES社"
log "送信上限: $MAX_SENDS件"
log "======================================"

notify "🚀 営業パイプライン開始
• クエリ: \`$QUERY\`
• リスト: ${MAX_COMPANIES}社
• 送信上限: ${MAX_SENDS}件"

cd "$REPO_DIR"

# venv有効化
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 環境変数
if [ -z "$OPENAI_API_KEY" ] && [ -f "$OPENAI_KEY_PATH" ]; then
    export OPENAI_API_KEY=$(cat "$OPENAI_KEY_PATH")
fi

# ========================================
# Phase 1: リスト作成
# ========================================
log ""
log "========== Phase 1: リスト作成 =========="

if python3 "$SCRIPT_DIR/create_sales_list.py" "$QUERY" --max-companies "$MAX_COMPANIES" 2>&1 | tee -a "$LOG_FILE"; then
    RESULT_FILE=$(ls -t "$OUTPUT_DIR"/sales_list_*.json 2>/dev/null | head -1)
    
    if [ -z "$RESULT_FILE" ] || [ ! -f "$RESULT_FILE" ]; then
        log "❌ リストファイルが見つかりません"
        notify "❌ パイプライン失敗: リスト作成でエラー"
        exit 1
    fi
    
    # JSONパースを1回にまとめる
    read COMPANY_COUNT FORM_COUNT <<< $(python3 -c "
import json, sys
try:
    data = json.load(open('$RESULT_FILE'))
    companies = data.get('companies', data) if isinstance(data, dict) else data
    form_count = len([c for c in companies if c.get('contact_form_url')])
    print(len(companies), form_count)
except Exception as e:
    print('? ?', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "? ?")
    
    log "✅ リスト作成完了: ${COMPANY_COUNT}社 (フォーム${FORM_COUNT}件)"
    notify "✅ Phase 1完了: ${COMPANY_COUNT}社収集 (フォーム${FORM_COUNT}件)"
else
    log "❌ リスト作成でエラー"
    notify "❌ パイプライン失敗: リスト作成でエラー"
    exit 1
fi

# ========================================
# Phase 1.5: 重複フィルタリング
# ========================================
log ""
log "========== Phase 1.5: 重複フィルタリング =========="

FILTERED_FILE="$OUTPUT_DIR/filtered_${TIMESTAMP}.json"

# 送信済みドメインをフィルタリング
python3 "$SCRIPT_DIR/filter_unsent.py" "$RESULT_FILE" --url-key "contact_form_url" > "$FILTERED_FILE" 2>> "$LOG_FILE"

# フィルタリング結果を取得
read FILTERED_COUNT FILTERED_FORM_COUNT <<< $(python3 -c "
import json, sys
try:
    data = json.load(open('$FILTERED_FILE'))
    companies = data if isinstance(data, list) else data.get('companies', [])
    form_count = len([c for c in companies if c.get('contact_form_url')])
    print(len(companies), form_count)
except Exception as e:
    print('0 0', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null || echo "0 0")

SKIPPED_COUNT=$((COMPANY_COUNT - FILTERED_COUNT))
log "✅ 重複フィルタ完了: ${FILTERED_COUNT}社残り (${SKIPPED_COUNT}社除外)"

# フィルタ後のファイルを使用
RESULT_FILE="$FILTERED_FILE"
FORM_COUNT="$FILTERED_FORM_COUNT"

# ========================================
# Phase 2: フォーム送信
# ========================================
log ""
log "========== Phase 2: フォーム送信 =========="

if [ "$FORM_COUNT" = "0" ] || [ "$FILTERED_COUNT" = "0" ]; then
    log "⚠️ 送信可能なフォームがありません（全て送信済み）"
    notify "⚠️ パイプライン完了（送信スキップ）: 全て送信済みまたはフォームなし"
    exit 0
fi

log "送信開始: 上限 $MAX_SENDS 件"

if python3 "$SCRIPT_DIR/send_sales_form.py" "$RESULT_FILE" --max-sends "$MAX_SENDS" 2>&1 | tee -a "$LOG_FILE"; then
    # 送信結果を集計（ログディレクトリから最新を取得）
    SENT_LOG="$OUTPUT_DIR/send_log.json"
    
    if [ -n "$SENT_LOG" ] && [ -f "$SENT_LOG" ]; then
        read SENT_COUNT FAILED_COUNT <<< $(python3 -c "
import json, sys
try:
    data = json.load(open('$SENT_LOG'))
    success = len([r for r in data if r.get('status') == 'success'])
    failed = len([r for r in data if r.get('status') != 'success'])
    print(success, failed)
except Exception as e:
    print('? ?', file=sys.stderr)
" 2>/dev/null || echo "? ?")
    else
        SENT_COUNT="?"
        FAILED_COUNT="?"
    fi
    
    log "✅ フォーム送信完了: 成功${SENT_COUNT}件 / 失敗${FAILED_COUNT}件"
else
    log "⚠️ フォーム送信でエラー（一部送信済みの可能性あり）"
    SENT_COUNT="?"
    FAILED_COUNT="?"
fi

# ========================================
# 完了
# ========================================
log ""
log "======================================"
log "✅ パイプライン完了"
log "======================================"

notify "✅ 営業パイプライン完了！
📊 結果:
• リスト: ${COMPANY_COUNT}社
• フォーム検出: ${FORM_COUNT}件
• 送信: ${SENT_COUNT:-?}件成功
📁 出力: \`$(basename "$RESULT_FILE")\`"
