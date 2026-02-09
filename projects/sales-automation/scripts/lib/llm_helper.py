"""
LLMを使った業種バリエーション生成
"""
import os
import json
from typing import List
from urllib.request import Request, urlopen
from urllib.error import URLError


def generate_industry_variations(query: str, max_variations: int = 10) -> List[str]:
    """
    LLM（GPT-4o-mini）を使って業種のバリエーションを生成
    
    Args:
        query: 基本クエリ（例: "東京 飲食店"）
        max_variations: 最大バリエーション数
    
    Returns:
        クエリのリスト
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        # APIキーがない場合はフォールバック
        return [query]
    
    # 地域を抽出
    regions = ['東京', '大阪', '名古屋', '福岡', '横浜', '札幌', '仙台', '神戸', '京都', '広島']
    found_region = None
    for region in regions:
        if region in query:
            found_region = region
            break
    
    # 業種キーワードを抽出
    industry_keyword = query.replace(found_region or '', '').strip() if found_region else query
    
    prompt = f"""以下の業種に関連する検索キーワードのバリエーションを{max_variations}個生成してください。

業種: {industry_keyword}
地域: {found_region or '指定なし'}

要件:
- 同じ業種の別の言い方、関連する業種を含める
- 検索で企業が見つかりやすいキーワードにする
- 日本語で出力
- 1行に1キーワード
- 地域は含めない（後で追加する）

例（IT企業の場合）:
システム開発
Web制作
アプリ開発
ソフトウェア開発
"""

    try:
        data = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500
        }).encode('utf-8')
        
        req = Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        
        with urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result['choices'][0]['message']['content']
            
            # レスポンスをパース
            lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
            # 番号付きの場合は番号を除去
            variations = []
            for line in lines:
                # "1. キーワード" や "- キーワード" の形式に対応
                if line[0].isdigit():
                    line = line.split('.', 1)[-1].strip()
                elif line.startswith('-'):
                    line = line[1:].strip()
                if line and len(line) > 1:
                    variations.append(line)
            
            # 地域を追加
            if found_region:
                variations = [f"{found_region} {v}" for v in variations]
            
            # 元のクエリを先頭に
            if query not in variations:
                variations.insert(0, query)
            
            return variations[:max_variations]
            
    except (URLError, json.JSONDecodeError, KeyError, Exception) as e:
        print(f"[LLM] Error: {e}")
        return [query]


if __name__ == "__main__":
    # テスト
    import sys
    query = sys.argv[1] if len(sys.argv) > 1 else "東京 飲食店"
    print(f"Query: {query}")
    print("-" * 40)
    variations = generate_industry_variations(query)
    for i, v in enumerate(variations, 1):
        print(f"{i}. {v}")
