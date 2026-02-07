"""
DuckDuckGo検索機能
"""
import re
import time
from urllib.parse import quote, urlparse
from typing import List, Dict, Optional
from .browser import browser_navigate, browser_evaluate


# 除外ドメイン（検索結果から除外するサイト）- setでO(1)検索
SKIP_DOMAINS = {
    # 検索エンジン
    'duckduckgo', 'google', 'bing', 'yahoo',
    # SNS
    'facebook', 'twitter', 'instagram', 'youtube', 'linkedin', 'tiktok',
    # 大手サイト
    'wikipedia', 'amazon', 'rakuten',
    # 求人サイト
    'indeed', 'wantedly', 'mynavi', 'rikunabi', 'doda', 'en-japan', 'type',
    'green-japan', 'bizreach', 'careerconnection',
    # CDN/インフラ
    'cloudflare', 'jsdelivr', 'googleapis', 'gstatic',
    # IT系比較・まとめサイト
    'itmedia', 'ferret-plus', 'boxil', 'itreview', 'saasus', 'bcnretail',
    'ascii', 'impress', 'zdnet', 'cnet', 'techcrunch', 'gizmodo',
    # 企業DB・まとめサイト
    'baseconnect', 'musubu', 'biz-maps', 'tdb', 'tsr-net',
    'en-hyouban', 'jobtalk', 'openwork', 'vorkers', 'lighthouse',
    # フリーランス・クラウドソーシング
    'crowdworks', 'lancers', 'coconala', 'freenance',
    # ニュース・メディア
    'prtimes', 'atpress', 'dreamnews', 'jiji', 'nikkei', 'asahi', 'yomiuri',
    # その他まとめ系
    'matome', 'naver', 'qiita', 'zenn', 'note.com', 'medium',
    'hatena', 'livedoor', 'seesaa', 'fc2', 'ameblo',
    # 発注・比較サイト（営業リストに不適切）
    'proni', 'imitsu', 'imi-tsuite',  # アイミツ/PRONI
    'system-kanji',  # システム幹事
    'hacchu-lounge', 'hacchulounge',  # 発注ラウンジ
    'itcapital', '1st-net',  # ITキャピタル
    '発注ナビ', 'haccyu-navi', '発注navi', 'hnavi',  # 発注ナビ
    'rekaizen', 'compare-biz', 'comparebiz',  # 比較ビズ
    'web-kanji', 'webkanji',  # Web幹事
    'meetsmore', 'ミツモア',
    'kakaku', '価格.com',
    'kakutoku',  # カクトク
    'saleshub',  # セールスハブ
    # ブログプラットフォーム
    'wordpress.com', 'wix', 'jimdo', 'weebly',
    # 開発者向け（企業サイトではない）
    'github', 'gitlab', 'bitbucket', 'stackoverflow',
    # 追加（テストで検出）
    'salesnow',  # SalesNow DB
    'shukatu-kyokasho', 'syukatu',  # 就活系
    'emeao',  # EMEAO
    'consul-go', 'consulgo',  # コンサルGO
    # 追加（2026-02-06: まとめサイト混入対策）
    'andmedia', 'itpark',  # IT PARK
    'gicp',  # GICP まとめ記事
    'digima',  # Digima
    '発注先探し', 'sourcing',
    'web-production-navigator',  # Web制作ナビ
    'lp-maker', 'lpmaker',  # LP系まとめ
    'system-kanji', 'systemkanji',  # システム幹事
    'dx-navi', 'dxnavi',  # DXナビ
    # 追加（2026-02-07: 検索テストで検出）
    'genee',  # GeNEE まとめ記事
    'liginc', 'lig',  # LIG ブログ
    'crexgroup',  # CREX まとめ
    'sidebiz-recipe',  # 副業レシピ
    'techpartner',  # テックパートナー
    'webtan',  # Web担当者Forum
    'markezine',  # MarkeZine
    'liskul',  # LISKUL
    'seleck',  # SELECK
    'fastgrow',  # FastGrow
    'thebridge',  # The Bridge
    'bridgewriters',  # ブリッジライターズ
}

# まとめ記事を示すタイトルキーワード（タイトルにこれらが含まれる場合は除外）
SKIP_TITLE_KEYWORDS = [
    'おすすめ',
    'オススメ',
    '選',  # ○選
    '比較',
    'ランキング',
    'まとめ',
    '一覧',
    '厳選',
    '徹底解説',
    '完全ガイド',
    'TOP',
    'Best',
]

# まとめ記事を示すURLパスパターン（正規表現）
SKIP_URL_PATTERNS = [
    r'/おすすめ',
    r'/オススメ',
    r'/recommend',
    r'/比較',
    r'/hikaku',
    r'/ランキング',
    r'/ranking',
    r'/\d+選',  # 10選、20選など
    r'/top-?\d+',  # top10, top-20など
    r'/best-?\d+',
    r'/まとめ',
    r'/matome',
    r'/一覧',
    r'/list/',
    r'/companies?/',  # /company/, /companies/
    r'/blog/',  # ブログ記事
    r'/column/',  # コラム記事
    r'/knowledge/',  # ナレッジ記事
    r'/contents?/',  # コンテンツ記事
    r'/article/',  # 記事
    r'/news/',  # ニュース
    r'/magazine/',  # マガジン
]


def search_duckduckgo(port: int, query: str, max_results: int = 10, scroll_pages: int = 3, exclude_matome: bool = True, use_site_operator: bool = False) -> List[Dict[str, str]]:
    """
    DuckDuckGoで検索して結果を取得（スクロールで追加結果も取得）

    Args:
        port: ブラウザコンテナのポート
        query: 検索クエリ
        max_results: 最大取得件数
        scroll_pages: スクロール回数（追加読み込み回数）
        exclude_matome: まとめサイト除外キーワードをクエリに追加するか
        use_site_operator: site:co.jp / site:.jp を使用して企業サイトに限定するか

    Returns:
        [{title: str, url: str, snippet: str}, ...]
    """
    # site:オペレータで企業ドメインに限定（まとめサイト排除に効果大）
    if use_site_operator:
        # co.jpドメインに限定（日本企業の公式サイト率が高い）
        query = f'site:co.jp {query}'
    
    # まとめサイト除外キーワードを追加
    if exclude_matome:
        exclude_terms = '-おすすめ -比較 -ランキング -まとめ -一覧 -選び方'
        query = f'{query} {exclude_terms}'
    
    encoded_query = quote(query)
    url = f"https://duckduckgo.com/?q={encoded_query}"

    if not browser_navigate(port, url):
        return []

    # ページロード待機
    time.sleep(3)

    all_results = []
    seen_urls = set()

    # 検索結果を抽出するJavaScript
    extract_script = """(function() {
        const results = [];
        const seen = new Set();

        // DuckDuckGoの検索結果セレクタ
        const resultElements = document.querySelectorAll('article[data-testid="result"], div[data-testid="result"]');

        resultElements.forEach(elem => {
            try {
                // タイトルとURL
                const linkElem = elem.querySelector('a[data-testid="result-title-a"], h2 a');
                if (!linkElem) return;

                const url = linkElem.href;
                const title = linkElem.textContent.trim();

                // スニペット
                let snippet = '';
                const snippetElem = elem.querySelector('div[data-result="snippet"]');
                if (snippetElem) {
                    snippet = snippetElem.textContent.trim();
                }

                // 重複チェック
                if (url && title && !seen.has(url)) {
                    seen.add(url);
                    results.push({
                        title: title,
                        url: url,
                        snippet: snippet.substring(0, 200)
                    });
                }
            } catch (e) {
                // エラー無視
            }
        });

        return JSON.stringify(results);
    })()"""

    # スクロールして追加結果を取得
    scroll_script = """(function() {
        // ページ最下部にスクロール
        window.scrollTo(0, document.body.scrollHeight);
        
        // 「もっと見る」ボタンがあればクリック
        const moreButton = document.querySelector('button[data-testid="more-results"], button.result--more__btn');
        if (moreButton) {
            moreButton.click();
            return true;
        }
        return false;
    })()"""

    for page in range(scroll_pages + 1):
        # 結果を抽出
        result = browser_evaluate(port, extract_script)
        if result:
            try:
                import json
                page_results = json.loads(result)
                for r in page_results:
                    url = r.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
            except:
                pass

        # 十分な結果が集まったら終了
        if len(all_results) >= max_results * 2:  # フィルタリング後を考慮
            break

        # 次のページをロード（最後のページ以外）
        if page < scroll_pages:
            browser_evaluate(port, scroll_script)
            time.sleep(2)  # 読み込み待機

    # 除外ドメイン・URLパターン・タイトルキーワードのフィルタリング
    filtered_results = []
    for r in all_results:
        url = r.get('url', '')
        title = r.get('title', '')
        
        # is_valid_company_url で総合判定
        if not is_valid_company_url(url):
            continue
        
        # タイトルにまとめ記事キーワードが含まれる場合は除外
        if is_matome_title(title):
            continue

        filtered_results.append(r)

    return filtered_results[:max_results]


def generate_query_variations(base_query: str) -> List[str]:
    """
    基本クエリから検索バリエーションを生成（公式サイト発見率を高める戦略）

    Args:
        base_query: 基本クエリ（例: "東京 システム開発会社"）

    Returns:
        クエリのリスト
    """
    variations = []

    # 地域を抽出
    regions = ['東京', '大阪', '名古屋', '福岡', '横浜', '札幌', '仙台', '神戸', '京都', '広島']
    found_region = None
    for region in regions:
        if region in base_query:
            found_region = region
            break

    # 基本クエリから業種キーワードを抽出
    industry_keyword = None
    it_keywords = [
        'システム開発', 'Web制作', 'アプリ開発', 'IT企業', 'ソフトウェア開発',
        'Webサービス', 'SaaS', 'Webシステム', 'DX支援', 'システム'
    ]
    for kw in it_keywords:
        if kw in base_query:
            industry_keyword = kw
            break

    # === 戦略1: 公式ページを狙うキーワード ===
    # 「会社概要」「事業内容」はまとめサイトには存在しない
    official_page_keywords = ['会社概要', '事業内容', '企業情報']
    
    for official_kw in official_page_keywords:
        if found_region and industry_keyword:
            variations.append(f'"{official_kw}" {found_region} {industry_keyword}')
        elif industry_keyword:
            variations.append(f'"{official_kw}" {industry_keyword}')
    
    # === 戦略2: 法人格を明示 ===
    # 「株式会社」「有限会社」を付けると公式サイトがヒットしやすい
    corp_types = ['株式会社', '合同会社']
    
    for corp in corp_types:
        if found_region and industry_keyword:
            variations.append(f'{found_region} {corp} {industry_keyword}')
        elif industry_keyword:
            variations.append(f'{corp} {industry_keyword}')

    # === 戦略3: 基本クエリもバリエーションに追加 ===
    if base_query not in variations:
        variations.append(base_query)

    # === 戦略4: 地域を細分化（東京の場合） ===
    tokyo_areas = ['渋谷区', '港区', '新宿区', '千代田区', '品川区', '中央区']
    if found_region == '東京' and industry_keyword:
        for area in tokyo_areas[:3]:  # 上位3区のみ
            variations.append(f'{area} {industry_keyword}')

    # === 戦略5: 業種の言い換え ===
    it_variations = {
        'システム開発': ['受託開発', 'SI', 'システムインテグレーター'],
        'Web制作': ['ホームページ制作', 'Webサイト制作'],
        'アプリ開発': ['スマホアプリ開発', 'モバイルアプリ開発'],
    }
    
    if industry_keyword and industry_keyword in it_variations:
        for alt_kw in it_variations[industry_keyword][:2]:
            if found_region:
                variations.append(f'{found_region} {alt_kw}')
            else:
                variations.append(alt_kw)

    # 重複除去して最大10バリエーション
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique_variations.append(v)
    
    return unique_variations[:10]


def is_matome_title(title: str) -> bool:
    """
    タイトルがまとめ記事っぽいかチェック

    Args:
        title: 検索結果のタイトル

    Returns:
        True: まとめ記事っぽい, False: 企業サイトっぽい
    """
    if not title:
        return False
    
    title_lower = title.lower()
    
    for keyword in SKIP_TITLE_KEYWORDS:
        if keyword.lower() in title_lower:
            return True
    
    # 数字+選のパターン（10選、20選など）
    if re.search(r'\d+選', title):
        return True
    
    return False


def is_valid_company_url(url: str) -> bool:
    """
    企業サイトとして妥当なURLかチェック

    Args:
        url: チェック対象URL

    Returns:
        True: 妥当, False: 不適切
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()

        # 除外ドメイン
        if any(skip in domain for skip in SKIP_DOMAINS):
            return False

        # まとめ記事URLパターン除外
        for pattern in SKIP_URL_PATTERNS:
            if re.search(pattern, path):
                return False

        # 企業サイトらしいドメイン
        if '.co.jp' in domain or '.jp' in domain or '.com' in domain:
            return True

        return False
    except:
        return False


def determine_search_context(query: str) -> str:
    """
    クエリから業種を自動判定

    Args:
        query: ユーザー入力のクエリ

    Returns:
        業種コンテキスト（IT, Manufacturing, Startup, General）
    """
    query_lower = query.lower()

    # IT系キーワード
    it_keywords = [
        'it', 'システム', 'ソフトウェア', '開発', 'web', 'アプリ',
        'saas', 'エンジニア', 'プログラミング', 'ai', 'dx'
    ]

    # 製造業系キーワード
    manufacturing_keywords = [
        '製造', '工場', '生産', 'メーカー', '部品', '機械',
        '自動車', '電子', '化学', '素材'
    ]

    # スタートアップ系キーワード
    startup_keywords = [
        'スタートアップ', 'ベンチャー', '資金調達', 'シード',
        'シリーズa', 'シリーズb', '起業'
    ]

    # キーワードマッチ
    if any(kw in query_lower for kw in startup_keywords):
        return 'Startup'

    if any(kw in query_lower for kw in it_keywords):
        return 'IT'

    if any(kw in query_lower for kw in manufacturing_keywords):
        return 'Manufacturing'

    return 'General'
