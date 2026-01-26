"""
Daytona Agent - Parallel Browser Research AI Agent

This package provides a CLI for running parallel browser research tasks
using Docker containers with Playwright.
"""

__version__ = "0.1.0"
__author__ = "zeneffi"

from .cli import main
from .orchestrator import Orchestrator
from .browser_pool import BrowserPool
from .snapshot import SnapshotManager
from .task_parser import TaskParser

__all__ = [
    "main",
    "Orchestrator",
    "BrowserPool",
    "SnapshotManager",
    "TaskParser",
]
