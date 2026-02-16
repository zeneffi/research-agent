"""
MCP Server - Model Context Protocol server for research-agent.

Exposes research-agent functionality as MCP tools for integration
with Clawdbot and other MCP-compatible systems.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    Server = None
    Tool = None
    TextContent = None

from .orchestrator import Orchestrator


@dataclass
class ResearchJob:
    """Represents an ongoing research job."""
    id: str
    query: str
    status: str  # pending, running, completed, failed
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class ResearchAgentMCPServer:
    """
    MCP server exposing research-agent tools.
    
    Tools:
    - research.start: Start a new research session
    - research.status: Check status of a research job
    - research.results: Get results of a completed research job
    - research.list: List all research jobs
    """
    
    def __init__(
        self,
        output_dir: Path = Path("data"),
        use_llm: bool = True,
        parallel: int = 3,
    ):
        """
        Initialize MCP server.
        
        Args:
            output_dir: Directory for research output
            use_llm: Whether to use LLM features
            parallel: Number of parallel browsers
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "MCP package is required. Install with: pip install mcp"
            )
        
        self.output_dir = output_dir
        self.use_llm = use_llm
        self.parallel = parallel
        
        # Track active jobs
        self._jobs: dict[str, ResearchJob] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        
        # Cleanup settings
        self._max_completed_jobs = 100
        self._job_retention_hours = 24
        
        # Create MCP server
        self.server = Server("research-agent")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP tool handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="research_start",
                    description="Start a new research session. Returns a job ID to track progress.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Research query to investigate"
                            },
                            "parallel": {
                                "type": "integer",
                                "description": "Number of parallel browsers (default: 3)",
                                "default": 3
                            },
                            "screenshot": {
                                "type": "boolean",
                                "description": "Take screenshots of pages",
                                "default": False
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="research_status",
                    description="Check status of a research job.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID returned from research_start"
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="research_results",
                    description="Get results of a completed research job.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "job_id": {
                                "type": "string",
                                "description": "Job ID returned from research_start"
                            },
                            "include_raw": {
                                "type": "boolean",
                                "description": "Include raw findings (default: false)",
                                "default": False
                            }
                        },
                        "required": ["job_id"]
                    }
                ),
                Tool(
                    name="research_list",
                    description="List all research jobs.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "status": {
                                "type": "string",
                                "description": "Filter by status (pending, running, completed, failed)",
                                "enum": ["pending", "running", "completed", "failed"]
                            }
                        }
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            try:
                if name == "research_start":
                    result = await self._start_research(
                        query=arguments["query"],
                        parallel=arguments.get("parallel", self.parallel),
                        screenshot=arguments.get("screenshot", False),
                    )
                elif name == "research_status":
                    result = await self._get_status(arguments["job_id"])
                elif name == "research_results":
                    result = await self._get_results(
                        arguments["job_id"],
                        include_raw=arguments.get("include_raw", False),
                    )
                elif name == "research_list":
                    result = await self._list_jobs(
                        status=arguments.get("status")
                    )
                else:
                    result = {"error": f"Unknown tool: {name}"}
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, ensure_ascii=False, default=str)
                )]
                
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    def _cleanup_completed_jobs(self) -> None:
        """Remove old completed/failed jobs to prevent memory leaks."""
        now = datetime.now(timezone.utc)
        completed_jobs = [
            (job_id, job) for job_id, job in self._jobs.items()
            if job.status in ("completed", "failed")
        ]
        
        # Remove jobs older than retention period
        for job_id, job in completed_jobs:
            if job.completed_at:
                age_hours = (now - job.completed_at).total_seconds() / 3600
                if age_hours > self._job_retention_hours:
                    self._jobs.pop(job_id, None)
                    self._running_tasks.pop(job_id, None)
        
        # If still too many completed jobs, remove oldest ones
        remaining_completed = [
            (job_id, job) for job_id, job in self._jobs.items()
            if job.status in ("completed", "failed")
        ]
        if len(remaining_completed) > self._max_completed_jobs:
            sorted_jobs = sorted(
                remaining_completed,
                key=lambda x: x[1].completed_at or x[1].created_at
            )
            for job_id, _ in sorted_jobs[:-self._max_completed_jobs]:
                self._jobs.pop(job_id, None)
                self._running_tasks.pop(job_id, None)

    async def _start_research(
        self,
        query: str,
        parallel: int = 3,
        screenshot: bool = False,
    ) -> dict:
        """Start a new research job."""
        # Cleanup old completed jobs before starting new one
        self._cleanup_completed_jobs()
        
        job_id = str(uuid4())[:8]
        
        job = ResearchJob(
            id=job_id,
            query=query,
            status="pending",
            created_at=datetime.now(timezone.utc),
        )
        self._jobs[job_id] = job
        
        # Start research in background
        task = asyncio.create_task(
            self._run_research(job_id, query, parallel, screenshot)
        )
        self._running_tasks[job_id] = task
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": f"Research started for: {query}"
        }
    
    async def _run_research(
        self,
        job_id: str,
        query: str,
        parallel: int,
        screenshot: bool,
    ):
        """Run research job in background."""
        job = self._jobs.get(job_id)
        if not job:
            return
        
        job.status = "running"
        
        try:
            orchestrator = Orchestrator(
                parallel=parallel,
                output_dir=self.output_dir,
                screenshot=screenshot,
                use_llm=self.use_llm,
            )
            
            result = await orchestrator.run(query)
            
            job.status = "completed"
            job.completed_at = datetime.now(timezone.utc)
            job.result = result
            
        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)
            job.error = str(e)
        
        finally:
            # Cleanup task reference
            if job_id in self._running_tasks:
                del self._running_tasks[job_id]
    
    async def _get_status(self, job_id: str) -> dict:
        """Get status of a research job."""
        job = self._jobs.get(job_id)
        
        if not job:
            return {"error": f"Job not found: {job_id}"}
        
        result = {
            "job_id": job.id,
            "query": job.query,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        }
        
        if job.completed_at:
            result["completed_at"] = job.completed_at.isoformat()
        
        if job.error:
            result["error"] = job.error
        
        if job.result:
            result["stats"] = {
                "completed": job.result.get("completed", 0),
                "total": job.result.get("total", 0),
            }
        
        return result
    
    async def _get_results(
        self,
        job_id: str,
        include_raw: bool = False,
    ) -> dict:
        """Get results of a completed research job."""
        job = self._jobs.get(job_id)
        
        if not job:
            return {"error": f"Job not found: {job_id}"}
        
        if job.status == "pending":
            return {"error": "Research not started yet", "status": "pending"}
        
        if job.status == "running":
            return {"error": "Research still running", "status": "running"}
        
        if job.status == "failed":
            return {"error": job.error, "status": "failed"}
        
        result = {
            "job_id": job.id,
            "query": job.query,
            "status": "completed",
            "summary": job.result.get("summary", ""),
            "output_path": job.result.get("output_path", ""),
        }
        
        if include_raw:
            result["findings"] = job.result.get("findings", [])
        
        return result
    
    async def _list_jobs(self, status: Optional[str] = None) -> dict:
        """List all research jobs."""
        jobs = []
        
        for job in self._jobs.values():
            if status and job.status != status:
                continue
            
            jobs.append({
                "job_id": job.id,
                "query": job.query[:50] + "..." if len(job.query) > 50 else job.query,
                "status": job.status,
                "created_at": job.created_at.isoformat(),
            })
        
        return {
            "jobs": jobs,
            "total": len(jobs),
        }
    
    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


async def main():
    """Main entry point for MCP server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Research Agent MCP Server")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Output directory for research results"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM features"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=3,
        help="Number of parallel browsers"
    )
    
    args = parser.parse_args()
    
    server = ResearchAgentMCPServer(
        output_dir=args.output_dir,
        use_llm=not args.no_llm,
        parallel=args.parallel,
    )
    
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
