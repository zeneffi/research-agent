"""
企業情報抽出機能
"""
import re
import time
from typing import Optional, Dict, Any
from .browser import browser_navigate, browser_evaluate


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

    # 基本情報抽出スクリプト
    script = f"""(function() {{
        const body = document.body.innerText;
        const title = document.title;

        // 企業名抽出（複数パターン）
        let companyName = '';
        const companyPatterns = [
            /(?:会社名|社名)[：:・\\s]*([^\\n]+)/,
            /(?:株式会社|有限会社|合同会社)([^\\n、,]+)/,
        ];
        for (const pattern of companyPatterns) {{
            const match = body.match(pattern);
            if (match) {{
                companyName = match[1].trim();
                break;
            }}
        }}

        // タイトルからフォールバック
        if (!companyName) {{
            const titleMatch = title.match(/(.+?)(?:｜|\\||のホームページ|公式サイト|株式会社|有限会社)/);
            if (titleMatch) companyName = titleMatch[1].trim();
        }}

        // 所在地抽出
        let location = '';
        const locationPatterns = [
            /(?:本社|所在地|住所)[：:・\\s]*([^\\n]+)/,
            /(?:〒|&#12306;)\\s*[0-9-]+\\s*([^\\n]+)/,
        ];
        for (const pattern of locationPatterns) {{
            const match = body.match(pattern);
            if (match) {{
                location = match[1].trim().substring(0, 100);
                break;
            }}
        }}

        // 事業内容抽出
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

        // カスタム項目抽出（業種別）
        let custom1 = '', custom2 = '', custom3 = '';

        const searchContext = '{search_context}';

        if (searchContext === 'IT') {{
            // IT: 技術スタック
            const techMatch = body.match(/(?:使用技術|技術スタック|Tech Stack)[：:・\\s]*([^\\n]+)/);
            if (techMatch) custom1 = techMatch[1].trim().substring(0, 200);

            // エンジニア数
            const engMatch = body.match(/エンジニア[：:・\\s]*(\\d+)[名人]/);
            if (engMatch) custom2 = engMatch[1] + '名';

            // 開発実績
            const devMatch = body.match(/(?:開発実績|実績)[：:・\\s]*([^\\n]+)/);
            if (devMatch) custom3 = devMatch[1].trim().substring(0, 200);

        }} else if (searchContext === 'Manufacturing') {{
            // 製造業: 主要製品
            const prodMatch = body.match(/(?:主要製品|製品)[：:・\\s]*([^\\n]+)/);
            if (prodMatch) custom1 = prodMatch[1].trim().substring(0, 200);

            // 工場所在地
            const factMatch = body.match(/(?:工場|生産拠点)[：:・\\s]*([^\\n]+)/);
            if (factMatch) custom2 = factMatch[1].trim().substring(0, 100);

            // ISO認証
            const isoMatch = body.match(/(ISO\\s*\\d+)/);
            if (isoMatch) custom3 = isoMatch[1];

        }} else if (searchContext === 'Startup') {{
            // スタートアップ: 調達ラウンド
            const roundPatterns = ['プレシリーズA', 'シリーズA', 'シリーズB', 'シリーズC', 'シード'];
            for (const round of roundPatterns) {{
                if (body.includes(round)) {{
                    custom1 = round;
                    break;
                }}
            }}

            // 調達額
            const amountMatch = body.match(/(\\d+(?:\\.\\d+)?)[\\s]*億円[のを]*(?:資金)?調達/);
            if (amountMatch) custom2 = amountMatch[1] + '億円';

            // 調達日
            const dateMatch = body.match(/(\\d{{4}})年(\\d{{1,2}})月/);
            if (dateMatch) custom3 = dateMatch[0];
        }}

        return JSON.stringify({{
            company_name: companyName || title.substring(0, 50),
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
        return json.loads(result)
    except:
        return None


def extract_custom_fields(page_text: str, search_context: str) -> Dict[str, str]:
    """
    カスタム項目を業種に応じて動的に抽出

    Args:
        page_text: ページテキスト
        search_context: 業種コンテキスト

    Returns:
        {custom_field_1: str, custom_field_2: str, custom_field_3: str}
    """
    custom_fields = {
        'custom_field_1': '',
        'custom_field_2': '',
        'custom_field_3': ''
    }

    if search_context == 'IT':
        # 技術スタック
        tech_match = re.search(r'(?:使用技術|技術スタック|Tech Stack)[：:・\s]*([^\n]+)', page_text)
        if tech_match:
            custom_fields['custom_field_1'] = tech_match.group(1).strip()[:200]

        # エンジニア数
        eng_match = re.search(r'エンジニア[：:・\s]*(\d+)[名人]', page_text)
        if eng_match:
            custom_fields['custom_field_2'] = eng_match.group(1) + '名'

        # 開発実績
        dev_match = re.search(r'(?:開発実績|実績)[：:・\s]*([^\n]+)', page_text)
        if dev_match:
            custom_fields['custom_field_3'] = dev_match.group(1).strip()[:200]

    elif search_context == 'Manufacturing':
        # 主要製品
        prod_match = re.search(r'(?:主要製品|製品)[：:・\s]*([^\n]+)', page_text)
        if prod_match:
            custom_fields['custom_field_1'] = prod_match.group(1).strip()[:200]

        # 工場所在地
        fact_match = re.search(r'(?:工場|生産拠点)[：:・\s]*([^\n]+)', page_text)
        if fact_match:
            custom_fields['custom_field_2'] = fact_match.group(1).strip()[:100]

        # ISO認証
        iso_match = re.search(r'(ISO\s*\d+)', page_text)
        if iso_match:
            custom_fields['custom_field_3'] = iso_match.group(1)

    elif search_context == 'Startup':
        # 調達ラウンド
        round_patterns = ['プレシリーズA', 'シリーズA', 'シリーズB', 'シリーズC', 'シード']
        for round_name in round_patterns:
            if round_name in page_text:
                custom_fields['custom_field_1'] = round_name
                break

        # 調達額
        amount_match = re.search(r'(\d+(?:\.\d+)?)\s*億円[のを]*(?:資金)?調達', page_text)
        if amount_match:
            custom_fields['custom_field_2'] = amount_match.group(1) + '億円'

        # 調達日
        date_match = re.search(r'(\d{4})年(\d{1,2})月', page_text)
        if date_match:
            custom_fields['custom_field_3'] = date_match.group(0)

    return custom_fields
