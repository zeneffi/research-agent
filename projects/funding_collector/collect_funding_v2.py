#!/usr/bin/env python
"""
資金調達企業収集スクリプト v2
複数ソース・複数キーワードで100社以上を収集
"""

import json
import subprocess
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import os

# 設定
CONFIG = {
    "target_count": 100,
    "min_amount": 1,  # 最小調達額（億円）- 幅広く収集
    "max_amount": 500,
    "months_back": 6,  # 6ヶ月に拡大
    "output_dir": os.path.dirname(os.path.abspath(__file__)),
}

# 検索キーワード（複数パターン）
SEARCH_KEYWORDS = [
    "資金調達 シリーズA",
    "資金調達 シリーズB",
    "資金調達 スタートアップ",
    "シリーズA 億円",
    "シリーズB 億円",
    "資金調達 完了",
    "第三者割当増資",
    "資金調達 実施",
    "プレシリーズA",
    "シリーズC 調達",
]


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


def browser_navigate(port: int, url: str, timeout: int = 30) -> bool:
    """ブラウザをURLにナビゲート"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/navigate",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"url": url})],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        data = json.loads(result.stdout)
        return data.get("success", False)
    except Exception as e:
        return False


def browser_evaluate(port: int, script: str, timeout: int = 60) -> Optional[str]:
    """ブラウザでJavaScriptを実行"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/evaluate",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"script": script})],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        data = json.loads(result.stdout)
        if data.get("success"):
            return data.get("result")
        return None
    except Exception as e:
        return None


def search_prtimes(port: int, keyword: str, page: int) -> list:
    """PR TIMESで検索してリンク取得"""
    from urllib.parse import quote
    encoded_keyword = quote(keyword)
    url = f"https://prtimes.jp/main/action.php?run=html&page=searchkey&search_word={encoded_keyword}&pagenum={page}"

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
            if(text.length > 15 && href.includes("prtimes.jp/main/html/rd/") && !seen.has(href) &&
               (text.includes("調達") || text.includes("億") || text.includes("シリーズ") || text.includes("増資"))) {
                seen.add(href);
                results.push({text: text.substring(0,200), href: href});
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

        // タイトルから会社名抽出
        let company = "";
        const titleMatch = title.match(/(.+?)(?:、|｜|\\||のプレスリリース)/);
        if(titleMatch) company = titleMatch[1].trim();

        // 本文から会社名抽出（フォールバック）
        if(!company) {
            const companyMatch = body.match(/会社名[：:・\\s]*([^\\n]+)/);
            if(companyMatch) company = companyMatch[1].trim();
        }

        // 代表者抽出
        let ceo = "";
        const ceoPatterns = [
            /代表取締役[社長CEO]*[：:・\\s]*([^\\n、,]+)/,
            /代表者[：:・\\s]*([^\\n、,]+)/,
            /CEO[：:・\\s]*([^\\n、,]+)/
        ];
        for(const pattern of ceoPatterns) {
            const match = body.match(pattern);
            if(match) { ceo = match[1].trim(); break; }
        }

        // URL抽出
        let corpUrl = "";
        const urlPatterns = [
            /URL[：:・\\s]*(https?:\\/\\/[^\\s\\n]+)/,
            /企業URL[：:・\\s]*(https?:\\/\\/[^\\s\\n]+)/,
            /コーポレートサイト[：:・\\s]*(https?:\\/\\/[^\\s\\n]+)/
        ];
        for(const pattern of urlPatterns) {
            const match = body.match(pattern);
            if(match) { corpUrl = match[1].trim(); break; }
        }

        // 所在地抽出
        let location = "";
        const locPatterns = [
            /本社[所在地]*[：:・\\s]*([^\\n]+)/,
            /所在地[：:・\\s]*([^\\n]+)/
        ];
        for(const pattern of locPatterns) {
            const match = body.match(pattern);
            if(match) { location = match[1].trim().substring(0, 100); break; }
        }

        // 調達額抽出（複数パターン対応）
        let amount = 0;
        const amountPatterns = [
            /総額(\\d+(?:\\.\\d+)?)[\\s]*億円/,
            /(\\d+(?:\\.\\d+)?)[\\s]*億円[のを]*(?:資金)?調達/,
            /調達[額金]*[はが]?(\\d+(?:\\.\\d+)?)[\\s]*億円/,
            /(\\d+(?:\\.\\d+)?)[\\s]*億円/
        ];
        for(const pattern of amountPatterns) {
            const match = body.match(pattern);
            if(match) { amount = parseFloat(match[1]); break; }
        }

        // ラウンド抽出
        let round = "";
        if(body.includes("プレシリーズA") || body.includes("Pre-Series A")) round = "プレシリーズA";
        else if(body.includes("シリーズA") || body.includes("Series A")) round = "シリーズA";
        else if(body.includes("シリーズB") || body.includes("Series B")) round = "シリーズB";
        else if(body.includes("シリーズC") || body.includes("Series C")) round = "シリーズC";
        else if(body.includes("シリーズD") || body.includes("Series D")) round = "シリーズD";
        else if(body.includes("シリーズE") || body.includes("Series E")) round = "シリーズE";
        else if(body.includes("シード") || body.includes("Seed")) round = "シード";

        // 事業内容抽出
        let business = "";
        const bizPatterns = [
            /事業内容[：:・\\s]*([^\\n]+)/,
            /サービス内容[：:・\\s]*([^\\n]+)/
        ];
        for(const pattern of bizPatterns) {
            const match = body.match(pattern);
            if(match) { business = match[1].trim().substring(0, 200); break; }
        }

        // 投資家抽出
        let investors = "";
        const invPatterns = [
            /(?:引受先|投資家|出資者)[一覧]*[^\\n]*[：:・]\\s*([^\\n]+)/,
            /リード投資家[：:・\\s]*([^\\n]+)/
        ];
        for(const pattern of invPatterns) {
            const match = body.match(pattern);
            if(match) { investors = match[1].trim().substring(0, 300); break; }
        }

        // 日付抽出
        let date = "";
        const dateMatch = body.match(/(2025|2026)年(\\d{1,2})月(\\d{1,2})日/);
        if(dateMatch) date = dateMatch[0];

        // 設立年抽出
        let founded = "";
        const foundedMatch = body.match(/設立[：:・\\s]*(\\d{4})年/);
        if(foundedMatch) founded = foundedMatch[1];

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
            date: date,
            founded: founded,
            source_url: window.location.href
        });
    })()"""

    result = browser_evaluate(port, script)
    if result:
        try:
            return json.loads(result)
        except:
            pass
    return None


def collect_all_links(ports: list) -> list:
    """複数キーワード・複数ページからリンクを収集"""
    all_links = []
    seen_urls = set()

    tasks = []
    for keyword in SEARCH_KEYWORDS:
        for page in range(1, 11):  # 各キーワード10ページ
            tasks.append((keyword, page))

    print(f"  検索タスク数: {len(tasks)}")

    batch_size = len(ports)
    for batch_start in range(0, len(tasks), batch_size):
        batch = tasks[batch_start:batch_start + batch_size]

        with ThreadPoolExecutor(max_workers=len(ports)) as executor:
            futures = {}
            for i, (keyword, page) in enumerate(batch):
                port = ports[i % len(ports)]
                futures[executor.submit(search_prtimes, port, keyword, page)] = (keyword, page)

            for future in as_completed(futures):
                keyword, page = futures[future]
                try:
                    links = future.result()
                    for link in links:
                        if link["href"] not in seen_urls:
                            seen_urls.add(link["href"])
                            all_links.append(link)
                except:
                    pass

        # 進捗表示
        processed = min(batch_start + batch_size, len(tasks))
        print(f"  進捗: {processed}/{len(tasks)} タスク完了, {len(all_links)}件のユニークリンク")

    return all_links


def collect_company_details(ports: list, links: list, target: int) -> list:
    """企業詳細を並列収集"""
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
                link = futures[future]
                try:
                    company = future.result()
                    if company and company.get("amount", 0) >= CONFIG["min_amount"]:
                        # 重複チェック（会社名ベース）
                        company_key = company.get("company", "") or company.get("source_url", "")
                        if company_key and company_key not in seen_companies:
                            seen_companies.add(company_key)
                            companies.append(company)
                            print(f"  [{len(companies)}] {company.get('company', 'Unknown')[:30]} - {company.get('amount', 0)}億円 ({company.get('round', '不明')})")
                except:
                    pass

        time.sleep(0.5)

    return companies


def categorize_company(company: dict) -> str:
    """企業を業種カテゴリに分類"""
    text = (company.get("business", "") + " " + company.get("title", "")).lower()

    categories = {
        "AI/SaaS/DX": ["ai", "saas", "エージェント", "自動化", "dx", "クラウド", "プラットフォーム"],
        "医療/ヘルスケア": ["医療", "患者", "ヘルス", "メディカル", "病院", "診療", "治療", "創薬"],
        "フィンテック": ["金融", "決済", "投資", "銀行", "保険", "fintech", "暗号", "ブロックチェーン"],
        "リテール/EC": ["小売", "ec", "コマース", "リテール", "店舗", "在庫", "物流"],
        "エネルギー/環境": ["エネルギー", "電力", "環境", "カーボン", "脱炭素", "再生可能"],
        "不動産/建設": ["不動産", "建設", "住宅", "空き家", "建築"],
        "HRテック/人材": ["人材", "採用", "hr", "労務", "給与"],
        "教育/Edテック": ["教育", "学習", "edtech", "スクール"],
        "宇宙/ディープテック": ["宇宙", "衛星", "ロケット", "量子", "バイオ", "ゲノム"],
        "フード/農業": ["食品", "飲食", "農業", "フード", "レストラン"],
    }

    for category, keywords in categories.items():
        if any(kw in text for kw in keywords):
            return category

    return "その他"


def generate_markdown_report(companies: list, output_path: str):
    """マークダウンレポート生成"""
    today = datetime.now().strftime("%Y年%m月%d日")

    # カテゴリ分類
    categorized = {}
    for c in companies:
        cat = categorize_company(c)
        if cat not in categorized:
            categorized[cat] = []
        categorized[cat].append(c)

    # 調達額でソート
    for cat in categorized:
        categorized[cat].sort(key=lambda x: x.get("amount", 0), reverse=True)

    total_amount = sum(c.get("amount", 0) for c in companies)
    avg_amount = total_amount / len(companies) if companies else 0

    # ラウンド別集計
    round_counts = {}
    for c in companies:
        r = c.get("round", "不明")
        round_counts[r] = round_counts.get(r, 0) + 1

    md = f"""# 受託開発営業リスト（資金調達直後企業）

**作成日**: {today}
**収集企業数**: {len(companies)}社
**対象期間**: 直近{CONFIG['months_back']}ヶ月
**データソース**: PR TIMES

---

## エグゼクティブサマリー

| 指標 | 値 |
|-----|-----|
| 総企業数 | {len(companies)}社 |
| 総調達額 | 約{total_amount:.1f}億円 |
| 平均調達額 | {avg_amount:.1f}億円 |

### ラウンド別内訳
| ラウンド | 企業数 |
|---------|-------|
"""
    for r, count in sorted(round_counts.items(), key=lambda x: x[1], reverse=True):
        md += f"| {r} | {count}社 |\n"

    md += """
### 業種別内訳
| 業種 | 企業数 | 主要プレイヤー |
|-----|-------|--------------|
"""
    for cat, items in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        top_companies = ", ".join([c.get("company", "")[:15] for c in items[:3] if c.get("company")])
        md += f"| {cat} | {len(items)}社 | {top_companies} |\n"

    md += "\n---\n\n"

    # 優先度高（シリーズA/B、3-15億円）
    priority_high = [c for c in companies if c.get("round") in ["シリーズA", "シリーズB", "プレシリーズA"] and 3 <= c.get("amount", 0) <= 15]
    priority_high.sort(key=lambda x: x.get("amount", 0), reverse=True)

    if priority_high:
        md += f"""## 営業優先度: 高（シリーズA/B、3-15億円）

受託開発ニーズが最も高いセグメント。プロダクト拡張フェーズでエンジニアリソースが不足しやすい。

"""
        for i, c in enumerate(priority_high[:30], 1):
            md += f"""### {i}. {c.get('company', 'Unknown')}
| 項目 | 内容 |
|-----|------|
| **調達額** | {c.get('amount', 0)}億円（{c.get('round', '不明')}） |
| **事業内容** | {c.get('business', '不明')[:100]} |
| **本社** | {c.get('location', '不明')[:50]} |
| **代表** | {c.get('ceo', '不明')[:30]} |
| **URL** | {c.get('url', '不明')} |
| **投資家** | {c.get('investors', '不明')[:80]}... |
| **カテゴリ** | {categorize_company(c)} |

"""

    md += "\n---\n\n"

    # 全企業リスト（カテゴリ別）
    md += "## 全企業リスト（カテゴリ別）\n\n"

    for cat, items in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        md += f"### {cat}（{len(items)}社）\n\n"
        md += "| # | 企業名 | 調達額 | ラウンド | 事業内容 |\n"
        md += "|---|--------|--------|----------|----------|\n"

        for i, c in enumerate(items, 1):
            name = c.get("company", "Unknown")[:25]
            amount = c.get("amount", 0)
            round_name = c.get("round", "不明")
            business = c.get("business", "")[:40]
            md += f"| {i} | {name} | {amount}億円 | {round_name} | {business} |\n"

        md += "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md)

    return md


def generate_json_output(companies: list, output_path: str):
    """JSON出力"""
    # カテゴリ追加
    for c in companies:
        c["category"] = categorize_company(c)

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
    print("資金調達企業収集スクリプト v2")
    print("=" * 60)
    print(f"目標: {CONFIG['target_count']}社")
    print()

    # コンテナポート取得
    ports = get_container_ports()
    if not ports:
        print("エラー: Dockerコンテナが起動していません")
        return

    print(f"利用可能なブラウザコンテナ: {len(ports)}個")
    print()

    # ステップ1: リンク収集
    print("[1/3] PR TIMESから資金調達リンクを収集中...")
    all_links = collect_all_links(ports)
    print(f"  合計: {len(all_links)}件のユニークリンク\n")

    # ステップ2: 詳細収集
    print(f"[2/3] 企業詳細を収集中（目標: {CONFIG['target_count']}社）...")
    companies = collect_company_details(ports, all_links, CONFIG["target_count"])
    print(f"  合計: {len(companies)}社\n")

    # ステップ3: レポート生成
    print("[3/3] レポート生成中...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    md_path = os.path.join(CONFIG["output_dir"], f"funding_list_{timestamp}.md")
    json_path = os.path.join(CONFIG["output_dir"], f"funding_list_{timestamp}.json")

    generate_markdown_report(companies, md_path)
    generate_json_output(companies, json_path)

    print(f"\n{'=' * 60}")
    print("完了!")
    print(f"{'=' * 60}")
    print(f"  - マークダウン: {md_path}")
    print(f"  - JSON: {json_path}")
    print(f"  - 収集企業数: {len(companies)}社")


if __name__ == "__main__":
    main()
