"""
重複送信チェック機能

送信済みドメインをファイルで管理し、同じ企業への重複送信を防ぐ。
"""
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Set, Optional


# デフォルトのファイルパス
DEFAULT_SENT_DOMAINS_FILE = Path(__file__).parent.parent.parent / "data" / "sent_domains.txt"


def get_domain_from_url(url: str) -> Optional[str]:
    """
    URLからドメインを抽出

    Args:
        url: WebサイトURL

    Returns:
        ドメイン（例: example.com）
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        # www.を除去
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.lower()
    except Exception:
        return None


def load_sent_domains(filepath: Path = DEFAULT_SENT_DOMAINS_FILE) -> Set[str]:
    """
    送信済みドメイン一覧を読み込み

    Args:
        filepath: 送信済みドメインファイルのパス

    Returns:
        送信済みドメインのセット
    """
    domains = set()
    if not filepath.exists():
        return domains

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # コメント行と空行をスキップ
            if line and not line.startswith('#'):
                domains.add(line.lower())

    return domains


def save_sent_domain(domain: str, filepath: Path = DEFAULT_SENT_DOMAINS_FILE) -> None:
    """
    送信済みドメインをファイルに追加

    Args:
        domain: 追加するドメイン
        filepath: 送信済みドメインファイルのパス
    """
    # ディレクトリがなければ作成
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # ファイルがなければヘッダー付きで作成
    if not filepath.exists():
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 送信済みドメイン一覧\n")
            f.write("# 新規利用時はこのファイルを空にしてください\n")
            f.write("\n")

    # ドメインを追記
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(f"{domain.lower()}\n")


def is_already_sent(url: str, filepath: Path = DEFAULT_SENT_DOMAINS_FILE) -> bool:
    """
    指定URLのドメインが送信済みかチェック

    Args:
        url: チェックするURL
        filepath: 送信済みドメインファイルのパス

    Returns:
        True: 送信済み、False: 未送信
    """
    domain = get_domain_from_url(url)
    if not domain:
        return False

    sent_domains = load_sent_domains(filepath)
    return domain in sent_domains


def mark_as_sent(url: str, filepath: Path = DEFAULT_SENT_DOMAINS_FILE) -> None:
    """
    指定URLのドメインを送信済みとして記録

    Args:
        url: 送信済みURL
        filepath: 送信済みドメインファイルのパス
    """
    domain = get_domain_from_url(url)
    if domain:
        # 既に記録済みでなければ追加
        sent_domains = load_sent_domains(filepath)
        if domain not in sent_domains:
            save_sent_domain(domain, filepath)


def filter_unsent_companies(companies: list, url_key: str = 'url',
                            filepath: Path = DEFAULT_SENT_DOMAINS_FILE) -> list:
    """
    企業リストから未送信の企業のみをフィルタリング

    Args:
        companies: 企業情報のリスト
        url_key: URLが格納されているキー名
        filepath: 送信済みドメインファイルのパス

    Returns:
        未送信企業のリスト
    """
    sent_domains = load_sent_domains(filepath)
    unsent = []

    for company in companies:
        url = company.get(url_key)
        if not url:
            continue

        domain = get_domain_from_url(url)
        if domain and domain not in sent_domains:
            unsent.append(company)

    return unsent


def get_stats(filepath: Path = DEFAULT_SENT_DOMAINS_FILE) -> dict:
    """
    送信統計を取得

    Args:
        filepath: 送信済みドメインファイルのパス

    Returns:
        {'total_sent': int}
    """
    sent_domains = load_sent_domains(filepath)
    return {
        'total_sent': len(sent_domains)
    }
