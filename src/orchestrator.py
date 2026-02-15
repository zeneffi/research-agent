"""
Orchestrator - Coordinates parallel browser research tasks.

Manages task distribution, result aggregation, and session state.
Supports LLM-powered query decomposition and result summarization.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING
from uuid import uuid4

from rich.progress import Progress

from .browser_pool import BrowserPool, BrowserInstance
from .snapshot import SnapshotManager
from .task_parser import TaskParser, LLMTaskParser, ResearchTask, create_parser
from .semantic_filter import SemanticFilter
from .retry import retry_with_backoff, RetryConfig, get_fallback_search_url

if TYPE_CHECKING:
    from .llm_client import LLMClient


# System prompt for result summarization
SUMMARIZATION_PROMPT = """You are a research analyst. Your job is to synthesize research findings into a clear, actionable summary.

Given a set of research findings from multiple sources, create a comprehensive summary that:
1. Identifies the key insights and themes
2. Highlights important facts and statistics
3. Notes any conflicting information between sources
4. Provides actionable conclusions

Format your response as Markdown with the following structure:

## Summary
A brief 2-3 sentence overview of the findings.

## Key Insights
- Bullet points of the most important discoveries

## Details
Detailed findings organized by topic/theme.

## Sources
Notable sources and their contributions.

## Conclusions
Actionable takeaways from the research.

Be concise but thorough. Focus on information that directly answers the original research query."""


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
    - Summarize findings with LLM (optional)
    """

    def __init__(
        self,
        parallel: int = 5,
        output_dir: Path = Path("data"),
        screenshot: bool = False,
        session_name: Optional[str] = None,
        timeout: int = 300,
        profile_dir: Optional[Path] = None,
        use_llm: bool = False,
        llm_client: Optional["LLMClient"] = None,
    ):
        self.parallel = parallel
        self.output_dir = output_dir
        self.screenshot = screenshot
        self.session_name = session_name or f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.timeout = timeout
        self.profile_dir = profile_dir
        self.use_llm = use_llm
        self.llm_client = llm_client
        self.use_semantic_filter = use_llm  # Enable semantic filter with LLM

        self.pool = BrowserPool()
        self.snapshot_manager = SnapshotManager(output_dir)
        self.task_parser = create_parser(use_llm=use_llm)
        self.semantic_filter = SemanticFilter() if self.use_semantic_filter else None

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

            # Aggregate findings (with semantic filtering if enabled)
            findings = await self._aggregate_findings(results, query)

            # Summarize with LLM if enabled
            if progress and self.use_llm:
                summary_task = progress.add_task("Summarizing results...", total=None)
            
            summary = await self.summarize_results(findings, query)
            
            if progress and self.use_llm:
                progress.update(summary_task, completed=True, description="Summary generated")

            # Save session
            self.session.status = "completed"
            await self.snapshot_manager.save_session(self.session)

            # Save results to file
            output_path = await self._save_results(findings, summary)

            return {
                "session_id": self.session.id,
                "completed": self.session.completed,
                "total": self.session.total,
                "findings": findings,
                "summary": summary,
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

        findings = await self._aggregate_findings(all_results, session_data["query"])
        summary = await self.summarize_results(findings, session_data["query"])

        self.session.status = "completed"
        await self.snapshot_manager.save_session(self.session)
        output_path = await self._save_results(findings, summary)

        await self.pool.close()

        return {
            "session_id": self.session.id,
            "completed": self.session.completed,
            "total": self.session.total,
            "findings": findings,
            "summary": summary,
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
        instance: BrowserInstance,
        max_retries: int = 2,
    ) -> TaskResult:
        """Execute a single research task with retry and fallback support."""
        result = TaskResult(
            task_id=task.id,
            instance_id=instance.id,
            status="running",
            started_at=datetime.now()
        )
        
        # URLs to try (original + fallbacks)
        urls_to_try = [task.url]
        
        # Add fallback URL if this is a search task
        if task.task_type == "search":
            # Extract engine from URL
            failed_engine = None
            for engine in ["duckduckgo", "google", "bing"]:
                if engine in task.url.lower():
                    failed_engine = engine
                    break
            
            if failed_engine:
                fallback_url = get_fallback_search_url(task.query, failed_engine)
                if fallback_url:
                    urls_to_try.append(fallback_url)

        last_error: Optional[str] = None
        
        for url_idx, url in enumerate(urls_to_try):
            for attempt in range(max_retries + 1):
                try:
                    # Navigate to URL with retry
                    nav_result = await asyncio.wait_for(
                        self.pool.navigate(instance, url),
                        timeout=self.timeout
                    )

                    if not nav_result.get("success"):
                        last_error = nav_result.get("error", "Navigation failed")
                        if attempt < max_retries:
                            # Wait before retry with exponential backoff
                            await asyncio.sleep(1.0 * (2 ** attempt))
                            continue
                        # Try next URL
                        break

                    result.url = nav_result.get("url", url)
                    result.title = nav_result.get("title", "")

                    # Wait for page to stabilize
                    await asyncio.sleep(2)

                    # Get page content with retry
                    content_result = await self._get_content_with_retry(instance)
                    if content_result.get("success"):
                        result.content = content_result.get("text", "")[:10000]

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
                    return result

                except asyncio.TimeoutError:
                    last_error = f"Timeout after {self.timeout}s"
                    if attempt < max_retries:
                        await asyncio.sleep(1.0 * (2 ** attempt))
                        continue
                    # Try next URL
                    break
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries:
                        await asyncio.sleep(1.0 * (2 ** attempt))
                        continue
                    # Try next URL
                    break

        # All URLs and retries exhausted
        result.status = "error"
        result.error = last_error or "Unknown error"
        result.completed_at = datetime.now()
        return result
    
    async def _get_content_with_retry(
        self,
        instance: BrowserInstance,
        max_retries: int = 2,
    ) -> dict:
        """Get page content with retry."""
        for attempt in range(max_retries + 1):
            try:
                result = await self.pool.get_content(instance)
                if result.get("success"):
                    return result
            except Exception:
                pass
            
            if attempt < max_retries:
                await asyncio.sleep(0.5 * (2 ** attempt))
        
        return {"success": False, "error": "Failed to get content"}

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

    async def _aggregate_findings(
        self,
        results: list[TaskResult],
        query: str = "",
    ) -> list[dict]:
        """Aggregate findings from all results, optionally with semantic filtering."""
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

        # Apply semantic filtering if available
        if self.semantic_filter and self.semantic_filter.available and query:
            try:
                scored = await self.semantic_filter.filter_findings(
                    query=query,
                    findings=all_findings,
                    top_k=50,
                )
                return [self.semantic_filter.scored_to_dict(s) for s in scored]
            except Exception:
                # Fall through to basic sorting on error
                pass

        # Sort by relevance
        all_findings.sort(key=lambda x: x.get("relevance", 0), reverse=True)
        return all_findings[:50]

    async def summarize_results(
        self,
        findings: list[dict],
        query: str,
    ) -> str:
        """
        Summarize research findings using LLM.
        
        Args:
            findings: Aggregated findings from research
            query: Original research query
            
        Returns:
            Markdown summary of findings
        """
        if not self.use_llm or not findings:
            return self._generate_basic_summary(findings, query)
        
        try:
            # Get or create LLM client
            if self.llm_client is None:
                from .llm_client import LLMClient
                self.llm_client = LLMClient()
            
            # Prepare findings text for LLM
            findings_text = self._format_findings_for_llm(findings)
            
            prompt = f"""Original Research Query: {query}

Research Findings:
{findings_text}

Please synthesize these findings into a comprehensive research summary."""
            
            response = await self.llm_client.complete(
                prompt=prompt,
                system=SUMMARIZATION_PROMPT,
            )
            
            return response.content
            
        except Exception as e:
            # Fallback to basic summary on error
            return self._generate_basic_summary(findings, query) + f"\n\n*Note: LLM summarization failed: {e}*"
    
    def _format_findings_for_llm(self, findings: list[dict]) -> str:
        """Format findings for LLM consumption."""
        sections = []
        
        for i, finding in enumerate(findings[:20], 1):
            source = finding.get("source", "Unknown")
            title = finding.get("title", "No title")
            summary = finding.get("summary", "")
            
            sections.append(f"""### Finding {i}
**Source:** {source}
**Title:** {title}
**Content:** {summary}
""")
        
        return "\n".join(sections)
    
    def _generate_basic_summary(self, findings: list[dict], query: str) -> str:
        """Generate basic summary without LLM."""
        lines = [
            f"# Research Summary: {query}",
            "",
            f"**Total Findings:** {len(findings)}",
            "",
            "## Top Findings",
            "",
        ]
        
        for i, finding in enumerate(findings[:10], 1):
            lines.append(f"### {i}. {finding.get('title', 'Unknown')}")
            lines.append(f"**Source:** {finding.get('source', '')}")
            lines.append(f"{finding.get('summary', '')}")
            lines.append("")
        
        return "\n".join(lines)

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

    async def _save_results(
        self,
        findings: list[dict],
        summary: Optional[str] = None,
    ) -> Path:
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
            "findings": findings,
            "summary": summary or "",
        }

        filepath.write_text(json.dumps(output, indent=2, ensure_ascii=False))

        # Also save markdown summary
        await self._save_markdown_summary(findings, summary)

        return filepath

    async def _save_markdown_summary(
        self,
        findings: list[dict],
        summary: Optional[str] = None,
    ) -> Path:
        """Save markdown summary."""
        results_dir = self.output_dir / "results"
        filepath = results_dir / f"{self.session_name}.md"

        lines = [
            f"# Research: {self.session.query if self.session else 'Unknown'}",
            "",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Tasks:** {self.session.completed if self.session else 0}/{self.session.total if self.session else 0}",
            "",
        ]
        
        # Add LLM summary if available
        if summary:
            lines.append("## Summary")
            lines.append("")
            lines.append(summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("## Raw Findings")
        lines.append("")

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
