"""
ブラウザ操作関数
funding_collector から流用
"""
import json
import subprocess
import re
import os
from pathlib import Path
from typing import Optional, List
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


def get_container_ports() -> List[int]:
    """起動中のコンテナのAPIポートを取得"""
    # docker-compose.yaml のディレクトリを特定
    # Go up from lib -> scripts -> sales-automation -> projects -> research-agent
    project_root = Path(__file__).resolve().parents[4]
    docker_dir = project_root / "docker"

    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "{{.Name}}\t{{.Ports}}"],
        capture_output=True,
        text=True,
        cwd=docker_dir
    )

    ports = []
    for line in result.stdout.strip().split("\n"):
        if "browser" in line and "3000" in line:
            match = re.search(r"0\.0\.0\.0:(\d+)->3000", line)
            if match:
                ports.append(int(match.group(1)))

    return sorted(ports)


def _browser_post(port: int, path: str, payload: dict, timeout: int = 30) -> Optional[dict]:
    try:
        api_url = f"http://localhost:{port}{path}"
        data = json.dumps(payload).encode('utf-8')
        req = Request(api_url, data=data, headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8'))
    except (URLError, HTTPError, json.JSONDecodeError, Exception):
        return None


def _browser_new_tab(port: int, url: str = 'about:blank', timeout: int = 30) -> bool:
    """ブラウザに新規タブを作成（active tabが無い状態の復旧用）"""
    result = _browser_post(port, '/browser/tabs/new', {"url": url}, timeout=timeout)
    return bool(result and result.get('success'))


def _browser_recover(port: int, timeout: int = 30) -> bool:
    """Playwrightがクラッシュした/変な状態になったときの復旧（close→init→new tab）"""
    _browser_post(port, '/browser/close', {}, timeout=timeout)
    init = _browser_post(port, '/browser/init', {}, timeout=timeout)
    if not (init and init.get('success')):
        return False
    return _browser_new_tab(port, timeout=timeout)


def browser_navigate(port: int, url: str, timeout: int = 30) -> bool:
    """ブラウザをURLにナビゲート"""
    api_url = f"http://localhost:{port}/browser/navigate"
    data = json.dumps({"url": url}).encode('utf-8')
    req = Request(api_url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("success", False)
    except HTTPError as e:
        # Browser APIが "No active tab" や "Page crashed" を返すことがある
        # → 状況に応じて 1回だけ復旧・リトライ
        try:
            body = e.read().decode('utf-8')
            if 'No active tab' in body:
                if _browser_new_tab(port, timeout=timeout):
                    with urlopen(req, timeout=timeout) as response:
                        result = json.loads(response.read().decode('utf-8'))
                        return result.get("success", False)
            if 'Page crashed' in body:
                if _browser_recover(port, timeout=timeout):
                    with urlopen(req, timeout=timeout) as response:
                        result = json.loads(response.read().decode('utf-8'))
                        return result.get("success", False)
        except Exception:
            pass
        return False
    except (URLError, json.JSONDecodeError, Exception):
        return False


def browser_evaluate(port: int, script: str, timeout: int = 60) -> Optional[str]:
    """ブラウザでJavaScriptを実行"""
    try:
        api_url = f"http://localhost:{port}/browser/evaluate"
        data = json.dumps({"script": script}).encode('utf-8')
        req = Request(api_url, data=data, headers={'Content-Type': 'application/json'})

        with urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get("success"):
                return result.get("result")
            return None
    except (URLError, json.JSONDecodeError, Exception):
        return None


def browser_get_content(port: int, timeout: int = 30) -> Optional[dict]:
    """ページコンテンツを取得"""
    try:
        api_url = f"http://localhost:{port}/browser/content"
        req = Request(api_url, data=b'', headers={'Content-Type': 'application/json'})

        with urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            if result.get("success"):
                return result
            return None
    except (URLError, json.JSONDecodeError, Exception):
        return None
