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
    '発注ナビ', 'haccyu-navi', '発注navi',  # 発注ナビ（hnaviは企業サイトもあるので除外）
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
    # 2026-02-08: 企業コンテンツサイトは除外しない（URLパスで判定）
    # 以下は削除: andmedia, gicp, hnavi（企業のメディア部門）
    # 追加（テストで検出）
    'houjin.goo',  # 全国法人検索（企業DBサイト）
    # 2026-02-08: メディア・情報サイト追加
    'fallabs',  # ITキャリアメディア
    'hojokin-ouendan',  # 補助金情報メディア
    'ikesai',  # いけてるサイト.com（Web制作比較）
    'sakufuri',  # サクフリマーケ（マーケティングメディア）
    'neeed',  # NeeeD（開発会社比較）
    'qopo',  # Qopo:MEDIA（Web制作比較）
    'freeconsul',  # コンサルGO
    'tobus',  # 都バス
    # 2026-02-09: 比較サイト・ポータル追加
    'system-dev-navi',  # システム開発ナビ（比較サイト）
    'odex-telex',  # ODEX展示会
    'telex',  # 展示会系
    'tokyo-kosha',  # 東京都中小企業振興公社
    'tokyo-cci',  # 東京商工会議所
    'jcci',  # 日本商工会議所
    'jetro',  # JETRO
    'smrj',  # 中小機構
    # 2026-02-09: エージェント・比較サイト追加
    'mid-works', 'midworks',  # Midworks（エージェント）
    'itpark', 'it-park',  # IT PARK（比較サイト）
    'andmedia',  # andmedia（IT PARK運営元）
    'geekly',  # ギークリー（エージェント）
    'levtech',  # レバテック（エージェント）
    'crowdtech',  # クラウドテック（エージェント）
}

# 行政・公共機関ドメイン（企業リストから除外）
GOVERNMENT_DOMAINS = {
    '.lg.jp',      # 地方自治体
    '.go.jp',      # 政府機関
    '.or.jp',      # 公益法人・財団法人
    '.metro.tokyo',  # 東京都
    '.city.',      # 市町村
    '.pref.',      # 都道府県
    'govtech',     # GovTech系
    'e-tokyo',     # 東京都電子自治体
}

# 無効な企業名パターン（タイトルから抽出された無意味なテキスト）
INVALID_COMPANY_NAMES = {
    'この条件から検索',
    '条件から検索',
    '企業名 株式会社',
    '会社名 株式会社',
    '検索結果',
    '一覧',
    'トップページ',
    'ホーム',
    'HOME',
    'TOP',
}

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


def search_duckduckgo(port: int, query: str, max_results: int = 10, scroll_pages: int = 5) -> List[Dict[str, str]]:
    """
    DuckDuckGoで検索して結果を取得（スクロールで追加結果も取得）

    Args:
        port: ブラウザコンテナのポート
        query: 検索クエリ
        max_results: 最大取得件数
        scroll_pages: スクロール回数（追加読み込み回数）

    Returns:
        [{title: str, url: str, snippet: str}, ...]
    """
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

    # 除外ドメイン・URLパターンのフィルタリング
    filtered_results = []
    for r in all_results:
        url = r.get('url', '')
        
        # is_valid_company_url で総合判定
        if not is_valid_company_url(url):
            continue

        filtered_results.append(r)

    return filtered_results[:max_results]


def generate_query_variations(base_query: str, max_variations: int = 10) -> List[str]:
    """
    基本クエリから検索バリエーションを生成

    Args:
        base_query: 基本クエリ（例: "東京 システム開発会社"）
        max_variations: 最大バリエーション数

    Returns:
        クエリのリスト
    """
    variations = [base_query]

    # 地域を抽出
    regions = ['東京', '大阪', '名古屋', '福岡', '横浜', '札幌', '仙台', '神戸', '京都', '広島']
    found_region = None
    for region in regions:
        if region in base_query:
            found_region = region
            break

    # 業種キーワードのバリエーション（拡張）
    it_variations = [
        'システム開発', 'Web制作', 'アプリ開発', 'IT企業', 'ソフトウェア開発',
        'Webサービス', 'SaaS', 'Webシステム', 'DX支援',
        '受託開発', 'SI企業', 'システムインテグレーター', 'Webアプリ開発',
        'モバイルアプリ開発', 'クラウド開発', 'AWS構築', 'インフラ構築',
        'ノーコード開発', 'ローコード開発', 'AI開発', '機械学習',
        'データ分析', 'IoT開発', 'ブロックチェーン',
    ]

    # 製造業バリエーション
    manufacturing_variations = [
        '製造業', 'メーカー', '工場', '金属加工', '精密機器', '電子部品',
        '機械製造', '自動車部品', 'プラスチック成形', '板金加工', '切削加工',
        'NC加工', '金型製作', '試作品', 'OEM', 'ODM',
    ]

    # 不動産バリエーション
    realestate_variations = [
        '不動産会社', '不動産', '賃貸', '売買仲介', '不動産管理',
        'マンション販売', '住宅販売', 'ビル管理', '不動産投資', '土地活用',
        'テナント', 'オフィス仲介', '商業施設', '物件管理',
    ]

    # 建設業バリエーション
    construction_variations = [
        '建設会社', '建築', '工務店', 'ゼネコン', 'リフォーム',
        '施工', '設計事務所', '内装', '外壁', '塗装', '電気工事',
        '設備工事', '土木', 'プラント',
    ]

    # 業種判定と適用
    all_industry_variations = {
        'it': it_variations,
        'manufacturing': manufacturing_variations,
        'realestate': realestate_variations,
        'construction': construction_variations,
    }

    # 基本クエリから業種キーワードを特定して、バリエーションを追加
    matched = False
    for industry, kw_list in all_industry_variations.items():
        for kw in kw_list:
            if kw in base_query:
                # 同じ業種の別表現を追加
                for alt_kw in kw_list:
                    if alt_kw != kw:
                        if found_region:
                            new_query = f"{found_region} {alt_kw}"
                        else:
                            new_query = alt_kw
                        if new_query not in variations:
                            variations.append(new_query)
                matched = True
                break
        if matched:
            break

    # 会社/企業の表現バリエーション
    if '会社' in base_query:
        variations.append(base_query.replace('会社', '企業'))
    if '企業' in base_query:
        variations.append(base_query.replace('企業', '会社'))

    return variations[:max_variations]


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

        # 行政・公共機関ドメイン除外
        if any(gov in domain for gov in GOVERNMENT_DOMAINS):
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
