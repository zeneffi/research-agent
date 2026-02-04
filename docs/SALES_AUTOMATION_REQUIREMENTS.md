# 営業自動化機能要件

## スキル1: sales-list-creation（営業リスト作成）

### 機能要件

| 項目 | 内容 |
|------|------|
| **目的** | 営業ターゲット企業のリストを自動作成（業種・業態を問わず柔軟に対応） |
| **入力** | ・検索クエリ（Claudeが自動解析）<br>・目標件数（デフォルト：100社） |
| **出力** | **3つ全部出力**：<br>・JSON（プログラム用）`sales_list.json`<br>・CSV（スプレッドシート用）`sales_list.csv`<br>・Markdown（レポート）`sales_list.md` |
| **収集データ** | **必須**：企業名、WebサイトURL<br>**オプション**（検索対象に応じて使い分け）：<br>・問い合わせフォームURL（全業種で有効）<br>・業種、従業員数、資本金、設立年、所在地、連絡先（全業種で有効）<br>・技術スタック（IT企業向け）<br>・資金調達情報（スタートアップ・ベンチャー企業向け） |
| **並列実行** | **15コンテナ並列**（最大限活用） |
| **検索エンジン** | DuckDuckGo必須（CLAUDE.md準拠、CAPTCHA回避） |
| **検索戦略** | ・DuckDuckGoで検索クエリを実行（**ユーザーが自由にカスタマイズ可能**）<br>・**検索例**：<br>　- スタートアップ企業：`site:prtimes.jp 資金調達 シリーズA`<br>　- IT企業：`受託開発企業 日本 React`<br>　- 製造業：`製造業 新規事業 日本`<br>　- 小売業：`小売業 DX 導入`<br>・検索結果ページから全リンクを取得<br>・各リンクに並列アクセスして企業情報を抽出 |
| **重複排除** | ・企業名の正規化（株式会社/有限会社などを統一）<br>・URL正規化（www有無、末尾スラッシュを統一） |
| **設定変更** | `config/sales_automation.json` で変更可能 |

### 実行フロー

```
1. ユーザクエリ解析
   ↓
2. DuckDuckGo検索（例は上記「検索戦略」参照、検索対象に応じて自由にカスタマイズ）
   ↓
3. 検索結果ページから全リンクを抽出
   ↓
4. 15コンテナで並列アクセス
   - 各ページから企業情報を抽出
   - 正規表現・JavaScript evaluate使用
   ↓
5. 重複排除（企業名・URL正規化）
   ↓
6. JSON/CSV/Markdown形式で出力
```

### 出力形式

**JSON** (`sales_list.json`):

*注：以下は2つの例を示しています。検索対象によって出力内容は変動します*

```json
[
  {
    "company_name": "株式会社ExampleTech",
    "website_url": "https://example-tech.com",
    "contact_form_url": "https://example-tech.com/contact",
    "industry": "Web制作",
    "employees": 50,
    "capital": "1000万円",
    "founded_year": 2020,
    "location": "東京都渋谷区",
    "contact_email": "info@example-tech.com",
    "custom_field_1": "React, TypeScript",
    "custom_field_2": "ECサイト開発10件以上",
    "custom_field_3": "エンジニア15名"
  },
  {
    "company_name": "株式会社GeneralCorp",
    "website_url": "https://general-corp.com",
    "contact_form_url": "https://general-corp.com/inquiry",
    "industry": "製造業",
    "employees": 200,
    "capital": "5000万円",
    "founded_year": 2015,
    "location": "愛知県名古屋市",
    "contact_email": "contact@general-corp.com",
    "custom_field_1": "自動車部品、精密機械",
    "custom_field_2": "愛知県、タイ工場",
    "custom_field_3": "ISO9001, ISO14001"
  }
]
```

**CSV** (`sales_list.csv`):

*注：検索対象によって出力内容は変動します*

```csv
企業名,WebサイトURL,問い合わせフォームURL,業種,従業員数,資本金,設立年,所在地,連絡先メール,カスタム項目1,カスタム項目2,カスタム項目3
株式会社ExampleTech,https://example-tech.com,https://example-tech.com/contact,Web制作,50,1000万円,2020,東京都渋谷区,info@example-tech.com,"React, TypeScript",ECサイト開発10件以上,エンジニア15名
株式会社GeneralCorp,https://general-corp.com,https://general-corp.com/inquiry,製造業,200,5000万円,2015,愛知県名古屋市,contact@general-corp.com,自動車部品・精密機械,愛知県・タイ工場,ISO9001・ISO14001
```

**Markdown** (`sales_list.md`):

*注：検索対象によって出力内容は変動します*

```markdown
# 営業リスト調査結果

調査日: 2024-01-20
検索対象: IT企業
対象件数: 100社

## カスタム項目定義
- **カスタム項目1**: 技術スタック
- **カスタム項目2**: 開発実績
- **カスタム項目3**: エンジニア数

## 1. 株式会社ExampleTech

- **Webサイト**: https://example-tech.com
- **問い合わせフォーム**: https://example-tech.com/contact
- **業種**: Web制作
- **従業員数**: 50名
- **資本金**: 1000万円
- **設立年**: 2020年
- **所在地**: 東京都渋谷区
- **連絡先**: info@example-tech.com
- **カスタム項目1（技術スタック）**: React, TypeScript
- **カスタム項目2（開発実績）**: ECサイト開発10件以上
- **カスタム項目3（エンジニア数）**: 15名

## 2. 株式会社GeneralCorp

- **Webサイト**: https://general-corp.com
- **問い合わせフォーム**: https://general-corp.com/inquiry
- **業種**: 製造業
- **従業員数**: 200名
- **資本金**: 5000万円
- **設立年**: 2015年
- **所在地**: 愛知県名古屋市
- **連絡先**: contact@general-corp.com
- **カスタム項目1（主要製品）**: 自動車部品、精密機械
- **カスタム項目2（工場所在地）**: 愛知県、タイ工場
- **カスタム項目3（ISO認証）**: ISO9001, ISO14001
```

---

## スキル2: form-sales（フォーム営業）

### 機能要件

| 項目 | 内容 |
|------|------|
| **目的** | 問い合わせフォームから営業文を自動送信 |
| **入力** | ・営業リスト（JSON/CSV）<br>・送信者情報（会社名、担当者名、メール、電話） |
| **出力** | ・送信ログ（JSON）`send_log.json`<br>・送信結果レポート（Markdown）`send_report.md`<br>・エラー時のスクリーンショット |
| **営業文生成** | **Claudeが企業情報に応じて自動選択・生成**（API不要）<br>・**パターン1（スタートアップ・ベンチャー企業向け）**：カスタム項目に資金調達情報がある場合 → 「調達おめでとうございます」<br>・**パターン2（IT企業向け）**：カスタム項目に技術スタックがある場合 → 「{tech}の開発実績を活かして」<br>・**パターン3（汎用）**：その他の企業 → 業種・事業内容・カスタム項目に合わせた柔軟な提案<br>・文字数：200-300文字<br>・具体的な提案を含む<br>・押し売り感を出さない |
| **並列実行** | **5コンテナ並列** |
| **安全対策** | ✅ レートリミット：1日100件、3分間隔<br>✅ CAPTCHA検出：検出時は自動スキップ<br>✅ 送信ログ：全送信を記録<br>✅ エラーハンドリング：タイムアウト120秒<br>✅ スクリーンショット保存：エラー時 |
| **設定変更** | `config/sales_automation.json` で全数値変更可能 |

### 営業文生成ルール

Claudeが企業情報を見て、**最適なパターンを自動選択**し、カスタマイズした営業文を生成します：

#### パターン1: スタートアップ・ベンチャー企業向け（カスタム項目1に資金調達情報がある場合）
```
{custom_field_1}で{custom_field_2}の調達おめでとうございます。
事業拡大フェーズでのリソース不足をサポートさせていただけないでしょうか。
弊社は{業種}分野での実績が豊富で、貴社の成長に貢献できると考えております。
```

#### パターン2: IT企業向け（カスタム項目1に技術スタックがある場合）
```
貴社が{custom_field_1}を活用されていることを拝見しました。
弊社も同技術での開発実績が豊富で、{業種}分野での貴社の事業に技術面でお力添えできればと考えております。
具体的な支援の可能性について、一度お話しさせていただけないでしょうか。
```

#### パターン3: 汎用（その他の企業）
```
{業種}分野で事業を展開されている貴社に、弊社のサービスをご提案させていただきたく存じます。
{企業の事業内容・特徴に応じた具体的な提案}
貴社のビジネス成長をサポートできればと考えております。
まずはお気軽にお話しできれば幸いです。
```

*注：実際の営業文は、企業情報（業種、事業内容、企業規模など）に基づいて柔軟にカスタマイズされます*

### 実行フロー

```
1. 営業リスト読み込み（JSON/CSV自動判定）
   ↓
2. レートリミットチェック
   - 日次上限（100件）確認
   - 前回送信から3分経過確認
   ↓
3. 5コンテナで並列実行（各企業）
   ├─ フォームURLに遷移
   ├─ CAPTCHA検出 → あればスキップ
   ├─ フォーム項目自動検出（name/placeholder属性）
   ├─ Claudeが営業文生成（企業情報から）
   ├─ フォーム入力・送信
   ├─ 送信ログ記録
   └─ スクリーンショット保存（エラー時）
   ↓
4. 送信結果レポート生成
```

### フォーム項目の自動検出

```javascript
// name属性から推測
{
  "company": ["会社名", "company", "organization"],
  "name": ["お名前", "氏名", "name", "your-name"],
  "email": ["メール", "email", "mail"],
  "phone": ["電話", "tel", "phone"],
  "message": ["お問い合わせ内容", "message", "inquiry", "content"]
}
```

### CAPTCHA検出

```javascript
// reCAPTCHA/hCaptchaを検出
const hasCaptcha = await page.evaluate(() => {
  return !!(
    document.querySelector('.g-recaptcha') ||
    document.querySelector('.h-captcha') ||
    document.querySelector('[data-sitekey]')
  );
});

if (hasCaptcha) {
  console.log('CAPTCHA検出 - スキップ');
  return { status: 'skipped', reason: 'CAPTCHA detected' };
}
```

### 送信ログ形式

**send_log.json**:
```json
{
  "summary": {
    "total": 100,
    "success": 85,
    "failed": 10,
    "skipped": 5,
    "started_at": "2024-01-20T10:00:00Z",
    "completed_at": "2024-01-20T15:30:00Z"
  },
  "entries": [
    {
      "company_name": "株式会社ExampleTech",
      "url": "https://example-tech.com/contact",
      "status": "success",
      "timestamp": "2024-01-20T10:05:00Z",
      "message_preview": "シリーズAで5億円の調達おめでとうございます...",
      "form_fields_detected": ["company", "name", "email", "message"]
    },
    {
      "company_name": "株式会社FailExample",
      "url": "https://fail-example.com/contact",
      "status": "failed",
      "timestamp": "2024-01-20T10:10:00Z",
      "error": "Timeout after 120 seconds",
      "screenshot": "/path/to/screenshot.png"
    },
    {
      "company_name": "株式会社CaptchaExample",
      "url": "https://captcha-example.com/contact",
      "status": "skipped",
      "timestamp": "2024-01-20T10:15:00Z",
      "reason": "CAPTCHA detected"
    }
  ]
}
```

### 送信結果レポート

**send_report.md**:
```markdown
# フォーム営業 送信結果レポート

実行日時: 2024-01-20 10:00 - 15:30

## サマリー

- **総数**: 100社
- **成功**: 85社（85%）
- **失敗**: 10社（10%）
- **スキップ**: 5社（5% - CAPTCHA検出）

## 送信成功

### 1. 株式会社ExampleTech
- **URL**: https://example-tech.com/contact
- **送信時刻**: 10:05
- **営業文**: シリーズAで5億円の調達おめでとうございます...

## 送信失敗

### 1. 株式会社FailExample
- **URL**: https://fail-example.com/contact
- **エラー**: タイムアウト（120秒超過）
- **スクリーンショット**: /path/to/screenshot.png

## スキップ

### 1. 株式会社CaptchaExample
- **URL**: https://captcha-example.com/contact
- **理由**: CAPTCHA検出
```

---

## 設定ファイル

**config/sales_automation.json**:
```json
{
  "list_creation": {
    "max_containers": 15,
    "target_count": 100,
    "search_engine": "duckduckgo"
  },
  "form_sales": {
    "max_containers": 5,
    "rate_limit": {
      "daily_limit": 100,
      "interval_seconds": 180
    },
    "timeout_seconds": 120,
    "sender_info": {
      "company_name": "",
      "contact_name": "",
      "email": "",
      "phone": ""
    }
  },
  "output_dir": "projects/sales-automation/output"
}
```

---

## スキル連携フロー

```
ユーザ指示
   ↓
sales-list-creation スキル
   ↓
sales_list.json（100社）
sales_list.csv
sales_list.md
   ↓
form-sales スキル
   ↓
send_log.json（送信結果）
send_report.md
```

### パイプライン実行

```bash
# 1. 営業リスト作成
python projects/sales-automation/scripts/create_sales_list.py

# 2. フォーム送信
python projects/sales-automation/scripts/send_sales_form.py

# 3. パイプライン統合実行
python projects/sales-automation/scripts/full_pipeline.py
```

---

## 安全性の考慮

### レートリミット
- 1日100件の送信上限
- 各送信間隔は3分（180秒）
- `send_log.json`で送信履歴を管理

### CAPTCHA対策
- reCAPTCHA/hCaptchaを自動検出
- 検出時は送信をスキップし、ログに記録

### エラーハンドリング
- タイムアウト: 120秒
- フォーム検出失敗: スキップしてログ記録
- ネットワークエラー: リトライせずスキップ

### プライバシー保護
- 送信ログには営業文のプレビューのみ保存（全文は保存しない）
- エラー時のスクリーンショットは自動保存

---

## 検証方法

### 営業リスト作成の検証
1. 小規模テスト（10社で実行）
2. JSON/CSV/Markdown全ての出力を確認
3. 重複排除の動作確認
4. 必須項目（企業名、URL）の取得確認

### フォーム送信の検証
1. テスト用フォームで送信確認
2. CAPTCHA検出の動作確認
3. レートリミットの動作確認（3分間隔）
4. 送信ログの記録確認
5. 営業文生成の品質確認

### エンドツーエンドの検証
```bash
python projects/sales-automation/scripts/full_pipeline.py
```

---

## 参考実装との対応関係

### 既存実装から再利用可能なコード

`funding_collector/collect_funding_v2.py` の以下の関数は **そのまま流用可能**：

| 関数名 | 用途 | 再利用箇所 |
|--------|------|----------|
| `get_container_ports()` | Dockerコンテナの起動確認とAPIポート取得 | **sales-list-creation**、**form-sales** 両方で使用 |
| `browser_navigate(port, url)` | ブラウザをURLにナビゲート | **sales-list-creation**（検索・企業ページ）<br>**form-sales**（フォームページ） |
| `browser_evaluate(port, script)` | ブラウザでJavaScript実行 | **sales-list-creation**（情報抽出）<br>**form-sales**（フォーム検出・入力） |
| `generate_json_output(companies, path)` | JSON形式で出力 | **sales-list-creation**（営業リスト出力） |
| `generate_markdown_report(companies, path)` | Markdownレポート生成 | **sales-list-creation**（レポート出力）※カスタマイズ必要 |

### ThreadPoolExecutor による並列実行パターン

**そのまま流用可能**（変更不要）：

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

# sales-list-creation: 15コンテナ並列
with ThreadPoolExecutor(max_workers=len(ports)) as executor:
    futures = {}
    for i, link in enumerate(batch):
        port = ports[i % len(ports)]
        futures[executor.submit(extract_company_info, port, link)] = link

    for future in as_completed(futures):
        try:
            result = future.result()
            # 結果処理
        except Exception as e:
            # エラー処理
            pass
```

### ブラウザAPI関数

以下の3つの関数がブラウザ操作の基盤（**全て再利用可能**）：

```python
# 1. コンテナ起動確認
ports = get_container_ports()  # [3001, 3002, ..., 3015]

# 2. ページ遷移
success = browser_navigate(port=3001, url="https://example.com", timeout=30)

# 3. JavaScript実行
result = browser_evaluate(port=3001, script="document.title", timeout=60)
```

---

## 新規作成が必要な関数（sales-list-creation）

以下の関数は **funding_collector にないため新規作成が必要**：

| 関数名 | 難易度 | 所要時間 | 説明 |
|--------|--------|----------|------|
| `search_duckduckgo(port, query)` | ⭐⭐ | 30分 | DuckDuckGoで検索して結果リンクを取得 |
| `extract_company_info(port, url)` | ⭐⭐⭐ | 60分 | 企業ページから情報を抽出（URL、業種、従業員数など） |
| `find_contact_form_url(port, base_url)` | ⭐⭐⭐⭐ | 90分 | 問い合わせフォームURLを検出（詳細は後述） |
| `normalize_company_name(name)` | ⭐ | 15分 | 企業名の正規化（株式会社/有限会社の統一） |
| `generate_csv_output(companies, path)` | ⭐ | 15分 | CSV形式で出力 |

**合計所要時間**: 約3.5時間

### 1. search_duckduckgo() 実装例

```python
def search_duckduckgo(port: int, query: str, page: int = 1) -> list:
    """DuckDuckGoで検索してリンク取得"""
    from urllib.parse import quote
    encoded_query = quote(query)
    url = f"https://duckduckgo.com/?q={encoded_query}&ia=web"

    if not browser_navigate(port, url):
        return []

    time.sleep(2)

    script = """(function() {
        const links = document.querySelectorAll("a[href^='http']");
        const results = [];
        const seen = new Set();
        links.forEach(a => {
            const href = a.href;
            if (!href.includes('duckduckgo.com') && !seen.has(href)) {
                seen.add(href);
                results.push({
                    title: a.textContent.trim(),
                    url: href
                });
            }
        });
        return JSON.stringify(results);
    })()"""

    result = browser_evaluate(port, script)
    return json.loads(result) if result else []
```

### 2. extract_company_info() 実装例

```python
def extract_company_info(port: int, url: str) -> Optional[dict]:
    """企業ページから情報を抽出"""
    if not browser_navigate(port, url):
        return None

    time.sleep(2)

    script = """(function() {
        const body = document.body.innerText;

        // 企業名
        let company = document.title.split(/[｜|]/)[0].trim();

        // 業種（キーワードマッチング）
        let industry = "";
        const industries = {
            "Web制作": ["web制作", "ホームページ", "サイト制作"],
            "システム開発": ["システム開発", "受託開発", "ソフトウェア"],
            "アプリ開発": ["アプリ開発", "モバイル", "スマホアプリ"]
        };
        for (const [ind, keywords] of Object.entries(industries)) {
            if (keywords.some(kw => body.toLowerCase().includes(kw))) {
                industry = ind;
                break;
            }
        }

        // 従業員数
        let employees = 0;
        const empMatch = body.match(/従業員[数]?[：:・\\s]*(\\d+)[名人]/);
        if (empMatch) employees = parseInt(empMatch[1]);

        // 資本金
        let capital = "";
        const capMatch = body.match(/資本金[：:・\\s]*([\\d,]+(?:百万|億)?円)/);
        if (capMatch) capital = capMatch[1];

        // 設立年
        let founded = 0;
        const foundMatch = body.match(/設立[：:・\\s]*(\\d{4})年/);
        if (foundMatch) founded = parseInt(foundMatch[1]);

        // 所在地
        let location = "";
        const locMatch = body.match(/(?:本社|所在地)[：:・\\s]*([^\\n]{10,50})/);
        if (locMatch) location = locMatch[1].trim();

        return JSON.stringify({
            company_name: company,
            website_url: window.location.href,
            industry: industry,
            employees: employees,
            capital: capital,
            founded_year: founded,
            location: location
        });
    })()"""

    result = browser_evaluate(port, script)
    return json.loads(result) if result else None
```

### 3. find_contact_form_url() の詳細実装

**難易度**: ⭐⭐⭐⭐（最も複雑）
**所要時間**: 90分
**想定精度**: 70-80%

#### 検出戦略（3段階フォールバック）

```python
def find_contact_form_url(port: int, base_url: str) -> Optional[str]:
    """問い合わせフォームURLを検出（3段階フォールバック）"""

    # ステップ1: トップページから「お問い合わせ」リンクを検出
    if not browser_navigate(port, base_url):
        return None

    time.sleep(2)

    # フェーズ1: リンクテキストから検出（精度: 80%）
    script_phase1 = """(function() {
        const links = document.querySelectorAll("a[href]");
        const patterns = ["お問い合わせ", "問い合わせ", "contact", "コンタクト", "ご相談"];

        for (const link of links) {
            const text = link.textContent.toLowerCase();
            const href = link.href.toLowerCase();

            if (patterns.some(p => text.includes(p) || href.includes(p))) {
                return link.href;
            }
        }
        return null;
    })()"""

    result = browser_evaluate(port, script_phase1)
    if result and result != "null":
        return result

    # フェーズ2: URL パターンから検出（精度: 60%）
    script_phase2 = """(function() {
        const links = document.querySelectorAll("a[href]");
        const urlPatterns = ["/contact", "/inquiry", "/form", "/toiawase"];

        for (const link of links) {
            const href = link.href.toLowerCase();
            if (urlPatterns.some(p => href.includes(p))) {
                return link.href;
            }
        }
        return null;
    })()"""

    result = browser_evaluate(port, script_phase2)
    if result and result != "null":
        return result

    # フェーズ3: フォーム要素の存在確認（精度: 50%）
    # トップページ自体がフォームの場合
    script_phase3 = """(function() {
        const forms = document.querySelectorAll("form");
        const hasMessageField = Array.from(forms).some(form => {
            const textareas = form.querySelectorAll("textarea");
            return textareas.length > 0;
        });

        return hasMessageField ? window.location.href : null;
    })()"""

    result = browser_evaluate(port, script_phase3)
    if result and result != "null":
        return result

    return None  # 検出失敗
```

#### 精度と制約

- **フェーズ1（リンクテキスト）**: 80% - 最も信頼性が高い
- **フェーズ2（URL パターン）**: 60% - 英語サイトで有効
- **フェーズ3（フォーム要素）**: 50% - フォールバック用
- **総合精度**: 70-80%（複数フェーズ組み合わせ）

#### 検出失敗する主なケース

1. JavaScriptで動的生成されるリンク（SPA）
2. 画像リンクのみでテキストなし
3. 問い合わせフォームが外部サービス（Googleフォームなど）
4. ログインが必要なフォーム

---

## 新規作成が必要な関数（form-sales）

| 関数名 | 難易度 | 所要時間 | 説明 |
|--------|--------|----------|------|
| `detect_form_fields(port, url)` | ⭐⭐⭐ | 60分 | フォーム項目を自動検出 |
| `generate_sales_message(company_info)` | ⭐⭐ | 45分 | 企業情報から営業文を生成 |
| `fill_and_submit_form(port, fields, data)` | ⭐⭐⭐ | 60分 | フォーム入力・送信 |
| `detect_captcha(port)` | ⭐⭐ | 30分 | CAPTCHA検出 |
| `check_rate_limit(log_path)` | ⭐ | 20分 | レートリミットチェック |
| `save_send_log(log_path, entry)` | ⭐ | 15分 | 送信ログ保存 |

**合計所要時間**: 約3.5時間

### 1. detect_form_fields() 実装例

```python
def detect_form_fields(port: int, url: str) -> Optional[dict]:
    """フォーム項目を自動検出"""
    if not browser_navigate(port, url):
        return None

    time.sleep(2)

    script = """(function() {
        const form = document.querySelector("form");
        if (!form) return null;

        const fields = {
            company: null,
            name: null,
            email: null,
            phone: null,
            message: null
        };

        // name属性から推測
        const mapping = {
            company: ["company", "会社", "organization", "kaisya"],
            name: ["name", "名前", "氏名", "your-name", "namae"],
            email: ["email", "mail", "メール"],
            phone: ["tel", "phone", "電話", "denwa"],
            message: ["message", "inquiry", "content", "お問い合わせ", "本文"]
        };

        const inputs = form.querySelectorAll("input, textarea");
        for (const input of inputs) {
            const name = (input.name || input.id || input.placeholder || "").toLowerCase();

            for (const [field, patterns] of Object.entries(mapping)) {
                if (patterns.some(p => name.includes(p))) {
                    fields[field] = input.name || input.id;
                    break;
                }
            }
        }

        return JSON.stringify(fields);
    })()"""

    result = browser_evaluate(port, script)
    return json.loads(result) if result else None
```

### 2. generate_sales_message() 実装例

```python
def generate_sales_message(company_info: dict) -> str:
    """企業情報から営業文を生成（企業情報に応じて最適なパターンを自動選択）"""
    company = company_info.get("company_name", "")
    custom_1 = company_info.get("custom_field_1", "")
    custom_2 = company_info.get("custom_field_2", "")
    custom_3 = company_info.get("custom_field_3", "")
    industry = company_info.get("industry", "")

    # カスタム項目の内容から企業タイプを推測して最適なパターンを選択
    
    # パターン1: 資金調達企業向け
    # custom_field_1が「シリーズA」「シリーズB」などを含む場合
    if custom_1 and any(keyword in custom_1 for keyword in ["シリーズ", "ラウンド", "資金調達"]):
        return f"""{custom_1}で{custom_2}の調達おめでとうございます。
事業拡大フェーズでのリソース不足をサポートさせていただけないでしょうか。
弊社は{industry}分野での実績が豊富で、貴社の成長に貢献できると考えております。
まずはお気軽にお話しできれば幸いです。"""

    # パターン2: IT企業向け
    # custom_field_1が技術スタックっぽい場合（React、Python、JavaScriptなど）
    elif custom_1 and any(tech in custom_1 for tech in ["React", "Python", "JavaScript", "TypeScript", "Java", "PHP", "Ruby", "Go"]):
        return f"""貴社が{custom_1}を活用されていることを拝見しました。
弊社も同技術での実績が豊富で、{industry}分野での貴社の事業に技術面でお力添えできればと考えております。
具体的な支援の可能性について、一度お話しさせていただけないでしょうか。"""

    # パターン3: 製造業向け
    # custom_field_3にISO認証が含まれる場合
    elif custom_3 and "ISO" in custom_3:
        return f"""{industry}分野で{custom_1}を手がける貴社に、弊社のサービスをご提案させていただきたく存じます。
{custom_3}を取得されている貴社の品質へのこだわりに、弊社も貢献できればと考えております。
まずはお気軽にお話しできれば幸いです。"""

    # パターン4: 汎用（その他の企業）
    elif industry:
        return f"""{industry}分野で事業を展開されている貴社に、弊社のサービスをご提案させていただきたく存じます。
貴社のビジネス成長をサポートできればと考えております。
まずはお気軽にお話しできれば幸いです。"""
    else:
        # 業種情報がない場合のフォールバック
        return f"""貴社の事業内容を拝見し、弊社のサービスをご提案させていただきたく存じます。
貴社のビジネス成長をサポートできればと考えております。
まずはお気軽にお話しできれば幸いです。"""
```

### 3. fill_and_submit_form() 実装例

```python
def fill_and_submit_form(port: int, fields: dict, data: dict) -> bool:
    """フォーム入力・送信"""
    script = f"""(function() {{
        try {{
            // 会社名
            if ("{fields['company']}") {{
                const comp = document.querySelector("[name='{fields['company']}']");
                if (comp) comp.value = "{data['company']}";
            }}

            // 氏名
            if ("{fields['name']}") {{
                const name = document.querySelector("[name='{fields['name']}']");
                if (name) name.value = "{data['name']}";
            }}

            // メール
            if ("{fields['email']}") {{
                const email = document.querySelector("[name='{fields['email']}']");
                if (email) email.value = "{data['email']}";
            }}

            // 電話
            if ("{fields['phone']}") {{
                const phone = document.querySelector("[name='{fields['phone']}']");
                if (phone) phone.value = "{data['phone']}";
            }}

            // メッセージ
            if ("{fields['message']}") {{
                const msg = document.querySelector("[name='{fields['message']}']");
                if (msg) msg.value = `{data['message']}`;
            }}

            // 送信ボタンをクリック
            const submitBtn = document.querySelector("button[type='submit'], input[type='submit']");
            if (submitBtn) {{
                submitBtn.click();
                return true;
            }}

            return false;
        }} catch(e) {{
            return false;
        }}
    }})()"""

    result = browser_evaluate(port, script)
    return result == "true"
```

---

## 実装の全体像

### sales-list-creation の実装フロー

```python
def main():
    # 1. 既存関数（再利用）
    ports = get_container_ports()  # ← funding_collector から

    # 2. 新規関数（検索クエリはユーザーが自由にカスタマイズ）
    # 例: スタートアップ企業 → "site:prtimes.jp 資金調達 シリーズA"
    # 例: IT企業 → "受託開発企業 日本 React"
    # 例: 製造業 → "製造業 新規事業 日本"
    search_results = search_duckduckgo(ports[0], query)  # query はユーザー指定

    # 3. 既存の並列実行パターン（再利用）
    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {}
        for i, result in enumerate(search_results):
            port = ports[i % len(ports)]
            futures[executor.submit(extract_company_info, port, result['url'])] = result

        companies = []
        for future in as_completed(futures):
            info = future.result()
            if info:
                # 新規関数
                info['contact_form_url'] = find_contact_form_url(port, info['website_url'])
                companies.append(info)

    # 4. 既存の出力関数（再利用）
    generate_json_output(companies, "sales_list.json")  # ← funding_collector から
    generate_markdown_report(companies, "sales_list.md")  # ← funding_collector から
    # 新規関数
    generate_csv_output(companies, "sales_list.csv")
```

### form-sales の実装フロー

```python
def main():
    # 1. 既存関数（再利用）
    ports = get_container_ports()  # ← funding_collector から

    # 2. 営業リスト読み込み
    with open("sales_list.json") as f:
        companies = json.load(f)

    # 3. レートリミットチェック（新規）
    if not check_rate_limit("send_log.json"):
        return

    # 4. 並列送信（ThreadPoolExecutor再利用 + 新規関数）
    with ThreadPoolExecutor(max_workers=5) as executor:
        for company in companies:
            # CAPTCHA検出（新規）
            if detect_captcha(port):
                continue

            # フォーム検出（新規）
            fields = detect_form_fields(port, company['contact_form_url'])

            # 営業文生成（新規）
            message = generate_sales_message(company)

            # フォーム送信（新規 + 既存のbrowser_evaluate）
            success = fill_and_submit_form(port, fields, {
                'company': '送信元会社',
                'name': '担当者名',
                'email': 'info@example.com',
                'phone': '03-1234-5678',
                'message': message
            })

            # ログ保存（新規）
            save_send_log("send_log.json", {...})
```

---

## 開発の進め方

### Step 1: sales-list-creation（目安: 1日）

1. ✅ 既存関数のコピー（30分）
   - `get_container_ports()`
   - `browser_navigate()`
   - `browser_evaluate()`
   - `generate_json_output()`
   - `generate_markdown_report()`

2. 新規関数の実装（3.5時間）
   - `search_duckduckgo()` - 30分
   - `extract_company_info()` - 60分
   - `find_contact_form_url()` - 90分（最難関）
   - `normalize_company_name()` - 15分
   - `generate_csv_output()` - 15分

3. メイン処理の実装（1時間）
   - ThreadPoolExecutorでの並列実行統合
   - 重複排除ロジック

4. テスト（2時間）
   - 小規模テスト（10社）
   - 出力形式確認

### Step 2: form-sales（目安: 1日）

1. ✅ 既存関数の再利用（15分）
   - `get_container_ports()`
   - `browser_navigate()`
   - `browser_evaluate()`

2. 新規関数の実装（3.5時間）
   - `detect_form_fields()` - 60分
   - `generate_sales_message()` - 45分
   - `fill_and_submit_form()` - 60分
   - `detect_captcha()` - 30分
   - `check_rate_limit()` - 20分
   - `save_send_log()` - 15分

3. メイン処理の実装（1.5時間）
   - 並列送信ロジック
   - エラーハンドリング

4. テスト（2時間）
   - テストフォームでの検証
   - CAPTCHA検出テスト

### Step 3: 統合とドキュメント（目安: 0.5日）

1. パイプライン統合（1時間）
2. 設定ファイル作成（30分）
3. README作成（30分）

**総開発時間**: 約2.5日
