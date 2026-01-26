#!/bin/bash
# LP幹事から工務店LPのスクリーンショットを取得

OUTPUT_DIR="/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/lp_screenshots"
mkdir -p "$OUTPUT_DIR"

# 関数: LPを取得してスクリーンショット
capture_lp() {
    local index=$1
    local name=$2
    local ref=$3

    echo ""
    echo "=== [$index/20] $name ==="

    # 一覧ページを開く
    agent-browser open "https://lp-kanji.com/search/construction/" > /dev/null 2>&1
    sleep 2

    # スナップショット取得
    agent-browser snapshot -i > /dev/null 2>&1

    # クリック
    agent-browser click @$ref > /dev/null 2>&1
    sleep 2

    # LP URLを取得
    snapshot=$(agent-browser snapshot -i 2>/dev/null)
    lp_url=$(echo "$snapshot" | grep -oE 'link "https?://[^"]+' | head -1 | sed 's/link "//')

    if [ -z "$lp_url" ] || [[ "$lp_url" == *"lp-kanji.com"* ]]; then
        echo "  URL取得失敗、スキップ"
        return 1
    fi

    echo "  URL: $lp_url"

    # LPを開く
    agent-browser open "$lp_url" > /dev/null 2>&1
    sleep 4

    # スクリーンショット
    filename=$(printf "lp_%02d_%s.png" $index "$name")
    agent-browser screenshot --full "$OUTPUT_DIR/$filename" 2>&1

    if [ -f "$OUTPUT_DIR/$filename" ]; then
        size=$(ls -lh "$OUTPUT_DIR/$filename" | awk '{print $5}')
        echo "  保存: $filename ($size)"
        return 0
    else
        echo "  保存失敗"
        return 1
    fi
}

# 20件のLPを処理
capture_lp 1 "yamaso" "e6"
capture_lp 2 "cocochiya" "e7"
capture_lp 3 "california" "e8"
capture_lp 4 "receno" "e9"
capture_lp 5 "jibunhouse" "e10"
capture_lp 6 "cleverlyhome" "e11"
capture_lp 7 "unusual_building" "e12"
capture_lp 8 "sekisuiheim" "e13"
capture_lp 9 "creative_asset" "e14"
capture_lp 10 "refocolle" "e15"
capture_lp 11 "sumitomo" "e16"
capture_lp 12 "lifegram" "e17"
capture_lp 13 "fukei_house" "e18"
capture_lp 14 "gstyle" "e19"
capture_lp 15 "premium" "e20"
capture_lp 16 "rebita" "e21"
capture_lp 17 "sunstar" "e22"
capture_lp 18 "archivision" "e23"
capture_lp 19 "earthcom" "e24"
capture_lp 20 "homepro" "e25"

echo ""
echo "===== 完了 ====="
echo "保存先: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"/*.png 2>/dev/null | wc -l | xargs -I{} echo "スクリーンショット数: {} 件"
