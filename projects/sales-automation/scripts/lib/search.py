"""
DuckDuckGo検索機能
"""
import re
import time
from urllib.parse import quote, urlparse
from typing import List, Dict, Optional
from .browser import browser_navigate, browser_evaluate


# 除外ドメイン（検索結果から除外するサイト）
SKIP_DOMAINS = [
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
]


def search_duckduckgo(port: int, query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """
    DuckDuckGoで検索して結果を取得

    Args:
        port: ブラウザコンテナのポート
        query: 検索クエリ
        max_results: 最大取得件数

    Returns:
        [{title: str, url: str, snippet: str}, ...]
    """
    encoded_query = quote(query)
    url = f"https://duckduckgo.com/?q={encoded_query}"

    if not browser_navigate(port, url):
        return []

    # ページロード待機
    time.sleep(3)

    # 検索結果を抽出するJavaScript
    script = """(function() {
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

    result = browser_evaluate(port, script)
    if not result:
        return []

    try:
        import json
        all_results = json.loads(result)

        # 除外ドメインのフィルタリング
        filtered_results = []
        for r in all_results:
            url = r.get('url', '')
            domain = urlparse(url).netloc.lower()

            # 除外ドメインチェック
            if any(skip in domain for skip in SKIP_DOMAINS):
                continue

            # 日本語ドメイン優先（.co.jp, .jp）
            filtered_results.append(r)

        return filtered_results[:max_results]
    except:
        return []


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

        # 除外ドメイン
        if any(skip in domain for skip in SKIP_DOMAINS):
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
