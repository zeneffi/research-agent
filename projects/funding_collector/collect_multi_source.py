#!/usr/bin/env python
"""
マルチソース資金調達企業収集スクリプト
PR TIMES + BRIDGE + その他ソースから収集
"""

import json
import subprocess
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict
import os
from urllib.parse import quote

CONFIG = {
    "target_count": 100,
    "min_amount": 1,
    "max_amount": 200,
    "output_dir": os.path.dirname(os.path.abspath(__file__)),
}

# 検索設定
PRTIMES_KEYWORDS = [
    "資金調達",
    "シリーズA 調達",
    "シリーズB 調達",
    "第三者割当増資",
    "スタートアップ 億円",
    "ベンチャー 資金調達",
    "シリーズC",
    "プレシリーズA",
]

BRIDGE_URLS = [
    "https://thebridge.jp/category/startup",
    "https://thebridge.jp/tag/funding",
]

ASCII_URLS = [
    "https://ascii.jp/elem/000/004/230/",  # スタートアップ記事
]


def get_container_ports():
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "{{.Name}}\t{{.Ports}}"],
        capture_output=True, text=True,
        cwd=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docker")
    )
    ports = []
    for line in result.stdout.strip().split("\n"):
        if "browser" in line:
            match = re.search(r"0\.0\.0\.0:(\d+)->3000", line)
            if match:
                ports.append(int(match.group(1)))
    return sorted(ports)


def browser_navigate(port: int, url: str) -> bool:
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/navigate",
             "-H", "Content-Type: application/json", "-d", json.dumps({"url": url})],
            capture_output=True, text=True, timeout=30
        )
        return json.loads(result.stdout).get("success", False)
    except:
        return False


def browser_evaluate(port: int, script: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/evaluate",
             "-H", "Content-Type: application/json", "-d", json.dumps({"script": script})],
            capture_output=True, text=True, timeout=60
        )
        data = json.loads(result.stdout)
        return data.get("result") if data.get("success") else None
    except:
        return None


def search_prtimes(port: int, keyword: str, page: int) -> List[Dict]:
    """PR TIMESで検索"""
    url = f"https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word={quote(keyword)}&pagenum={page}"
    if not browser_navigate(port, url):
        return []
    time.sleep(2)

    script = """(function() {
        const links = document.querySelectorAll("a");
        const results = [];
        const seen = new Set();
        links.forEach(a => {
            const text = a.textContent.trim();
            const href = a.href;
            if(href.includes("prtimes.jp/main/html/rd/") && !seen.has(href) && text.length > 20) {
                const hasAmount = /\\d+(?:\\.\\d+)?億円/.test(text);
                const hasFunding = text.includes("調達") || text.includes("増資");
                if(hasAmount || hasFunding) {
                    seen.add(href);
                    results.push({text: text.substring(0,200), href, source: "prtimes"});
                }
            }
        });
        return JSON.stringify(results);
    })()"""

    result = browser_evaluate(port, script)
    return json.loads(result) if result else []


def search_duckduckgo(port: int, query: str) -> List[Dict]:
    """DuckDuckGoで検索"""
    url = f"https://duckduckgo.com/?q={quote(query)}"
    if not browser_navigate(port, url):
        return []
    time.sleep(3)

    script = """(function() {
        const links = document.querySelectorAll("a");
        const results = [];
        const seen = new Set();
        links.forEach(a => {
            const text = a.textContent.trim();
            const href = a.href;
            if(!seen.has(href) && text.length > 20 &&
               (href.includes("prtimes.jp") || href.includes("thebridge.jp") || href.includes("ascii.jp")) &&
               (text.includes("調達") || text.includes("億円") || text.includes("シリーズ"))) {
                seen.add(href);
                results.push({text: text.substring(0,200), href, source: "duckduckgo"});
            }
        });
        return JSON.stringify(results);
    })()"""

    result = browser_evaluate(port, script)
    return json.loads(result) if result else []


def extract_company_details(port: int, url: str) -> Optional[Dict]:
    """企業詳細を抽出"""
    if not browser_navigate(port, url):
        return None
    time.sleep(2)

    script = """(function() {
        const body = document.body.innerText;
        const title = document.title;

        // 会社名
        let company = "";
        const m1 = title.match(/(.+?)(?:、|｜|\\||のプレス|\\s-\\s)/);
        if(m1) company = m1[1].trim();
        if(!company) {
            const m1b = body.match(/会社名[：:・\\s]*([^\\n]+)/);
            if(m1b) company = m1b[1].trim();
        }

        // 調達額
        let amount = 0;
        const amountPatterns = [
            /総額(\\d+(?:\\.\\d+)?)[\\s]*億円/,
            /(\\d+(?:\\.\\d+)?)[\\s]*億円[のを]*(?:資金)?調達/,
            /調達[額金]?[はが]?(\\d+(?:\\.\\d+)?)[\\s]*億円/,
            /(\\d+(?:\\.\\d+)?)[\\s]*億円.*(?:調達|増資)/
        ];
        for(const p of amountPatterns) {
            const m = body.match(p);
            if(m) { amount = parseFloat(m[1]); break; }
        }
        // 最後のフォールバック
        if(amount === 0) {
            const m = body.match(/(\\d+(?:\\.\\d+)?)[\\s]*億円/);
            if(m) amount = parseFloat(m[1]);
        }

        // ラウンド
        let round = "";
        const roundPatterns = [
            [/プレシリーズ[\\s]*A/i, "プレシリーズA"],
            [/シリーズ[\\s]*A/i, "シリーズA"],
            [/シリーズ[\\s]*B/i, "シリーズB"],
            [/シリーズ[\\s]*C/i, "シリーズC"],
            [/シリーズ[\\s]*D/i, "シリーズD"],
            [/シリーズ[\\s]*E/i, "シリーズE"],
            [/シード/i, "シード"],
        ];
        for(const [p, r] of roundPatterns) {
            if(p.test(body)) { round = r; break; }
        }

        // 事業内容
        let business = "";
        const m3 = body.match(/事業内容[：:・\\s]*([^\\n]+)/);
        if(m3) business = m3[1].trim().substring(0,150);

        // 所在地
        let location = "";
        const m4 = body.match(/(?:本社|所在地)[：:・\\s]*([^\\n]+)/);
        if(m4) location = m4[1].trim().substring(0,80);

        // 代表
        let ceo = "";
        const m5 = body.match(/代表[者取締役社長CEO]*[：:・\\s]*([^\\n、,（\\(]+)/);
        if(m5) ceo = m5[1].trim().substring(0,30);

        // URL
        let corpUrl = "";
        const m6 = body.match(/(?:URL|企業URL|コーポレートサイト)[：:・\\s]*(https?:\\/\\/[^\\s\\n]+)/);
        if(m6) corpUrl = m6[1].trim();

        // 投資家
        let investors = "";
        const m7 = body.match(/(?:引受先|投資家|出資者)[一覧]*[^\\n]*[：:・]\\s*([^\\n]+)/);
        if(m7) investors = m7[1].trim().substring(0,200);

        // 日付
        let date = "";
        const m8 = body.match(/(202[456])年(\\d{1,2})月(\\d{1,2})日/);
        if(m8) date = m8[0];

        return JSON.stringify({
            company, amount, round, business, location, ceo,
            url: corpUrl, investors, date, source_url: window.location.href
        });
    })()"""

    result = browser_evaluate(port, script)
    if result:
        try:
            data = json.loads(result)
            # ノイズフィルタ
            if data.get("amount", 0) > 200:  # 200億円以上は怪しい
                return None
            if data.get("amount", 0) < 1:  # 1億円未満は対象外
                return None
            return data
        except:
            pass
    return None


def collect_links(ports: List[int]) -> List[Dict]:
    """全ソースからリンクを収集"""
    all_links = []
    seen_urls = set()

    # PR TIMES検索タスク
    tasks = []
    for keyword in PRTIMES_KEYWORDS:
        for page in range(1, 16):  # 1-15ページ
            tasks.append(("prtimes", keyword, page))

    # DuckDuckGo検索タスク
    ddg_queries = [
        "site:prtimes.jp 資金調達 2026年",
        "site:prtimes.jp シリーズA 億円 2026",
        "site:prtimes.jp シリーズB 億円 2025",
        "site:prtimes.jp スタートアップ 調達 2026",
        "資金調達 スタートアップ 2026年 億円",
    ]
    for query in ddg_queries:
        tasks.append(("ddg", query, 0))

    print(f"  総タスク数: {len(tasks)}")

    batch_size = len(ports)
    for batch_start in range(0, len(tasks), batch_size):
        batch = tasks[batch_start:batch_start + batch_size]

        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = {}
            for i, task in enumerate(batch):
                port = ports[i % len(ports)]
                if task[0] == "prtimes":
                    futures[executor.submit(search_prtimes, port, task[1], task[2])] = task
                elif task[0] == "ddg":
                    futures[executor.submit(search_duckduckgo, port, task[1])] = task

            for future in as_completed(futures):
                try:
                    links = future.result()
                    for link in links:
                        if link["href"] not in seen_urls:
                            seen_urls.add(link["href"])
                            all_links.append(link)
                except:
                    pass

        processed = min(batch_start + batch_size, len(tasks))
        if processed % 20 == 0:
            print(f"  進捗: {processed}/{len(tasks)}, リンク: {len(all_links)}件")

    return all_links


def collect_details(ports: List[int], links: List[Dict], target: int) -> List[Dict]:
    """企業詳細を収集"""
    companies = []
    seen_companies = set()

    batch_size = len(ports)
    for batch_start in range(0, len(links), batch_size):
        if len(companies) >= target:
            break

        batch = links[batch_start:batch_start + batch_size]

        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = {}
            for i, link in enumerate(batch):
                port = ports[i % len(ports)]
                futures[executor.submit(extract_company_details, port, link["href"])] = link

            for future in as_completed(futures):
                try:
                    company = future.result()
                    if company:
                        key = company.get("company", "") or company.get("source_url", "")
                        if key and key not in seen_companies:
                            seen_companies.add(key)
                            companies.append(company)
                            print(f"  [{len(companies)}] {company.get('company', 'Unknown')[:35]} - {company.get('amount')}億円 ({company.get('round', '不明')})")
                except:
                    pass

        time.sleep(0.3)

    return companies


def categorize(company: Dict) -> str:
    text = (company.get("business", "") + " " + company.get("company", "")).lower()
    categories = {
        "AI/SaaS": ["ai", "saas", "エージェント", "自動化", "dx", "クラウド"],
        "医療/ヘルスケア": ["医療", "患者", "ヘルス", "メディカル", "病院", "創薬"],
        "フィンテック": ["金融", "決済", "投資", "銀行", "保険"],
        "リテール/EC": ["小売", "ec", "コマース", "リテール", "店舗"],
        "エネルギー": ["エネルギー", "電力", "環境", "カーボン"],
        "不動産": ["不動産", "建設", "住宅", "空き家"],
        "HR/人材": ["人材", "採用", "hr", "労務"],
        "宇宙/ディープテック": ["宇宙", "衛星", "量子", "バイオ", "ゲノム"],
        "フード/農業": ["食品", "飲食", "農業", "フード"],
    }
    for cat, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return cat
    return "その他"


def generate_report(companies: List[Dict], output_path: str):
    """レポート生成"""
    today = datetime.now().strftime("%Y年%m月%d日")

    # カテゴリ分類
    categorized = {}
    for c in companies:
        cat = categorize(c)
        c["category"] = cat
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(c)

    for cat in categorized:
        categorized[cat].sort(key=lambda x: x.get("amount", 0), reverse=True)

    total = sum(c.get("amount", 0) for c in companies)
    avg = total / len(companies) if companies else 0

    # ラウンド集計
    rounds = {}
    for c in companies:
        r = c.get("round", "不明")
        rounds[r] = rounds.get(r, 0) + 1

    md = f"""# 受託開発営業リスト（資金調達直後企業）

**作成日**: {today}
**収集企業数**: {len(companies)}社
**データソース**: PR TIMES, DuckDuckGo

---

## サマリー

| 指標 | 値 |
|-----|-----|
| 総企業数 | {len(companies)}社 |
| 総調達額 | 約{total:.1f}億円 |
| 平均調達額 | {avg:.1f}億円 |

### ラウンド別
| ラウンド | 企業数 |
|---------|-------|
"""
    for r, cnt in sorted(rounds.items(), key=lambda x: x[1], reverse=True):
        md += f"| {r} | {cnt}社 |\n"

    md += """
### 業種別
| 業種 | 企業数 |
|-----|-------|
"""
    for cat, items in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        md += f"| {cat} | {len(items)}社 |\n"

    # 優先度高リスト
    priority = [c for c in companies if c.get("round") in ["シリーズA", "シリーズB", "プレシリーズA"] and 3 <= c.get("amount", 0) <= 20]
    priority.sort(key=lambda x: x.get("amount", 0), reverse=True)

    if priority:
        md += f"\n---\n\n## 営業優先度: 高（{len(priority)}社）\n\n"
        md += "| # | 企業名 | 調達額 | ラウンド | 業種 | 事業内容 |\n"
        md += "|---|--------|--------|----------|------|----------|\n"
        for i, c in enumerate(priority, 1):
            md += f"| {i} | {c.get('company', '')[:20]} | {c.get('amount')}億円 | {c.get('round')} | {c.get('category')} | {c.get('business', '')[:30]} |\n"

    # 全リスト
    md += "\n---\n\n## 全企業リスト\n\n"
    for cat, items in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        md += f"\n### {cat}（{len(items)}社）\n\n"
        md += "| # | 企業名 | 調達額 | ラウンド | 代表 | URL |\n"
        md += "|---|--------|--------|----------|------|-----|\n"
        for i, c in enumerate(items, 1):
            md += f"| {i} | {c.get('company', '')[:25]} | {c.get('amount')}億円 | {c.get('round', '不明')} | {c.get('ceo', '')[:15]} | {c.get('url', '')[:30]} |\n"

    with open(output_path, "w") as f:
        f.write(md)


def main():
    print("=" * 60)
    print("マルチソース資金調達企業収集")
    print("=" * 60)

    ports = get_container_ports()
    if not ports:
        print("エラー: コンテナなし")
        return
    print(f"コンテナ: {len(ports)}個\n")

    print("[1/3] リンク収集...")
    links = collect_links(ports)
    print(f"  合計: {len(links)}件\n")

    print(f"[2/3] 詳細収集（目標: {CONFIG['target_count']}社）...")
    companies = collect_details(ports, links, CONFIG["target_count"])
    print(f"  合計: {len(companies)}社\n")

    print("[3/3] レポート生成...")
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    md_path = os.path.join(CONFIG["output_dir"], f"funding_list_{ts}.md")
    json_path = os.path.join(CONFIG["output_dir"], f"funding_list_{ts}.json")

    generate_report(companies, md_path)
    with open(json_path, "w") as f:
        json.dump({"metadata": {"created_at": ts, "count": len(companies)}, "companies": companies}, f, ensure_ascii=False, indent=2)

    print(f"\n完了! {len(companies)}社")
    print(f"  - MD: {md_path}")
    print(f"  - JSON: {json_path}")


if __name__ == "__main__":
    main()
