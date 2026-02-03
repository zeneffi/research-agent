#!/usr/bin/env python
"""LP幹事から工務店LPのURLを取得するスクリプト"""

import subprocess
import re
import json
import time
import os


def run_browser_command(cmd):
    """agent-browserコマンドを実行"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr


def get_lp_urls():
    """LP一覧から各LPの実際のURLを取得"""
    lp_data = []

    # 一覧ページを開く
    run_browser_command(
        'agent-browser open "https://lp-kanji.com/search/construction/"'
    )
    time.sleep(2)

    # スナップショットを取得してリンクを解析
    snapshot = run_browser_command("agent-browser snapshot")
    print("一覧ページのスナップショット取得完了")

    # LP詳細ページのリンクパターン（e6からe26がLPリンク）
    lp_refs = [
        "e6",
        "e7",
        "e8",
        "e9",
        "e10",
        "e11",
        "e12",
        "e13",
        "e14",
        "e15",
        "e16",
        "e17",
        "e18",
        "e19",
        "e20",
        "e21",
        "e22",
        "e23",
        "e24",
        "e25",
    ]

    for i, ref in enumerate(lp_refs):
        print(f"\n--- LP {i+1}/20: {ref} ---")

        # 一覧ページを開く
        run_browser_command(
            'agent-browser open "https://lp-kanji.com/search/construction/"'
        )
        time.sleep(1)

        # LPリンクをクリック
        run_browser_command(f"agent-browser click @{ref}")
        time.sleep(2)

        # 詳細ページのスナップショットを取得
        detail_snapshot = run_browser_command("agent-browser snapshot -i")

        # 実際のLP URLを探す（e9が通常LP URLリンク）
        # "https://" で始まるリンクを探す
        url_match = re.search(r'link "https?://[^"]+?" \[ref=(e\d+)\]', detail_snapshot)
        if url_match:
            url_ref = url_match.group(1)
            # URLを取得
            lines = detail_snapshot.split("\n")
            for line in lines:
                if f"[ref={url_ref}]" in line and 'link "http' in line:
                    url = re.search(r'link "(https?://[^"]+)"', line)
                    if url:
                        lp_url = url.group(1)
                        print(f"  URL: {lp_url}")
                        lp_data.append({"index": i + 1, "url": lp_url})
                        break

        time.sleep(0.5)

    return lp_data


if __name__ == "__main__":
    lp_urls = get_lp_urls()

    # 結果をJSONファイルに保存
    with open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output", "lp_urls.json"),
        "w",
    ) as f:
        json.dump(lp_urls, f, ensure_ascii=False, indent=2)

    print(f"\n合計 {len(lp_urls)} 件のLPを取得")
    for lp in lp_urls:
        print(f"  {lp['index']}: {lp['url']}")
