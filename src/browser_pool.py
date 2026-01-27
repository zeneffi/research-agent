"""
Browser Pool - Docker container lifecycle management for browser instances.

Manages a pool of Docker containers running Playwright browsers.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from uuid import uuid4

import aiohttp


@dataclass
class BrowserInstance:
    """Represents a single browser container instance."""
    id: str
    container_id: str
    container_name: str
    session: str
    api_port: int
    vnc_port: int
    novnc_port: int
    status: str = "starting"
    current_url: str = ""
    error: Optional[str] = None


@dataclass
class PoolStatus:
    """Status of the browser pool."""
    total: int = 0
    running: int = 0
    starting: int = 0
    error: int = 0
    containers: list = field(default_factory=list)


class BrowserPool:
    """
    Manages a pool of Docker browser containers.

    Provides methods to:
    - Start/stop containers
    - Check health status
    - Execute browser commands
    - Manage sessions
    """

    def __init__(
        self,
        docker_compose_path: Optional[Path] = None,
        base_api_port: int = 3000,
        base_vnc_port: int = 5900,
        base_novnc_port: int = 6080,
        proxy_config_path: Optional[Path] = None
    ):
        self.docker_compose_path = docker_compose_path or Path(__file__).parent.parent / "docker"
        self.base_api_port = base_api_port
        self.base_vnc_port = base_vnc_port
        self.base_novnc_port = base_novnc_port
        self.instances: dict[str, BrowserInstance] = {}
        self._http_session: Optional[aiohttp.ClientSession] = None
        self.proxies: list[dict] = []

        # プロキシ設定を読み込む
        proxy_path = proxy_config_path or Path(__file__).parent.parent / "config" / "proxies.json"
        if proxy_path.exists():
            with open(proxy_path) as f:
                config = json.load(f)
                self.proxies = config.get("proxies", [])

    async def _get_http_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._http_session

    async def close(self):
        """Close HTTP session."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()

    def _parse_port(self, ports_str: str, container_port: int) -> int:
        """Parse host port from docker ports string.

        Args:
            ports_str: Ports string like "0.0.0.0:50103->3000/tcp, ..."
            container_port: Container port to find (e.g., 3000)

        Returns:
            Host port number
        """
        import re
        # Match pattern like "0.0.0.0:50103->3000/tcp"
        pattern = rf"0\.0\.0\.0:(\d+)->{container_port}/tcp"
        match = re.search(pattern, ports_str)
        if match:
            return int(match.group(1))
        return container_port  # Fallback to container port

    def _run_docker_command(self, *args: str, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a docker command."""
        cmd = ["docker"] + list(args)
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            cwd=self.docker_compose_path
        )

    def _run_compose_command(self, *args: str, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a docker-compose command."""
        cmd = ["docker", "compose"] + list(args)
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            cwd=self.docker_compose_path
        )

    async def start(
        self,
        count: int,
        session: str,
        build: bool = False,
        profile_dir: Optional[Path] = None
    ) -> list[BrowserInstance]:
        """
        Start browser containers with individual proxy assignments.

        Args:
            count: Number of containers to start
            session: Session name for labeling
            build: Whether to rebuild the image
            profile_dir: Browser profile directory to mount (for persistent login)

        Returns:
            List of started browser instances
        """
        # Build image if requested
        if build:
            result = self._run_compose_command("build")
            if result.returncode != 0:
                raise RuntimeError(f"Failed to build image: {result.stderr}")

        # 個別にコンテナを起動（プロキシ割り当て）
        for i in range(count):
            container_name = f"docker-browser-{i + 1}"

            # 既存コンテナを停止・削除
            self._run_docker_command("stop", container_name)
            self._run_docker_command("rm", "-f", container_name)

            # プロキシ設定
            env_args = [
                "-e", "DISPLAY=:99",
                "-e", "API_PORT=3000",
                "-e", "VNC_PORT=5900",
                "-e", "NOVNC_PORT=6080",
            ]

            if self.proxies and i < len(self.proxies):
                proxy = self.proxies[i]
                proxy_url = f"http://{proxy['host']}:{proxy['port']}"
                env_args.extend([
                    "-e", f"PROXY_SERVER={proxy_url}",
                    "-e", f"PROXY_USERNAME={proxy['username']}",
                    "-e", f"PROXY_PASSWORD={proxy['password']}",
                ])

            # ボリュームマウント設定
            volume_args = []
            if profile_dir:
                # プロファイルディレクトリをコンテナにマウント
                host_profile = Path(profile_dir).absolute()
                host_profile.mkdir(parents=True, exist_ok=True)
                volume_args = ["-v", f"{host_profile}:/app/profile"]
                env_args.extend(["-e", "BROWSER_PROFILE_DIR=/app/profile"])

            # コンテナを起動
            result = self._run_docker_command(
                "run", "-d",
                "--name", container_name,
                "--shm-size=2g",
                "-p", "3000",
                "-p", "5900",
                "-p", "6080",
                *env_args,
                *volume_args,
                "docker-browser"
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to start container {container_name}: {result.stderr}")

        # Wait for containers to be ready
        await asyncio.sleep(2)

        # Get container info
        containers = await self._get_containers(session)

        # Initialize browser instances
        instances = []
        for i, container in enumerate(containers):
            # Parse port mappings from container info
            ports_str = container.get("ports", "")
            api_port = self._parse_port(ports_str, 3000)
            vnc_port = self._parse_port(ports_str, 5900)
            novnc_port = self._parse_port(ports_str, 6080)

            instance = BrowserInstance(
                id=str(uuid4()),
                container_id=container["id"],
                container_name=container["name"],
                session=session,
                api_port=api_port,
                vnc_port=vnc_port,
                novnc_port=novnc_port
            )
            self.instances[instance.id] = instance
            instances.append(instance)

        # Wait for APIs to be ready
        await self._wait_for_ready(instances)

        return instances

    async def _get_containers(self, session: Optional[str] = None) -> list[dict]:
        """Get running container info."""
        result = self._run_docker_command(
            "ps", "--format", "json",
            "--filter", "ancestor=docker-browser"
        )

        if result.returncode != 0:
            # Try alternative filter
            result = self._run_compose_command("ps", "--format", "json")

        containers = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        container = json.loads(line)
                        containers.append({
                            "id": container.get("ID", container.get("id", "")),
                            "name": container.get("Names", container.get("name", "")),
                            "status": container.get("Status", container.get("status", "")),
                            "ports": container.get("Ports", container.get("ports", ""))
                        })
                    except json.JSONDecodeError:
                        continue

        return containers

    async def _wait_for_ready(
        self,
        instances: list[BrowserInstance],
        timeout: int = 60
    ) -> None:
        """Wait for all instances to be ready."""
        start_time = asyncio.get_event_loop().time()

        async def check_instance(instance: BrowserInstance) -> bool:
            try:
                session = await self._get_http_session()
                url = f"http://localhost:{instance.api_port}/health"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("browser") == "ready":
                            instance.status = "ready"
                            return True
                return False
            except Exception:
                return False

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                # Mark unready instances as error
                for instance in instances:
                    if instance.status != "ready":
                        instance.status = "error"
                        instance.error = "Timeout waiting for ready"
                break

            # Check all instances
            results = await asyncio.gather(
                *[check_instance(i) for i in instances],
                return_exceptions=True
            )

            if all(r is True for r in results):
                break

            await asyncio.sleep(1)

    async def stop(self, session: Optional[str] = None) -> None:
        """
        Stop browser containers.

        Args:
            session: Session name to stop. If None, stops all containers.
        """
        if session:
            # Stop specific session containers
            for instance_id, instance in list(self.instances.items()):
                if instance.session == session:
                    self._run_docker_command("stop", instance.container_id)
                    self._run_docker_command("rm", "-f", instance.container_id)
                    del self.instances[instance_id]
        else:
            # Stop all containers
            self._run_compose_command("down")
            self.instances.clear()

    async def status(self, session: Optional[str] = None) -> dict:
        """
        Get status of browser containers.

        Args:
            session: Session name to filter. If None, returns all.

        Returns:
            Status dictionary with container information
        """
        containers = await self._get_containers(session)

        pool_status = PoolStatus()
        pool_status.total = len(containers)

        for container in containers:
            status_str = container.get("status", "")
            if "Up" in status_str:
                pool_status.running += 1
            elif "starting" in status_str.lower():
                pool_status.starting += 1
            else:
                pool_status.error += 1

            pool_status.containers.append({
                "name": container.get("name", ""),
                "status": status_str,
                "ports": container.get("ports", ""),
                "session": session or ""
            })

        return {
            "total": pool_status.total,
            "running": pool_status.running,
            "starting": pool_status.starting,
            "error": pool_status.error,
            "containers": pool_status.containers
        }

    async def execute(
        self,
        instance: BrowserInstance,
        action: str,
        **kwargs
    ) -> dict:
        """
        Execute a browser action on an instance.

        Args:
            instance: Target browser instance
            action: Action to execute (navigate, click, type, screenshot, etc.)
            **kwargs: Action-specific parameters

        Returns:
            Action result dictionary
        """
        if instance.status != "ready":
            return {"success": False, "error": f"Instance not ready: {instance.status}"}

        session = await self._get_http_session()
        url = f"http://localhost:{instance.api_port}/browser/{action}"

        try:
            async with session.post(url, json=kwargs) as response:
                result = await response.json()
                return result
        except aiohttp.ClientError as e:
            return {"success": False, "error": str(e)}

    async def navigate(self, instance: BrowserInstance, url: str) -> dict:
        """Navigate to URL."""
        return await self.execute(instance, "navigate", url=url)

    async def screenshot(
        self,
        instance: BrowserInstance,
        full_page: bool = False
    ) -> dict:
        """Take a screenshot."""
        return await self.execute(instance, "screenshot", fullPage=full_page)

    async def snapshot(self, instance: BrowserInstance) -> dict:
        """Get page accessibility snapshot."""
        return await self.execute(instance, "snapshot")

    async def click(
        self,
        instance: BrowserInstance,
        selector: Optional[str] = None,
        text: Optional[str] = None
    ) -> dict:
        """Click an element."""
        return await self.execute(instance, "click", selector=selector, text=text)

    async def type_text(
        self,
        instance: BrowserInstance,
        text: str,
        selector: Optional[str] = None,
        submit: bool = False
    ) -> dict:
        """Type text into an element."""
        return await self.execute(
            instance, "type",
            text=text, selector=selector, submit=submit
        )

    async def get_content(self, instance: BrowserInstance) -> dict:
        """Get page content."""
        return await self.execute(instance, "content")

    async def wait(
        self,
        instance: BrowserInstance,
        selector: Optional[str] = None,
        text: Optional[str] = None,
        timeout: int = 30000
    ) -> dict:
        """Wait for element or text."""
        return await self.execute(
            instance, "wait",
            selector=selector, text=text, timeout=timeout
        )

    def get_instance(self, instance_id: str) -> Optional[BrowserInstance]:
        """Get instance by ID."""
        return self.instances.get(instance_id)

    def get_ready_instances(self) -> list[BrowserInstance]:
        """Get all ready instances."""
        return [i for i in self.instances.values() if i.status == "ready"]

    async def health_check(self) -> dict[str, bool]:
        """Check health of all instances."""
        results = {}
        session = await self._get_http_session()

        for instance_id, instance in self.instances.items():
            try:
                url = f"http://localhost:{instance.api_port}/health"
                async with session.get(url) as response:
                    results[instance_id] = response.status == 200
            except Exception:
                results[instance_id] = False
                instance.status = "error"

        return results
