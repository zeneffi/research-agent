#!/usr/bin/env python
"""LP幹事から工務店LPのフルスクリーンショットを取得するスクリプト"""

import subprocess
import re
import time
import os

OUTPUT_DIR = "/Users/wakiyamasora/Documents/product/zeneffi/zeneffi-ai-base/daytona-agent/lp_screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_cmd(cmd):
    """コマンドを実行して出力を返す"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    return result.stdout + result.stderr

def capture_lp(index, lp_id, name):
    """LP詳細ページからLPのURLを取得してスクリーンショットを撮る"""
    print(f"\n[{index}/20] {name} の処理中...")

    # LP幹事の詳細ページを開く
    detail_url = f"https://lp-kanji.com/lp/{lp_id}/"
    run_cmd(f'agent-browser open "{detail_url}"')
    time.sleep(2)

    # スナップショットを取得
    snapshot = run_cmd('agent-browser snapshot -i')

    # 実際のLPのURL (https://で始まるリンク) を探す
    # "link "https://xxxxx" [ref=e9]" のようなパターン
    url_match = re.search(r'link "(https?://[^"]+)" \[ref=e\d+\]', snapshot)

    if url_match:
        lp_url = url_match.group(1)
        # LP幹事自体のURLは除外
        if 'lp-kanji.com' in lp_url:
            # 2番目のURLを探す
            matches = re.findall(r'link "(https?://[^"]+)" \[ref=e\d+\]', snapshot)
            for url in matches:
                if 'lp-kanji.com' not in url and '03-6457-3550' not in url:
                    lp_url = url
                    break

        print(f"  LP URL: {lp_url}")

        # LPサイトを開く
        run_cmd(f'agent-browser open "{lp_url}"')
        time.sleep(3)

        # ネットワーク待機
        run_cmd('agent-browser wait --load networkidle')
        time.sleep(1)

        # フルスクリーンショットを保存
        filename = f"lp_{index:02d}_{name}.png"
        filepath = os.path.join(OUTPUT_DIR, filename)
        result = run_cmd(f'agent-browser screenshot --full "{filepath}"')

        if 'saved' in result.lower() or os.path.exists(filepath):
            print(f"  保存完了: {filename}")
            return True
        else:
            print(f"  保存失敗: {result}")
            return False
    else:
        print("  URL取得失敗")
        return False

# LP幹事のLP詳細ページID一覧（一覧ページから取得したもの）
# 実際のIDは詳細ページのURLから取得する必要があるので、一覧からクリックしてIDを収集

def get_lp_ids():
    """一覧ページから各LPの詳細ページIDを取得"""
    print("LP一覧からIDを収集中...")

    # 一覧ページを開く
    run_cmd('agent-browser open "https://lp-kanji.com/search/construction/"')
    time.sleep(2)

    lp_info = []

    # e6からe25まで（20件）の各リンクをクリックしてIDを取得
    for i, ref_num in enumerate(range(6, 26)):
        ref = f"e{ref_num}"
        print(f"  取得中: {ref}")

        # スクロールしてからクリック
        run_cmd('agent-browser scroll down 100')
        time.sleep(0.3)

        result = run_cmd(f'agent-browser click @{ref}')
        if 'not found' in result.lower():
            print(f"    要素が見つかりません、スキップ")
            continue

        time.sleep(1)

        # URLからIDを取得
        url = run_cmd('agent-browser get url').strip().split('\n')[-1]
        match = re.search(r'/lp/(\d+)/', url)
        if match:
            lp_id = match.group(1)
            print(f"    ID: {lp_id}")
            lp_info.append({'index': i + 1, 'id': lp_id})

        # 一覧ページに戻る
        run_cmd('agent-browser open "https://lp-kanji.com/search/construction/"')
        time.sleep(1)

    return lp_info

if __name__ == '__main__':
    # 既知のLP詳細ページID（手動で確認したもの）
    # 実際にはIDを動的に取得するが、時間短縮のため直接指定も可能

    # まずIDを取得
    lp_list = get_lp_ids()

    print(f"\n取得したLP数: {len(lp_list)}")

    # 各LPのスクリーンショットを取得
    success = 0
    for lp in lp_list:
        name = f"koumuten_{lp['id']}"
        if capture_lp(lp['index'], lp['id'], name):
            success += 1

    print(f"\n完了: {success}/{len(lp_list)} 件のスクリーンショットを保存")
    print(f"保存先: {OUTPUT_DIR}")

    # 保存されたファイル一覧
    files = os.listdir(OUTPUT_DIR)
    for f in sorted(files):
        filepath = os.path.join(OUTPUT_DIR, f)
        size = os.path.getsize(filepath) / 1024
        print(f"  {f} ({size:.1f} KB)")
