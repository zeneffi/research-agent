"""
Daytona Agent - Parallel Browser Research AI Agent

This package provides a CLI for running parallel browser research tasks
using Docker containers with Playwright.

Features:
- LLM-powered query decomposition and result summarization
- Semantic relevance filtering with embeddings
- Retry and fallback mechanisms for robust operation
- MCP server for Clawdbot integration
"""

__version__ = "0.2.0"
__author__ = "zeneffi"

from .cli import main
from .orchestrator import Orchestrator
from .browser_pool import BrowserPool
from .snapshot import SnapshotManager
from .task_parser import TaskParser, LLMTaskParser, create_parser
from .llm_client import LLMClient
from .semantic_filter import SemanticFilter
from .retry import retry_with_backoff, RetryConfig, FallbackChain

# MCP server (optional import)
try:
    from .mcp_server import ResearchAgentMCPServer
    _MCP_AVAILABLE = True
except ImportError:
    _MCP_AVAILABLE = False
    ResearchAgentMCPServer = None

__all__ = [
    "main",
    "Orchestrator",
    "BrowserPool",
    "SnapshotManager",
    "TaskParser",
    "LLMTaskParser",
    "create_parser",
    "LLMClient",
    "SemanticFilter",
    "retry_with_backoff",
    "RetryConfig",
    "FallbackChain",
    "ResearchAgentMCPServer",
]
