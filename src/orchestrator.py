"""
Orchestrator - Coordinates parallel browser research tasks.

Manages task distribution, result aggregation, and session state.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from rich.progress import Progress

from .browser_pool import BrowserPool, BrowserInstance
from .snapshot import SnapshotManager
from .task_parser import TaskParser, ResearchTask


@dataclass
class TaskResult:
    """Result of a single research task."""
    task_id: str
    instance_id: str
    status: str  # success, error, timeout
    url: str = ""
    title: str = ""
    content: str = ""
    screenshot_path: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    findings: list = field(default_factory=list)


@dataclass
class ResearchSession:
    """Represents a research session."""
    id: str
    query: str
    status: str  # running, completed, failed, paused
    parallel: int
    output_dir: Path
    screenshot: bool
    timeout: int
    created_at: datetime
    tasks: list[ResearchTask] = field(default_factory=list)
    results: list[TaskResult] = field(default_factory=list)
    completed: int = 0
    total: int = 0


class Orchestrator:
    """
    Orchestrates parallel browser research tasks.

    Responsibilities:
    - Parse query into research tasks
    - Manage browser pool
    - Distribute tasks to browsers
    - Collect and aggregate results
    - Save session state for resume
    """

    def __init__(
        self,
        parallel: int = 5,
        output_dir: Path = Path("data"),
        screenshot: bool = False,
        session_name: Optional[str] = None,
        timeout: int = 300,
        profile_dir: Optional[Path] = None
    ):
        self.parallel = parallel
        self.output_dir = output_dir
        self.screenshot = screenshot
        self.session_name = session_name or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.timeout = timeout
        self.profile_dir = profile_dir

        self.pool = BrowserPool()
        self.snapshot_manager = SnapshotManager(output_dir)
        self.task_parser = TaskParser()

        self.session: Optional[ResearchSession] = None
        self._running = False

    async def run(self, query: str, progress: Optional[Progress] = None) -> dict:
        """
        Run a research session.

        Args:
            query: Research query to investigate
            progress: Rich progress instance for UI updates

        Returns:
            Research results dictionary
        """
        self._running = True

        # Create session
        self.session = ResearchSession(
            id=str(uuid4()),
            query=query,
            status="running",
            parallel=self.parallel,
            output_dir=self.output_dir,
            screenshot=self.screenshot,
            timeout=self.timeout,
            created_at=datetime.now()
        )

        try:
            # Parse query into tasks
            if progress:
                task_id = progress.add_task("Parsing query...", total=None)

            tasks = await self.task_parser.parse(query)
            self.session.tasks = tasks
            self.session.total = len(tasks)

            if progress:
                progress.update(task_id, completed=True, description=f"Found {len(tasks)} research tasks")

            # Start browser pool
            if progress:
                pool_task = progress.add_task(f"Starting {self.parallel} browsers...", total=None)

            instances = await self.pool.start(
                count=min(self.parallel, len(tasks)),
                session=self.session_name,
                profile_dir=self.profile_dir
            )

            if progress:
                progress.update(pool_task, completed=True, description=f"Started {len(instances)} browsers")

            # Execute tasks in parallel
            if progress:
                research_task = progress.add_task("Researching...", total=len(tasks))

            results = await self._execute_tasks(tasks, instances, progress, research_task)
            self.session.results = results
            self.session.completed = len([r for r in results if r.status == "success"])

            # Aggregate findings
            findings = self._aggregate_findings(results)

            # Save session
            self.session.status = "completed"
            await self.snapshot_manager.save_session(self.session)

            # Save results to file
            output_path = await self._save_results(findings)

            return {
                "session_id": self.session.id,
                "completed": self.session.completed,
                "total": self.session.total,
                "findings": findings,
                "output_path": str(output_path)
            }

        except Exception as e:
            if self.session:
                self.session.status = "failed"
                await self.snapshot_manager.save_session(self.session)
            raise

        finally:
            self._running = False
            await self.pool.close()

    async def resume(
        self,
        session_data: dict,
        progress: Optional[Progress] = None
    ) -> dict:
        """
        Resume a paused session.

        Args:
            session_data: Saved session data
            progress: Rich progress instance

        Returns:
            Research results dictionary
        """
        # Restore session state
        self.session = ResearchSession(
            id=session_data["id"],
            query=session_data["query"],
            status="running",
            parallel=session_data.get("parallel", self.parallel),
            output_dir=Path(session_data.get("output_dir", self.output_dir)),
            screenshot=session_data.get("screenshot", self.screenshot),
            timeout=session_data.get("timeout", self.timeout),
            created_at=datetime.fromisoformat(session_data["created_at"]),
            completed=session_data.get("completed", 0),
            total=session_data.get("total", 0)
        )

        # Get remaining tasks
        completed_task_ids = {r["task_id"] for r in session_data.get("results", [])}
        remaining_tasks = [
            ResearchTask(**t) for t in session_data.get("tasks", [])
            if t["id"] not in completed_task_ids
        ]

        if not remaining_tasks:
            return {
                "session_id": self.session.id,
                "completed": self.session.completed,
                "total": self.session.total,
                "findings": [],
                "output_path": str(self.output_dir)
            }

        # Start browsers and continue
        instances = await self.pool.start(
            count=min(self.parallel, len(remaining_tasks)),
            session=self.session_name,
            profile_dir=self.profile_dir
        )

        if progress:
            research_task = progress.add_task(
                f"Resuming... ({len(remaining_tasks)} remaining)",
                total=len(remaining_tasks)
            )

        results = await self._execute_tasks(remaining_tasks, instances, progress, research_task)

        # Merge with previous results
        prev_results = [TaskResult(**r) for r in session_data.get("results", [])]
        all_results = prev_results + results
        self.session.results = all_results
        self.session.completed = len([r for r in all_results if r.status == "success"])

        findings = self._aggregate_findings(all_results)

        self.session.status = "completed"
        await self.snapshot_manager.save_session(self.session)
        output_path = await self._save_results(findings)

        await self.pool.close()

        return {
            "session_id": self.session.id,
            "completed": self.session.completed,
            "total": self.session.total,
            "findings": findings,
            "output_path": str(output_path)
        }

    async def _execute_tasks(
        self,
        tasks: list[ResearchTask],
        instances: list[BrowserInstance],
        progress: Optional[Progress] = None,
        progress_task_id: Optional[int] = None
    ) -> list[TaskResult]:
        """Execute research tasks on browser instances."""
        results = []
        task_queue = asyncio.Queue()

        # Fill queue with tasks
        for task in tasks:
            await task_queue.put(task)

        # Create worker coroutines
        async def worker(instance: BrowserInstance):
            while not task_queue.empty() and self._running:
                try:
                    task = task_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                result = await self._execute_single_task(task, instance)
                results.append(result)

                if progress and progress_task_id:
                    progress.update(progress_task_id, advance=1)

                task_queue.task_done()

        # Run workers
        workers = [worker(instance) for instance in instances]
        await asyncio.gather(*workers)

        return results

    async def _execute_single_task(
        self,
        task: ResearchTask,
        instance: BrowserInstance
    ) -> TaskResult:
        """Execute a single research task."""
        result = TaskResult(
            task_id=task.id,
            instance_id=instance.id,
            status="running",
            started_at=datetime.now()
        )

        try:
            # Navigate to URL
            nav_result = await asyncio.wait_for(
                self.pool.navigate(instance, task.url),
                timeout=self.timeout
            )

            if not nav_result.get("success"):
                result.status = "error"
                result.error = nav_result.get("error", "Navigation failed")
                return result

            result.url = nav_result.get("url", task.url)
            result.title = nav_result.get("title", "")

            # Wait for page to stabilize
            await asyncio.sleep(2)

            # Get page content
            content_result = await self.pool.get_content(instance)
            if content_result.get("success"):
                result.content = content_result.get("text", "")[:10000]  # Limit content size

            # Take screenshot if enabled
            if self.screenshot:
                screenshot_result = await self.pool.screenshot(instance, full_page=True)
                if screenshot_result.get("success"):
                    screenshot_path = await self._save_screenshot(
                        task.id,
                        screenshot_result.get("screenshot", "")
                    )
                    result.screenshot_path = str(screenshot_path)

            # Extract findings
            result.findings = self._extract_findings(result.content, task.keywords)
            result.status = "success"
            result.completed_at = datetime.now()

        except asyncio.TimeoutError:
            result.status = "timeout"
            result.error = f"Task timed out after {self.timeout}s"
        except Exception as e:
            result.status = "error"
            result.error = str(e)

        return result

    def _extract_findings(self, content: str, keywords: list[str]) -> list[dict]:
        """Extract relevant findings from page content."""
        findings = []

        if not content:
            return findings

        # Split content into paragraphs
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            para = para.strip()
            if len(para) < 50:
                continue

            # Check if paragraph contains any keywords
            para_lower = para.lower()
            matching_keywords = [k for k in keywords if k.lower() in para_lower]

            if matching_keywords:
                findings.append({
                    "text": para[:500],
                    "keywords": matching_keywords,
                    "relevance": len(matching_keywords) / len(keywords) if keywords else 0
                })

        # Sort by relevance and limit
        findings.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return findings[:10]

    def _aggregate_findings(self, results: list[TaskResult]) -> list[dict]:
        """Aggregate findings from all results."""
        all_findings = []

        for result in results:
            if result.status != "success":
                continue

            for finding in result.findings:
                all_findings.append({
                    "source": result.url,
                    "title": result.title,
                    "summary": finding.get("text", "")[:200],
                    "keywords": finding.get("keywords", []),
                    "relevance": finding.get("relevance", 0)
                })

        # Sort by relevance
        all_findings.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return all_findings[:50]

    async def _save_screenshot(self, task_id: str, base64_data: str) -> Path:
        """Save screenshot to file."""
        import base64

        screenshots_dir = self.output_dir / "screenshots" / self.session_name
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{task_id}-{datetime.now().strftime('%H%M%S')}.png"
        filepath = screenshots_dir / filename

        image_data = base64.b64decode(base64_data)
        filepath.write_bytes(image_data)

        return filepath

    async def _save_results(self, findings: list[dict]) -> Path:
        """Save results to JSON file."""
        results_dir = self.output_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{self.session_name}.json"
        filepath = results_dir / filename

        output = {
            "session_id": self.session.id if self.session else "",
            "query": self.session.query if self.session else "",
            "created_at": self.session.created_at.isoformat() if self.session else "",
            "completed_at": datetime.now().isoformat(),
            "stats": {
                "total": self.session.total if self.session else 0,
                "completed": self.session.completed if self.session else 0,
                "success_rate": (
                    self.session.completed / self.session.total * 100
                    if self.session and self.session.total > 0 else 0
                )
            },
            "findings": findings
        }

        filepath.write_text(json.dumps(output, indent=2, ensure_ascii=False))

        # Also save markdown summary
        await self._save_markdown_summary(findings)

        return filepath

    async def _save_markdown_summary(self, findings: list[dict]) -> Path:
        """Save markdown summary."""
        results_dir = self.output_dir / "results"
        filepath = results_dir / f"{self.session_name}.md"

        lines = [
            f"# Research: {self.session.query if self.session else 'Unknown'}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Tasks:** {self.session.completed if self.session else 0}/{self.session.total if self.session else 0}",
            "",
            "## Findings",
            ""
        ]

        for i, finding in enumerate(findings[:20], 1):
            lines.append(f"### {i}. {finding.get('title', 'Unknown')}")
            lines.append("")
            lines.append(f"**Source:** {finding.get('source', '')}")
            lines.append("")
            lines.append(finding.get('summary', ''))
            lines.append("")

        filepath.write_text('\n'.join(lines))
        return filepath

    async def stop(self) -> None:
        """Stop the orchestrator and save session state."""
        self._running = False

        if self.session:
            self.session.status = "paused"
            await self.snapshot_manager.save_session(self.session)

        await self.pool.stop(session=self.session_name)
        await self.pool.close()
