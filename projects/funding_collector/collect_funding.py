#!/usr/bin/env python
"""
資金調達企業収集スクリプト
PR TIMESから資金調達情報を並列収集し、営業リストを生成する
"""

import json
import subprocess
import re
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import os

# 設定
CONFIG = {
    "target_count": 100,  # 目標企業数
    "min_amount": 3,  # 最小調達額（億円）
    "max_amount": 100,  # 最大調達額（億円）
    "months_back": 3,  # 遡る月数
    "rounds": ["シリーズA", "シリーズB", "プレシリーズA", "シリーズC"],
    "output_dir": os.path.dirname(os.path.abspath(__file__)),
}


def get_container_ports():
    """起動中のコンテナのAPIポートを取得"""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "{{.Name}}\t{{.Ports}}"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docker")
    )
    ports = []
    for line in result.stdout.strip().split("\n"):
        if "browser" in line and "3000" in line:
            match = re.search(r"0\.0\.0\.0:(\d+)->3000", line)
            if match:
                ports.append(int(match.group(1)))
    return sorted(ports)


def browser_navigate(port: int, url: str) -> bool:
    """ブラウザをURLにナビゲート"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/navigate",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"url": url})],
            capture_output=True,
            text=True,
            timeout=30
        )
        data = json.loads(result.stdout)
        return data.get("success", False)
    except Exception as e:
        print(f"Navigate error on port {port}: {e}")
        return False


def browser_evaluate(port: int, script: str) -> Optional[str]:
    """ブラウザでJavaScriptを実行"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/evaluate",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"script": script})],
            capture_output=True,
            text=True,
            timeout=60
        )
        data = json.loads(result.stdout)
        if data.get("success"):
            return data.get("result")
        return None
    except Exception as e:
        print(f"Evaluate error on port {port}: {e}")
        return None


def extract_funding_links(port: int, page_num: int) -> list:
    """PR TIMESの検索結果ページから資金調達リンクを抽出"""
    url = f"https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word=%E8%B3%87%E9%87%91%E8%AA%BF%E9%81%94+%E3%82%B7%E3%83%AA%E3%83%BC%E3%82%BA&pagenum={page_num}"

    if not browser_navigate(port, url):
        return []

    time.sleep(3)

    script = """(function() {
        const links = document.querySelectorAll("a");
        const results = [];
        links.forEach(a => {
            const text = a.textContent.trim();
            const href = a.href;
            if(text.length > 20 && href.includes("prtimes.jp/main/html/rd/") &&
               (text.includes("調達") || text.includes("億") || text.includes("シリーズ"))) {
                results.push({text: text.substring(0,200), href});
            }
        });
        return JSON.stringify(results);
    })()"""

    result = browser_evaluate(port, script)
    if result:
        try:
            return json.loads(result)
        except:
            pass
    return []


def extract_company_details(port: int, url: str) -> Optional[dict]:
    """プレスリリースページから企業詳細を抽出"""
    if not browser_navigate(port, url):
        return None

    time.sleep(2)

    script = """(function() {
        const body = document.body.innerText;
        const title = document.title;

        // 会社名抽出
        const companyMatch = body.match(/会社名[：:・]\\s*([^\\n]+)/);
        const company = companyMatch ? companyMatch[1].trim() : "";

        // 代表者抽出
        const ceoMatch = body.match(/代表[者取締役]*[：:・]\\s*([^\\n]+)/);
        const ceo = ceoMatch ? ceoMatch[1].trim() : "";

        // URL抽出
        const urlMatch = body.match(/URL[：:・]\\s*(https?:\\/\\/[^\\s\\n]+)/);
        const corpUrl = urlMatch ? urlMatch[1].trim() : "";

        // 所在地抽出
        const locationMatch = body.match(/(?:本社|所在地)[：:・]\\s*([^\\n]+)/);
        const location = locationMatch ? locationMatch[1].trim() : "";

        // 調達額抽出
        const amountMatch = body.match(/(\\d+(?:\\.\\d+)?)[\\s]*億円/);
        const amount = amountMatch ? parseFloat(amountMatch[1]) : 0;

        // ラウンド抽出
        let round = "";
        if(body.includes("シリーズA")) round = "シリーズA";
        else if(body.includes("シリーズB")) round = "シリーズB";
        else if(body.includes("シリーズC")) round = "シリーズC";
        else if(body.includes("プレシリーズA")) round = "プレシリーズA";
        else if(body.includes("シード")) round = "シード";

        // 事業内容抽出
        const businessMatch = body.match(/事業内容[：:・]\\s*([^\\n]+)/);
        const business = businessMatch ? businessMatch[1].trim() : "";

        // 投資家抽出
        const investorMatch = body.match(/(?:引受先|投資家)[^\\n]*[：:・]\\s*([^\\n]+)/);
        const investors = investorMatch ? investorMatch[1].trim() : "";

        return JSON.stringify({
            title: title,
            company: company,
            ceo: ceo,
            url: corpUrl,
            location: location,
            amount: amount,
            round: round,
            business: business,
            investors: investors,
            source_url: window.location.href,
            body_preview: body.substring(0, 2000)
        });
    })()"""

    result = browser_evaluate(port, script)
    if result:
        try:
            return json.loads(result)
        except:
            pass
    return None


def filter_company(company: dict) -> bool:
    """収集条件に合致するかフィルタリング"""
    amount = company.get("amount", 0)
    round_name = company.get("round", "")

    # 金額フィルタ
    if amount < CONFIG["min_amount"] or amount > CONFIG["max_amount"]:
        return False

    # ラウンドフィルタ
    if round_name and round_name not in CONFIG["rounds"]:
        return False

    return True


def collect_funding_data(ports: list) -> list:
    """並列でデータ収集"""
    all_links = []
    companies = []
    seen_urls = set()

    print(f"[1/3] PR TIMESから資金調達リンクを収集中...")

    # ステップ1: 複数ページからリンク収集
    with ThreadPoolExecutor(max_workers=len(ports)) as executor:
        futures = {}
        for i, port in enumerate(ports):
            page_num = i + 1
            futures[executor.submit(extract_funding_links, port, page_num)] = page_num

        for future in as_completed(futures):
            page_num = futures[future]
            try:
                links = future.result()
                print(f"  - ページ {page_num}: {len(links)}件のリンク")
                all_links.extend(links)
            except Exception as e:
                print(f"  - ページ {page_num}: エラー {e}")

    # 重複除去
    unique_links = []
    for link in all_links:
        if link["href"] not in seen_urls:
            seen_urls.add(link["href"])
            unique_links.append(link)

    print(f"\n[2/3] {len(unique_links)}件のユニークリンクから詳細収集中...")

    # ステップ2: 詳細ページから情報収集
    collected = 0
    batch_size = len(ports)

    for batch_start in range(0, len(unique_links), batch_size):
        if len(companies) >= CONFIG["target_count"]:
            break

        batch = unique_links[batch_start:batch_start + batch_size]

        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = {}
            for i, link in enumerate(batch):
                port = ports[i % len(ports)]
                futures[executor.submit(extract_company_details, port, link["href"])] = link

            for future in as_completed(futures):
                link = futures[future]
                try:
                    company = future.result()
                    if company and filter_company(company):
                        companies.append(company)
                        collected += 1
                        print(f"  [{collected}] {company.get('company', 'Unknown')} - {company.get('amount', 0)}億円 ({company.get('round', '')})")
                except Exception as e:
                    print(f"  エラー: {e}")

        # 次のバッチ前に少し待つ
        time.sleep(1)

    return companies


def generate_markdown_report(companies: list, output_path: str):
    """マークダウンレポート生成"""
    today = datetime.now().strftime("%Y年%m月%d日")

    # 業種分類
    categories = {
        "AI/SaaS": [],
        "医療/ヘルスケア": [],
        "フィンテック": [],
        "リテール/EC": [],
        "エネルギー/環境": [],
        "その他": []
    }

    for c in companies:
        business = (c.get("business", "") + c.get("title", "")).lower()
        if any(w in business for w in ["ai", "saas", "エージェント", "自動化"]):
            categories["AI/SaaS"].append(c)
        elif any(w in business for w in ["医療", "患者", "ヘルス", "メディカル"]):
            categories["医療/ヘルスケア"].append(c)
        elif any(w in business for w in ["金融", "決済", "投資", "銀行"]):
            categories["フィンテック"].append(c)
        elif any(w in business for w in ["小売", "ec", "コマース", "リテール"]):
            categories["リテール/EC"].append(c)
        elif any(w in business for w in ["エネルギー", "電力", "環境", "カーボン"]):
            categories["エネルギー/環境"].append(c)
        else:
            categories["その他"].append(c)

    md = f"""# 受託開発営業リスト（資金調達直後企業）

**作成日**: {today}
**収集企業数**: {len(companies)}社
**対象期間**: 直近{CONFIG['months_back']}ヶ月
**条件**: {', '.join(CONFIG['rounds'])} / 調達額{CONFIG['min_amount']}〜{CONFIG['max_amount']}億円

---

## サマリー

| 指標 | 値 |
|-----|-----|
| 総企業数 | {len(companies)}社 |
| 総調達額 | 約{sum(c.get('amount', 0) for c in companies):.1f}億円 |
| 平均調達額 | {sum(c.get('amount', 0) for c in companies) / len(companies) if companies else 0:.1f}億円 |

### 業種別内訳
| 業種 | 企業数 |
|-----|-------|
"""
    for cat, items in categories.items():
        if items:
            md += f"| {cat} | {len(items)}社 |\n"

    md += "\n---\n\n"

    # 各企業の詳細
    for cat, items in categories.items():
        if not items:
            continue

        md += f"## {cat}\n\n"

        for i, c in enumerate(items, 1):
            company_name = c.get("company", "") or c.get("title", "").split("、")[0].split("｜")[0]
            md += f"""### {i}. {company_name}
| 項目 | 内容 |
|-----|------|
| **調達額** | {c.get('amount', 0)}億円（{c.get('round', '不明')}） |
| **事業内容** | {c.get('business', '不明')} |
| **本社** | {c.get('location', '不明')} |
| **代表** | {c.get('ceo', '不明')} |
| **URL** | {c.get('url', '不明')} |
| **投資家** | {c.get('investors', '不明')[:100]}... |
| **情報源** | [{c.get('source_url', '')}]({c.get('source_url', '')}) |

"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    return md


def generate_json_output(companies: list, output_path: str):
    """JSON出力"""
    output = {
        "metadata": {
            "created_at": datetime.now().isoformat(),
            "total_count": len(companies),
            "config": CONFIG
        },
        "companies": companies
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("資金調達企業収集スクリプト")
    print("=" * 60)
    print(f"目標: {CONFIG['target_count']}社")
    print(f"条件: {', '.join(CONFIG['rounds'])} / {CONFIG['min_amount']}〜{CONFIG['max_amount']}億円")
    print()

    # コンテナポート取得
    ports = get_container_ports()
    if not ports:
        print("エラー: Dockerコンテナが起動していません")
        print("以下のコマンドで起動してください:")
        print("  cd docker  # (リポジトリルートから)")
        print("  docker compose up -d --scale browser=10")
        return

    print(f"利用可能なブラウザコンテナ: {len(ports)}個")
    print()

    # データ収集
    companies = collect_funding_data(ports)

    print(f"\n[3/3] レポート生成中...")

    # 出力
    timestamp = datetime.now().strftime("%Y%m%d")
    md_path = os.path.join(CONFIG["output_dir"], f"funding_list_{timestamp}.md")
    json_path = os.path.join(CONFIG["output_dir"], f"funding_list_{timestamp}.json")

    generate_markdown_report(companies, md_path)
    generate_json_output(companies, json_path)

    print(f"\n完了!")
    print(f"  - マークダウン: {md_path}")
    print(f"  - JSON: {json_path}")
    print(f"  - 収集企業数: {len(companies)}社")


if __name__ == "__main__":
    main()
