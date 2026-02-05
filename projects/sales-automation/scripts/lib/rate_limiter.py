"""
レート制限管理機能

参考元1: output.py の generate_json_output() - JSON読み書きパターン
参考元2: auto_contact.py 行199-203 - 待機処理
"""
import json
import os
import time
from datetime import datetime, date
from typing import Dict, Any, Tuple


class RateLimiter:
    """
    送信レート制限管理クラス

    - 1日あたりの送信上限（デフォルト100件）
    - 送信間隔（デフォルト180秒=3分）
    - 送信ログ記録（send_log.json）
    """

    def __init__(self, log_path: str, daily_limit: int = 100,
                 interval_seconds: int = 180):
        """
        Args:
            log_path: send_log.json のパス
            daily_limit: 1日の送信上限（デフォルト100件）
            interval_seconds: 送信間隔（デフォルト180秒=3分）
        """
        self.log_path = log_path
        self.daily_limit = daily_limit
        self.interval_seconds = interval_seconds
        self._load_or_create_log()

    def _load_or_create_log(self):
        """
        ログファイルを読み込み、または新規作成

        移植元: output.py generate_json_output() のパターン
        """
        if os.path.exists(self.log_path) and os.path.getsize(self.log_path) > 0:
            try:
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    self.log_data = json.load(f)
            except json.JSONDecodeError:
                # ファイルが壊れている場合は新規作成
                self.log_data = self._create_empty_log()
        else:
            self.log_data = self._create_empty_log()

    def _create_empty_log(self):
        """空のログデータを作成"""
        return {
            "summary": {
                "total": 0,
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "started_at": None,
                "completed_at": None
            },
            "entries": []
        }

    def can_send(self) -> Tuple[bool, str]:
        """
        送信可能かチェック（日次上限・間隔チェック）

        Returns:
            (可否, 理由メッセージ)
        """
        # 日次上限チェック
        today = date.today()
        today_count = sum(
            1 for e in self.log_data['entries']
            if e.get('timestamp') and
            date.fromisoformat(e['timestamp'][:10]) == today and
            e.get('status') == 'success'  # 成功した送信のみカウント
        )

        if today_count >= self.daily_limit:
            return False, f"日次上限到達 ({today_count}/{self.daily_limit})"

        # 送信間隔チェック
        if self.log_data['entries']:
            last_entry = None
            # 最後の成功した送信を検索
            for e in reversed(self.log_data['entries']):
                if e.get('status') == 'success' and e.get('timestamp'):
                    last_entry = e
                    break

            if last_entry:
                try:
                    last_timestamp = datetime.fromisoformat(last_entry['timestamp'])
                    elapsed = (datetime.now() - last_timestamp).total_seconds()

                    if elapsed < self.interval_seconds:
                        wait_time = self.interval_seconds - elapsed
                        return False, f"送信間隔不足 (あと{wait_time:.0f}秒)"
                except:
                    pass  # タイムスタンプのパースに失敗した場合は継続

        return True, "OK"

    def wait_if_needed(self):
        """
        必要に応じて待機（前回送信から3分経過まで）

        移植元: auto_contact.py 行199-203
        """
        if not self.log_data['entries']:
            return

        # 最後の成功した送信を検索
        last_entry = None
        for e in reversed(self.log_data['entries']):
            if e.get('status') == 'success' and e.get('timestamp'):
                last_entry = e
                break

        if not last_entry:
            return

        try:
            last_timestamp = datetime.fromisoformat(last_entry['timestamp'])
            elapsed = (datetime.now() - last_timestamp).total_seconds()

            if elapsed < self.interval_seconds:
                wait_time = self.interval_seconds - elapsed
                print(f"  {wait_time:.0f}秒待機中...")
                time.sleep(wait_time)
        except:
            pass  # タイムスタンプのパースに失敗した場合はスキップ

    def log_send(self, entry: Dict[str, Any]):
        """
        送信ログを記録（send_log.jsonに追記）

        移植元: output.py generate_json_output() のパターン

        Args:
            entry: ログエントリ
                {
                    'company_name': str,
                    'url': str,
                    'status': 'success'|'failed'|'skipped',
                    'timestamp': str (ISO 8601),
                    'message_preview': str,
                    'form_fields_detected': list,
                    'error': str,
                    'screenshot': str
                }
        """
        self.log_data['entries'].append(entry)

        # サマリー更新
        status = entry.get('status', 'unknown')
        if status == 'success':
            self.log_data['summary']['success'] += 1
        elif status == 'failed':
            self.log_data['summary']['failed'] += 1
        elif status == 'skipped':
            self.log_data['summary']['skipped'] += 1

        self.log_data['summary']['total'] = len(self.log_data['entries'])

        # started_at の記録
        if self.log_data['summary']['started_at'] is None:
            self.log_data['summary']['started_at'] = entry.get('timestamp')

        # completed_at は常に更新
        self.log_data['summary']['completed_at'] = entry.get('timestamp')

        # output.py 行28-29のJSON書き込みパターンを流用
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, ensure_ascii=False, indent=2)

    def get_summary(self) -> Dict[str, Any]:
        """
        サマリー情報を取得

        Returns:
            {'total': int, 'success': int, 'failed': int, 'skipped': int}
        """
        return self.log_data['summary']
