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
from urllib.error import URLError


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


def browser_navigate(port: int, url: str, timeout: int = 30) -> bool:
    """ブラウザをURLにナビゲート"""
    try:
        api_url = f"http://localhost:{port}/browser/navigate"
        data = json.dumps({"url": url}).encode('utf-8')
        req = Request(api_url, data=data, headers={'Content-Type': 'application/json'})

        with urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get("success", False)
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
