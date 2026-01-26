#!/bin/bash
# LP幹事から工務店LPのフルスクリーンショットを取得するスクリプト

OUTPUT_DIR="/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/lp_screenshots"
mkdir -p "$OUTPUT_DIR"

# LP名と実際のURLのリスト
declare -A LP_URLS

# 各LPの詳細ページからURLを取得する関数
get_lp_url() {
    local ref=$1
    local name=$2
    local index=$3

    echo "[$index/20] $name の処理中..."

    # 一覧ページを開く
    agent-browser open "https://lp-kanji.com/search/construction/" > /dev/null 2>&1
    sleep 1

    # LPリンクをクリック
    agent-browser click @$ref > /dev/null 2>&1
    sleep 2

    # 詳細ページのスナップショットを取得してURLを抽出
    snapshot=$(agent-browser snapshot -i 2>/dev/null)

    # https:// で始まるリンクを探す
    url=$(echo "$snapshot" | grep -o 'link "https://[^"]*"' | head -1 | sed 's/link "\(.*\)"/\1/')

    if [ -n "$url" ]; then
        echo "  URL: $url"

        # LPページを開く
        agent-browser open "$url" > /dev/null 2>&1
        sleep 3

        # フルページスクリーンショットを撮影
        filename=$(printf "%02d_%s.png" $index "$(echo "$name" | tr ' ' '_' | tr '/' '_' | cut -c1-30)")
        agent-browser screenshot --full "$OUTPUT_DIR/$filename" > /dev/null 2>&1

        if [ -f "$OUTPUT_DIR/$filename" ]; then
            echo "  スクリーンショット保存: $filename"
        else
            echo "  スクリーンショット保存失敗"
        fi
    else
        echo "  URLが取得できませんでした"
    fi
}

# LPリスト（ref番号と名前）
get_lp_url "e6" "山装" 1
get_lp_url "e7" "cocochiya" 2
get_lp_url "e8" "カリフォルニア工務店" 3
get_lp_url "e9" "ReCENOインテリア" 4
get_lp_url "e10" "ジブンハウス" 5
get_lp_url "e11" "クレバリーホーム" 6
get_lp_url "e12" "世にもおかしな建築物" 7
get_lp_url "e13" "セキスイハイム" 8
get_lp_url "e14" "クリエイティブアセット" 9
get_lp_url "e15" "リフォコレ" 10
get_lp_url "e16" "住友林業" 11
get_lp_url "e17" "ライフグラム" 12
get_lp_url "e18" "風景のある家" 13
get_lp_url "e19" "G-styleCLUB" 14
get_lp_url "e20" "PREMIUM_SERIES" 15
get_lp_url "e21" "住んでからのリビタ" 16
get_lp_url "e22" "SUNSTAR" 17
get_lp_url "e23" "アーキビジョン21" 18
get_lp_url "e24" "アースコム" 19
get_lp_url "e25" "ホームプロ" 20

echo ""
echo "完了！保存先: $OUTPUT_DIR"
ls -la "$OUTPUT_DIR"
