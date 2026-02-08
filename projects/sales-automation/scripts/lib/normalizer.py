"""
データ正規化機能
"""
import re
from typing import List, Dict, Any


def normalize_company_name(name: str) -> str:
    """
    企業名を正規化（重複排除用）

    Args:
        name: 元の企業名

    Returns:
        正規化された企業名
    """
    normalized = name

    # 区切り文字以降を削除（「株式会社ABC｜サービス紹介」→「株式会社ABC」）
    for sep in ['｜', '|', ' - ', '－', '―', '–']:
        if sep in normalized:
            normalized = normalized.split(sep)[0]

    # 括弧内の補足を削除（「株式会社LIG(リグ)」→「株式会社LIG」）
    normalized = re.sub(r'[（(][^）)]*[）)]', '', normalized)

    # 法人格を除去
    corp_patterns = [
        r'株式会社\s*',
        r'有限会社\s*',
        r'合同会社\s*',
        r'合資会社\s*',
        r'一般社団法人\s*',
        r'公益財団法人\s*',
        r'\(株\)',
        r'（株）',
    ]
    for pattern in corp_patterns:
        normalized = re.sub(pattern, '', normalized)

    # 全角英数→半角
    normalized = normalized.translate(str.maketrans(
        'ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９',
        'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    ))

    # 複数の空白を1つに
    normalized = re.sub(r'\s+', ' ', normalized)

    # 小文字化（英語企業名の重複排除用）
    normalized = normalized.lower()

    # 前後の空白除去
    normalized = normalized.strip()

    return normalized


def deduplicate_companies(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    企業リストから重複を除去

    Args:
        companies: 企業情報のリスト

    Returns:
        重複を除去した企業リスト
    """
    seen = set()
    unique_companies = []

    for company in companies:
        # 正規化された企業名でチェック
        normalized_name = normalize_company_name(company.get('company_name', ''))

        # URLでもチェック（企業名が取れない場合のフォールバック）
        url = company.get('company_url', '')

        # ユニークキー
        key = normalized_name if normalized_name else url

        if key and key not in seen:
            seen.add(key)
            unique_companies.append(company)

    return unique_companies


def clean_text(text: str, max_length: int = 200) -> str:
    """
    テキストをクリーニング

    Args:
        text: 元のテキスト
        max_length: 最大文字数

    Returns:
        クリーニングされたテキスト
    """
    if not text:
        return ''

    # 改行・タブを空白に変換
    cleaned = re.sub(r'[\n\r\t]+', ' ', text)

    # 複数の空白を1つに
    cleaned = re.sub(r'\s+', ' ', cleaned)

    # 前後の空白除去
    cleaned = cleaned.strip()

    # 最大文字数で切る
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + '...'

    return cleaned


def validate_company_data(company: Dict[str, Any]) -> bool:
    """
    企業データが有効かチェック

    Args:
        company: 企業情報

    Returns:
        True: 有効, False: 無効
    """
    # 必須フィールド
    required_fields = ['company_name', 'company_url']

    for field in required_fields:
        value = company.get(field, '')
        if not value or value.strip() == '':
            return False

    # URLの形式チェック
    url = company.get('company_url', '')
    if not url.startswith('http'):
        return False

    return True
