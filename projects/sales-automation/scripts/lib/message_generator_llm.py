"""
LLMを使った営業文生成

企業情報を元に、動的にパーソナライズされた営業文を生成
"""
import os
import logging
from typing import Dict, Any, Optional

from openai import OpenAI, APIError, RateLimitError, APIConnectionError

logger = logging.getLogger(__name__)

# OpenAIは遅延インポート（インストールされていない環境対応）
_openai_client = None


class OpenAIKeyNotFoundError(Exception):
    """OpenAI APIキーが設定されていない場合のエラー"""
    pass


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise OpenAIKeyNotFoundError(
                "OPENAI_API_KEY 環境変数が設定されていません。\n"
                "export OPENAI_API_KEY='sk-...' を実行してください。"
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


# デフォルトのシステムプロンプト
DEFAULT_SYSTEM_PROMPT = """あなたは営業メール文を作成するアシスタントです。
以下の提案内容と文体で、300-400文字程度のDMを作成してください。

【提案内容：案件紹介パートナープログラム】
- 貴社のリソース不足や専門外で断っていた案件を、弊社に紹介するだけで収益化
- 還元率は業界最高水準（例：500万円の案件なら150万円還元）
- 商談同席不要、メールで繋ぐだけでOK

【弊社の強み】
- 認証・決済・AI連携などの「標準モジュール」を保有し、開発原価が安い
- 浮いた原価分を高額な紹介料としてパートナーに還元
- 全案件に役員クラスがPMとして入るため、品質トラブルがない

【文体ルール】
1. 「初めてご連絡いたします。ゼネフィ合同会社の藤崎と申します。」で始める
2. 相手企業の特徴に触れて共感を示す（1-2文）
3. パートナープログラムを簡潔に紹介
4. 「一度オンラインで軽く情報交換させていただけますと幸いです」で締める
5. 押し売り感を出さない、相談ベースのトーン
6. 最後に署名（会社名、氏名）
"""

# デフォルトの会社紹介
DEFAULT_COMPANY_INTRO = """ゼネフィ合同会社はシステム開発会社です。
「標準モジュール」の活用により、開発リソース不足や機会損失といった課題を解決します。
高額還元パートナー制度（500万円の案件なら150万円還元）と役員PMによる品質保証が強みです。"""


def generate_sales_message_llm(
    company_info: Dict[str, Any],
    sender_info: Dict[str, str],
    system_prompt: Optional[str] = None,
    company_intro: Optional[str] = None,
    model: str = "gpt-4o-mini"
) -> str:
    """
    LLMで営業文を生成（200-300文字）
    
    Args:
        company_info: 企業情報（company_name, business, custom_field_1-3など）
        sender_info: 送信者情報（company_name, contact_name, email, phone）
        system_prompt: システムプロンプト（なければデフォルト使用）
        company_intro: 自社紹介文（なければデフォルト使用）
        model: 使用するモデル（デフォルト: gpt-4o-mini）
    
    Returns:
        生成された営業文
    
    Raises:
        OpenAIKeyNotFoundError: APIキーが設定されていない場合
    """
    client = _get_openai_client()
    
    # 企業情報を整理
    company_name = company_info.get('company_name', '御社')
    business = company_info.get('business', '')
    custom_1 = company_info.get('custom_field_1', '')
    custom_2 = company_info.get('custom_field_2', '')
    custom_3 = company_info.get('custom_field_3', '')
    website = company_info.get('company_url', '')
    
    # 送信者情報
    sender_company = sender_info.get('company_name', '')
    sender_name = sender_info.get('contact_name', '')
    sender_email = sender_info.get('email', '')
    sender_phone = sender_info.get('phone', '')
    
    # プロンプト（Noneの場合のみデフォルト使用、空文字は許容）
    sys_prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
    intro = company_intro if company_intro is not None else DEFAULT_COMPANY_INTRO

    user_prompt = f"""以下の企業に送る営業文を作成してください。

【送信先企業】
- 会社名: {company_name}
- 事業内容: {business}
- 特徴1: {custom_1}
- 特徴2: {custom_2}
- 特徴3: {custom_3}
- URL: {website}

【送信者情報】
- 会社名: {sender_company}
- 担当者: {sender_name}
- メール: {sender_email}
- 電話: {sender_phone}

【弊社について】
{intro}

営業文を作成してください（本文のみ、件名は不要）：
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except RateLimitError as e:
        logger.error(f"OpenAI APIレート制限エラー: {e}")
        raise
    except APIConnectionError as e:
        logger.error(f"OpenAI API接続エラー: {e}")
        raise
    except APIError as e:
        logger.error(f"OpenAI APIエラー: {e}")
        raise


def estimate_cost(num_companies: int) -> dict:
    """
    コスト見積もり
    
    gpt-4o-mini: 入力$0.15/1M, 出力$0.6/1M
    1件あたり約1000トークン入力、300トークン出力と仮定
    """
    input_tokens = num_companies * 1000
    output_tokens = num_companies * 300
    
    input_cost = (input_tokens / 1_000_000) * 0.15
    output_cost = (output_tokens / 1_000_000) * 0.6
    total_cost = input_cost + output_cost
    
    return {
        "num_companies": num_companies,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(total_cost, 4),
        "cost_jpy": round(total_cost * 150, 2)  # 1USD=150JPY想定
    }


if __name__ == "__main__":
    # テスト
    print("=== コスト見積もり ===")
    for n in [10, 50, 100]:
        est = estimate_cost(n)
        print(f"{n}社: ${est['cost_usd']} (約{est['cost_jpy']}円)")
    
    print("\n=== サンプル生成（API呼び出しなし） ===")
    print("OPENAI_API_KEY を設定して実行してください")
