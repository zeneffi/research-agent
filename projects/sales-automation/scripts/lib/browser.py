"""
ブラウザ操作関数
funding_collector から流用
"""
import json
import subprocess
import re
import os
from typing import Optional, List


def get_container_ports() -> List[int]:
    """起動中のコンテナのAPIポートを取得"""
    # docker-compose.yaml のディレクトリを特定
    # Go up from lib -> scripts -> sales-automation -> projects -> research-agent
    docker_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
        "docker"
    )

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
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/navigate",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"url": url})],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        data = json.loads(result.stdout)
        return data.get("success", False)
    except Exception as e:
        return False


def browser_evaluate(port: int, script: str, timeout: int = 60) -> Optional[str]:
    """ブラウザでJavaScriptを実行"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/evaluate",
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"script": script})],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        data = json.loads(result.stdout)
        if data.get("success"):
            return data.get("result")
        return None
    except Exception as e:
        return None


def browser_get_content(port: int, timeout: int = 30) -> Optional[dict]:
    """ページコンテンツを取得"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"http://localhost:{port}/browser/content"],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        data = json.loads(result.stdout)
        if data.get("success"):
            return data
        return None
    except Exception as e:
        return None
