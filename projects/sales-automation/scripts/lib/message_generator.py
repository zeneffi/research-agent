"""
営業文生成機能

LLM版とテンプレート版を設定で切り替え可能
"""
from typing import Dict, Any, Optional


def generate_sales_message(
    company_info: Dict[str, Any],
    sender_info: Dict[str, str],
    config: Optional[Dict[str, Any]] = None
) -> str:
    """
    企業情報から営業文を生成（200-300文字）
    
    Args:
        company_info: 企業情報
        sender_info: 送信者情報
        config: message_generation設定（use_llm, model等）
    
    Returns:
        営業メッセージ
    """
    # 設定からLLM使用を判断
    msg_config = config or {}
    use_llm = msg_config.get('use_llm', False)
    
    if use_llm:
        return _generate_with_llm(company_info, sender_info, msg_config)
    else:
        return _generate_with_template(company_info, sender_info)


def _generate_with_llm(
    company_info: Dict[str, Any],
    sender_info: Dict[str, str],
    config: Dict[str, Any]
) -> str:
    """LLMで営業文を生成"""
    from .message_generator_llm import generate_sales_message_llm
    
    return generate_sales_message_llm(
        company_info=company_info,
        sender_info=sender_info,
        system_prompt=config.get('system_prompt'),
        company_intro=config.get('company_intro'),
        model=config.get('model', 'gpt-4o-mini')
    )


def _generate_with_template(
    company_info: Dict[str, Any],
    sender_info: Dict[str, str]
) -> str:
    """テンプレートで営業文を生成（従来方式）"""
    company_type = detect_company_type(company_info)
    template = get_message_template(company_type)
    
    # 連絡先を追加
    contact_info = f"""
---
{sender_info.get('company_name', '')}
{sender_info.get('contact_name', '')}
Email: {sender_info.get('email', '')}
TEL: {sender_info.get('phone', '')}
"""

    message = template.format(
        company_name=company_info.get('company_name', '御社'),
        custom_field_1=company_info.get('custom_field_1', ''),
        custom_field_2=company_info.get('custom_field_2', ''),
        custom_field_3=company_info.get('custom_field_3', ''),
        industry=company_info.get('business', ''),
        sender_company=sender_info.get('company_name', ''),
        sender_name=sender_info.get('contact_name', '')
    )
    
    return message + contact_info


def detect_company_type(company_info: Dict[str, Any]) -> str:
    """企業タイプ推定: 'startup'|'it_company'|'manufacturing'|'general'"""
    custom_1 = company_info.get('custom_field_1', '')
    custom_3 = company_info.get('custom_field_3', '')

    tech_keywords = [
        'React', 'Python', 'JavaScript', 'TypeScript',
        'Java', 'PHP', 'Ruby', 'Go', 'Node.js',
        'Vue', 'Angular', 'Django', 'Flask', 'Rails',
        'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes'
    ]
    if any(tech in custom_1 for tech in tech_keywords):
        return 'it_company'

    startup_keywords = [
        'シリーズ', 'ラウンド', '資金調達',
        'Series', 'Seed', 'プレシリーズ',
        '億円', '調達'
    ]
    if any(kw in custom_1 for kw in startup_keywords):
        return 'startup'

    if 'ISO' in custom_3:
        return 'manufacturing'

    return 'general'


def get_message_template(company_type: str) -> str:
    """企業タイプ別のテンプレート取得"""
    TEMPLATES = {
        'startup': """突然のご連絡失礼いたします。

{custom_field_1}で{custom_field_2}の調達おめでとうございます。
事業拡大フェーズでのリソース不足をサポートさせていただけないでしょうか。

弊社は{industry}分野での実績が豊富で、貴社の成長に貢献できると考えております。
まずはお気軽にお話しできれば幸いです。

何卒ご検討のほどよろしくお願いいたします。""",

        'it_company': """突然のご連絡失礼いたします。

貴社が{custom_field_1}を活用されていることを拝見しました。
弊社も同技術での実績が豊富で、{industry}分野での貴社の事業に技術面でお力添えできればと考えております。

具体的な支援の可能性について、一度お話しさせていただけないでしょうか。

何卒ご検討のほどよろしくお願いいたします。""",

        'manufacturing': """突然のご連絡失礼いたします。

{industry}分野で{custom_field_1}を手がける貴社に、弊社のサービスをご提案させていただきたく存じます。
{custom_field_3}を取得されている貴社の品質へのこだわりに、弊社も貢献できればと考えております。

まずはお気軽にお話しできれば幸いです。

何卒ご検討のほどよろしくお願いいたします。""",

        'general': """突然のご連絡失礼いたします。

{company_name}様の事業内容を拝見し、弊社のサービスをご提案させていただきたく存じます。
貴社のビジネス成長をサポートできればと考えております。

まずはお気軽にお話しできれば幸いです。

何卒ご検討のほどよろしくお願いいたします。"""
    }

    return TEMPLATES.get(company_type, TEMPLATES['general'])
