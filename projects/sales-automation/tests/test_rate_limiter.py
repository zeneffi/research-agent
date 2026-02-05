"""
rate_limiter.py のテスト
"""
import os
import json
import tempfile
from datetime import datetime
from scripts.lib.rate_limiter import RateLimiter


def test_rate_limiter_init():
    """初期化のテスト"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        log_path = f.name

    try:
        limiter = RateLimiter(log_path, daily_limit=10, interval_seconds=60)
        assert limiter.daily_limit == 10
        assert limiter.interval_seconds == 60
        assert limiter.log_data['summary']['total'] == 0
    finally:
        if os.path.exists(log_path):
            os.unlink(log_path)


def test_can_send_empty():
    """空の状態での送信可否チェック"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        log_path = f.name

    try:
        limiter = RateLimiter(log_path, daily_limit=10, interval_seconds=60)
        can_send, reason = limiter.can_send()
        assert can_send is True
        assert reason == "OK"
    finally:
        if os.path.exists(log_path):
            os.unlink(log_path)


def test_log_send():
    """ログ記録のテスト"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        log_path = f.name

    try:
        limiter = RateLimiter(log_path)

        entry = {
            'company_name': 'テスト企業',
            'url': 'https://example.com/contact',
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'message_preview': 'テストメッセージ...',
            'form_fields_detected': ['name', 'email', 'message'],
            'error': None,
            'screenshot': None
        }

        limiter.log_send(entry)

        assert limiter.log_data['summary']['total'] == 1
        assert limiter.log_data['summary']['success'] == 1
        assert len(limiter.log_data['entries']) == 1

        # ファイルに保存されているか確認
        with open(log_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            assert saved_data['summary']['total'] == 1

    finally:
        if os.path.exists(log_path):
            os.unlink(log_path)


def test_get_summary():
    """サマリー取得のテスト"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        log_path = f.name

    try:
        limiter = RateLimiter(log_path)

        # 複数エントリを追加
        for status in ['success', 'failed', 'skipped']:
            entry = {
                'company_name': f'テスト企業_{status}',
                'url': 'https://example.com/contact',
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'message_preview': 'テストメッセージ...',
                'form_fields_detected': [],
                'error': None,
                'screenshot': None
            }
            limiter.log_send(entry)

        summary = limiter.get_summary()
        assert summary['total'] == 3
        assert summary['success'] == 1
        assert summary['failed'] == 1
        assert summary['skipped'] == 1

    finally:
        if os.path.exists(log_path):
            os.unlink(log_path)
