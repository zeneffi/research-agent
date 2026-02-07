"""
企業情報抽出機能（v2 - 会社名抽出強化版）
"""
import re
import time
from typing import Optional, Dict, Any
from .browser import browser_navigate, browser_evaluate

# 企業名として不適切なパターン（スキップ対象）
NG_TITLE_PATTERNS = {
    # 法的ページ
    '利用規約', 'プライバシーポリシー', '個人情報保護', '特定商取引法', 'お問い合わせ',
    # まとめサイト・メディア
    '全国法人検索', '就活の教科書', '懸賞生活', 'おすすめ', '比較', 'ランキング',
    '選び方', '一覧', 'まとめ', '転職', '求人', 'Indeed', 'マイナビ', 'リクナビ',
    # 非企業ページ
    'サイトマップ', 'お知らせ', 'ニュース', 'ブログ', 'コラム', 'メディア',
    '編集ポリシー', '解約', '退会', 'FAQ', 'ヘルプ',
    # 2026-02-09: 無意味なタイトル追加
    'この条件から検索', '条件から検索', '企業名 株式会社', '検索結果',
    'トップページ', 'ホーム', 'HOME', 'TOP', '主な支援策', '支援策',
    'デジタル化推進', 'ポータル', '展示会', 'EXPO', 'イベント',
    # 行政機関
    'GovTech', '東京都', '都庁', '市役所', '区役所', '県庁',
    '内閣', '省庁', '政府', '自治体',
    # 2026-02-09: 曖昧・一般的すぎる名前
    '会社概要', '各部門の紹介', '導入事例', 'キャリア採用', '募集要項',
    '実績紹介', '開催場所', '配信元', 'English', 'ロゴに込めた', 'UX / UI 専攻',
    '個人事業主の場合', '業者探し', 'プログラミングなび', 'マナビタイム',
    'キャリアトラス', 'タレントスクエア', '毎日新聞', 'Forbidden', '403',
}

def is_valid_company_name(name: str) -> bool:
    """企業名として有効かチェック"""
    if not name or len(name) < 2:
        return False
    
    # 前後の空白を除去
    name = name.strip()
    
    # NGパターンを含むか
    name_lower = name.lower()
    for ng in NG_TITLE_PATTERNS:
        if ng.lower() in name_lower:
            return False
    
    # 法人格のみ、または法人格+1-2文字だけの名前は除外
    # 例: "株式会社", "対応 株式会社", "Form 株式会社"
    corp_patterns = ['株式会社', '有限会社', '合同会社', '合資会社']
    for corp in corp_patterns:
        if corp in name:
            # 法人格を除いた部分を取得
            name_without_corp = name.replace(corp, '').strip()
            # 法人格を除いた部分が短すぎる（3文字未満）なら除外
            if len(name_without_corp) < 3:
                return False
            # 一般的な単語のみの場合も除外
            generic_words = ['対応', 'Form', 'English', '会社', '07', '配信元', '開催場所', '導入事例']
            if name_without_corp in generic_words:
                return False
    
    # 法人格を含むか（より信頼性が高い）
    has_corp = any(corp in name for corp in ['株式会社', '有限会社', '合同会社', '合資会社', 'Inc', 'LLC', 'Ltd'])
    # 法人格がなくても、NGでなければOK（ただし短すぎるのはNG）
    if not has_corp and len(name) < 4:
        return False
    
    return True


def extract_company_info(port: int, url: str, search_context: str = 'General') -> Optional[Dict[str, Any]]:
    """
    企業ページから情報を抽出

    Args:
        port: ブラウザコンテナのポート
        url: 企業サイトURL
        search_context: 業種コンテキスト（IT, Manufacturing, Startup, General）

    Returns:
        {
            company_name: str,
            company_url: str,
            location: str,
            business: str,
            custom_field_1: str,
            custom_field_2: str,
            custom_field_3: str,
        }
    """
    if not browser_navigate(port, url):
        return None

    # ページロード待機
    time.sleep(2)

    # 基本情報抽出スクリプト（v2: 会社名抽出を大幅強化）
    script = f"""(function() {{
        const body = document.body.innerText;
        const title = document.title;
        const hostname = window.location.hostname;

        // === 会社名抽出のヘルパー関数 ===
        
        // 法人格を含むかチェック
        function hasCorpSuffix(name) {{
            return /(?:株式会社|有限会社|合同会社|合資会社|一般社団法人|一般財団法人)/.test(name);
        }}
        
        // 無効な会社名パターンをチェック
        function isInvalidName(name) {{
            if (!name || name.length < 2) return true;
            
            const invalidPatterns = [
                /^(採用情報|会社概要|事業内容|お問い合わせ|アクセス|ニュース|ブログ)/,
                /^(会社名|商号|運営会社|社名)/,
                /^(トップ|ホーム|TOP|HOME|Menu|サービス|事例|実績|概要)/i,
                /^\\d{{2,4}}\\s*(株式会社|有限会社|合同会社)/,  // 「21 株式会社」「2026 株式会社」等
                /^(送信|確認|入力|完了|登録)\\s*(株式会社|有限会社|合同会社)/,
                /(様|御中|殿)\\s*(株式会社|有限会社|合同会社)/,
                /^[A-Z]{{2,5}}$/,  // 単なる略語（ABC等）
                /ここに.*(?:入り|入力|記載)/,  // プレースホルダー
                /\\(.*説明.*\\)/,  // (ここにサイトの説明が入ります)等
                /^\\s*$/,
                /^(Movie|Video|Photo|Image|News|Blog|Contact)\\s*(株式会社)?$/i,
            ];
            
            for (const pattern of invalidPatterns) {{
                if (pattern.test(name)) return true;
            }}
            return false;
        }}
        
        // 会社名をクリーンアップ
        function cleanCompanyName(name) {{
            if (!name) return '';
            
            // 前後の空白除去
            name = name.trim();
            
            // パイプ・ダッシュ以降を削除（会社名が先頭にある場合）
            if (hasCorpSuffix(name.split(/[｜|\\-–—]/)[0])) {{
                name = name.split(/[｜|\\-–—]/)[0].trim();
            }}
            
            // 括弧内の余分なテキストを削除（ただし社名の一部っぽい場合は残す）
            name = name.replace(/\\s*[（(][^）)]*(?:説明|ここに|サイト|ページ)[^）)]*[）)]\\s*/g, '');
            
            // 「会社名」「商号」等のラベルを除去
            name = name.replace(/^(?:会社名|商号|社名|運営会社)[：:・\\s]*/g, '');
            
            // 【公式】等を除去
            name = name.replace(/^【[^】]*】\\s*/, '');
            
            // 連続空白を1つに
            name = name.replace(/[\\s　]+/g, ' ').trim();
            
            // 末尾のゴミを除去
            name = name.replace(/\\s*[-–—]\\s*$/, '').trim();
            name = name.replace(/\\s*[｜|]\\s*$/, '').trim();
            
            return name;
        }}
        
        // ドメインから会社名を推測
        function guessNameFromDomain() {{
            // www. と .co.jp/.jp/.com 等を除去
            let domain = hostname.replace(/^www\\./, '').replace(/\\.(co\\.jp|or\\.jp|ne\\.jp|ac\\.jp|jp|com|net|org)$/, '');
            
            // ハイフンをスペースに、キャメルケースを分割
            domain = domain.replace(/-/g, ' ');
            domain = domain.replace(/([a-z])([A-Z])/g, '$1 $2');
            
            // 頭文字大文字化
            domain = domain.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            
            return domain;
        }}

        // === 企業名抽出（優先度順） ===
        let companyName = '';
        let candidates = [];

        // 1. meta要素から取得（最も信頼性が高い）
        const ogSiteName = document.querySelector('meta[property="og:site_name"]')?.content;
        if (ogSiteName && ogSiteName.length > 2 && ogSiteName.length < 60) {{
            candidates.push({{ name: ogSiteName.trim(), source: 'og:site_name', priority: 1 }});
        }}

        // 2. 構造化データ（JSON-LD）から取得
        const jsonLd = document.querySelector('script[type="application/ld+json"]');
        if (jsonLd) {{
            try {{
                const data = JSON.parse(jsonLd.textContent);
                if (data.name) {{
                    candidates.push({{ name: data.name, source: 'json-ld', priority: 2 }});
                }}
                if (data.legalName) {{
                    candidates.push({{ name: data.legalName, source: 'json-ld-legal', priority: 1 }});
                }}
            }} catch(e) {{}}
        }}

        // 3. 明示的な「会社名：〇〇」形式（本文から）
        const explicitMatch = body.match(/(?:会社名|社名|商号|運営会社)[：:・\\s]+([^\\n、,（(｜|]+)/);
        if (explicitMatch && explicitMatch[1].trim().length > 2) {{
            candidates.push({{ name: explicitMatch[1].trim(), source: 'explicit', priority: 1 }});
        }}

        // 4. タイトルから法人格を含む形式を抽出
        // 前株パターン
        const titlePrefixMatch = title.match(/((?:株式会社|有限会社|合同会社|合資会社)[^｜|\\-–—\\n]+)/);
        if (titlePrefixMatch) {{
            candidates.push({{ name: titlePrefixMatch[1].trim(), source: 'title-prefix', priority: 3 }});
        }}
        // 後株パターン
        const titlePostfixMatch = title.match(/([^｜|\\-–—\\n]+(?:株式会社|有限会社|合同会社|合資会社))/);
        if (titlePostfixMatch) {{
            candidates.push({{ name: titlePostfixMatch[1].trim(), source: 'title-postfix', priority: 3 }});
        }}

        // 5. タイトルの区切り文字前
        const titleFirstPart = title.split(/[｜|\\-–—]/)[0].trim();
        if (titleFirstPart && titleFirstPart.length > 2 && titleFirstPart.length < 60) {{
            candidates.push({{ name: titleFirstPart, source: 'title-first', priority: 5 }});
        }}

        // 6. ドメインからの推測（最終手段）
        const domainGuess = guessNameFromDomain();
        if (domainGuess && domainGuess.length > 2) {{
            candidates.push({{ name: domainGuess, source: 'domain', priority: 10 }});
        }}

        // === 候補を評価して最適なものを選択 ===
        // 優先度でソート（低い方が高優先）
        candidates.sort((a, b) => a.priority - b.priority);
        
        for (const candidate of candidates) {{
            const cleaned = cleanCompanyName(candidate.name);
            if (!isInvalidName(cleaned)) {{
                // 法人格を含む候補を優先
                if (hasCorpSuffix(cleaned)) {{
                    companyName = cleaned;
                    break;
                }}
                // 法人格なしでも、他に候補がなければ採用
                if (!companyName) {{
                    companyName = cleaned;
                }}
            }}
        }}
        
        // 最終フォールバック
        if (!companyName || isInvalidName(companyName)) {{
            companyName = guessNameFromDomain() + '（推定）';
        }}

        // === 所在地抽出 ===
        let location = '';
        const locationPatterns = [
            /(?:本社所在地|所在地|住所|本社)[：:・\\s]*([^\\n]+)/,
            /〒\\s*[0-9\\-]+\\s*([^\\n]+)/,
        ];
        for (const pattern of locationPatterns) {{
            const match = body.match(pattern);
            if (match) {{
                location = match[1].trim().substring(0, 100);
                break;
            }}
        }}

        // === 事業内容抽出 ===
        let business = '';
        const businessPatterns = [
            /(?:事業内容|業務内容|サービス内容)[：:・\\s]*([^\\n]+)/,
            /(?:主な事業|事業概要)[：:・\\s]*([^\\n]+)/,
        ];
        for (const pattern of businessPatterns) {{
            const match = body.match(pattern);
            if (match) {{
                business = match[1].trim().substring(0, 200);
                break;
            }}
        }}

        // === カスタム項目抽出（業種別） ===
        let custom1 = '', custom2 = '', custom3 = '';
        const searchContext = '{search_context}';

        if (searchContext === 'IT') {{
            const techMatch = body.match(/(?:使用技術|技術スタック|Tech Stack)[：:・\\s]*([^\\n]+)/);
            if (techMatch) custom1 = techMatch[1].trim().substring(0, 200);
            
            const engMatch = body.match(/エンジニア[：:・\\s]*(\\d+)[名人]/);
            if (engMatch) custom2 = engMatch[1] + '名';
            
            const devMatch = body.match(/(?:開発実績|実績)[：:・\\s]*([^\\n]+)/);
            if (devMatch) custom3 = devMatch[1].trim().substring(0, 200);
        }}

        return JSON.stringify({{
            company_name: companyName,
            company_url: window.location.href,
            location: location,
            business: business,
            custom_field_1: custom1,
            custom_field_2: custom2,
            custom_field_3: custom3,
        }});
    }})()"""

    result = browser_evaluate(port, script)
    if not result:
        return None

    try:
        import json
        data = json.loads(result)
        # 企業名のNG判定
        if not is_valid_company_name(data.get('company_name', '')):
            return None
        return data
    except:
        return None
