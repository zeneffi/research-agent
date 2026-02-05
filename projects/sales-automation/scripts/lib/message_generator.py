"""
営業文生成機能

extractor.py の条件分岐パターン + auto_contact.py のテンプレート機構を組み合わせ
"""
from typing import Dict, Any


def generate_sales_message(company_info: Dict[str, Any],
                          sender_info: Dict[str, str]) -> str:
    """
    企業情報から営業文を生成（200-300文字）

    移植元1: extractor.py extract_custom_fields() の条件分岐を逆向きで使用
    移植元2: auto_contact.py のテンプレート機構（str.format()）

    パターン判定ロジック（extractor.pyから流用）:
    1. スタートアップ: custom_field_1に「シリーズ」「ラウンド」「資金調達」
    2. IT企業: custom_field_1に技術名（React, Python, JavaScript等）
    3. 製造業: custom_field_3に「ISO」
    4. 汎用: その他

    Args:
        company_info: 企業情報
        sender_info: 送信者情報

    Returns:
        営業メッセージ（200-300文字）
    """
    company_type = detect_company_type(company_info)
    template = get_message_template(company_type)

    # auto_contact.py 行83の.format()パターンをそのまま使用
    return template.format(
        company_name=company_info.get('company_name', '御社'),
        custom_field_1=company_info.get('custom_field_1', ''),
        custom_field_2=company_info.get('custom_field_2', ''),
        custom_field_3=company_info.get('custom_field_3', ''),
        industry=company_info.get('business', ''),
        sender_company=sender_info.get('company_name', ''),
        sender_name=sender_info.get('contact_name', '')
    )


def detect_company_type(company_info: Dict[str, Any]) -> str:
    """
    企業タイプ推定: 'startup'|'it_company'|'manufacturing'|'general'

    移植元: extractor.py 行161-228 の条件分岐を逆向きで使用

    Args:
        company_info: 企業情報

    Returns:
        企業タイプ
    """
    custom_1 = company_info.get('custom_field_1', '')
    custom_3 = company_info.get('custom_field_3', '')

    # IT: extractor.py 行178-192
    tech_keywords = [
        'React', 'Python', 'JavaScript', 'TypeScript',
        'Java', 'PHP', 'Ruby', 'Go', 'Node.js',
        'Vue', 'Angular', 'Django', 'Flask', 'Rails',
        'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes'
    ]
    if any(tech in custom_1 for tech in tech_keywords):
        return 'it_company'

    # Startup: extractor.py 行210-226
    startup_keywords = [
        'シリーズ', 'ラウンド', '資金調達',
        'Series', 'Seed', 'プレシリーズ',
        '億円', '調達'
    ]
    if any(kw in custom_1 for kw in startup_keywords):
        return 'startup'

    # Manufacturing: extractor.py 行194-208
    if 'ISO' in custom_3:
        return 'manufacturing'

    return 'general'


def get_message_template(company_type: str) -> str:
    """
    企業タイプ別のテンプレート取得

    移植元: auto_contact.py 行152-171 のテンプレート構造

    Args:
        company_type: 企業タイプ

    Returns:
        メッセージテンプレート
    """
    TEMPLATES = {
        'startup': """
突然のご連絡失礼いたします。

{custom_field_1}で{custom_field_2}の調達おめでとうございます。
事業拡大フェーズでのリソース不足をサポートさせていただけないでしょうか。

弊社は{industry}分野での実績が豊富で、貴社の成長に貢献できると考えております。
まずはお気軽にお話しできれば幸いです。

何卒ご検討のほどよろしくお願いいたします。
""".strip(),

        'it_company': """
突然のご連絡失礼いたします。

貴社が{custom_field_1}を活用されていることを拝見しました。
弊社も同技術での実績が豊富で、{industry}分野での貴社の事業に技術面でお力添えできればと考えております。

具体的な支援の可能性について、一度お話しさせていただけないでしょうか。

何卒ご検討のほどよろしくお願いいたします。
""".strip(),

        'manufacturing': """
突然のご連絡失礼いたします。

{industry}分野で{custom_field_1}を手がける貴社に、弊社のサービスをご提案させていただきたく存じます。
{custom_field_3}を取得されている貴社の品質へのこだわりに、弊社も貢献できればと考えております。

まずはお気軽にお話しできれば幸いです。

何卒ご検討のほどよろしくお願いいたします。
""".strip(),

        'general': """
突然のご連絡失礼いたします。

{company_name}様の事業内容を拝見し、弊社のサービスをご提案させていただきたく存じます。
貴社のビジネス成長をサポートできればと考えております。

まずはお気軽にお話しできれば幸いです。

何卒ご検討のほどよろしくお願いいたします。
""".strip()
    }

    return TEMPLATES.get(company_type, TEMPLATES['general'])
