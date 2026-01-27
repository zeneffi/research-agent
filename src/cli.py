"""
CLI entry point for the Daytona Agent.

Usage:
    python -m daytona_agent research "query" --parallel 5 --screenshot
    python -m daytona_agent status
    python -m daytona_agent stop
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.live import Live

from .orchestrator import Orchestrator
from .browser_pool import BrowserPool
from .snapshot import SnapshotManager
from .task_parser import TaskParser
from .agent_registry import AgentRegistry

console = Console()

DEFAULT_PARALLEL = 5
MAX_PARALLEL = 15
DEFAULT_OUTPUT_DIR = Path("data")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="daytona-agent",
        description="Parallel Browser Research AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m daytona_agent research "AI エージェントの最新動向"
    python -m daytona_agent research "Python 3.12の新機能" --parallel 3
    python -m daytona_agent research "クラウドサービス比較" --screenshot
    python -m daytona_agent status
    python -m daytona_agent stop
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # research command
    research_parser = subparsers.add_parser("research", help="Start a research session")
    research_parser.add_argument(
        "query",
        type=str,
        help="Research query to investigate"
    )
    research_parser.add_argument(
        "--parallel", "-p",
        type=int,
        default=DEFAULT_PARALLEL,
        help=f"Number of parallel browsers (default: {DEFAULT_PARALLEL}, max: {MAX_PARALLEL})"
    )
    research_parser.add_argument(
        "--output", "-o",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    research_parser.add_argument(
        "--screenshot", "-s",
        action="store_true",
        help="Save screenshots at each step"
    )
    research_parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session name for resuming"
    )
    research_parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browsers in headless mode (no VNC)"
    )
    research_parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds per task (default: 300)"
    )
    research_parser.add_argument(
        "--agent",
        type=str,
        default=None,
        help="Use a registered agent profile"
    )

    # status command
    status_parser = subparsers.add_parser("status", help="Show current status")
    status_parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session name to check"
    )

    # stop command
    stop_parser = subparsers.add_parser("stop", help="Stop running containers")
    stop_parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session name to stop (stops all if not specified)"
    )
    stop_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force stop without confirmation"
    )

    # list command
    list_parser = subparsers.add_parser("list", help="List sessions")
    list_parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Show all sessions including completed"
    )

    # resume command
    resume_parser = subparsers.add_parser("resume", help="Resume a session")
    resume_parser.add_argument(
        "session",
        type=str,
        help="Session name to resume"
    )

    # agent command
    agent_parser = subparsers.add_parser("agent", help="Manage agents")
    agent_subparsers = agent_parser.add_subparsers(dest="agent_command", help="Agent commands")

    # agent register
    agent_register = agent_subparsers.add_parser("register", help="Register a new agent")
    agent_register.add_argument("name", type=str, help="Agent name")
    agent_register.add_argument("--type", type=str, required=True, help="Agent type (search, scraper, etc.)")
    agent_register.add_argument("--file", type=str, required=True, help="Path to agent script")
    agent_register.add_argument("--description", type=str, default="", help="Agent description")

    # agent list
    agent_list = agent_subparsers.add_parser("list", help="List all agents")
    agent_list.add_argument("--type", type=str, help="Filter by agent type")
    agent_list.add_argument("--enabled-only", action="store_true", help="Show only enabled agents")

    # agent delete
    agent_delete = agent_subparsers.add_parser("delete", help="Delete an agent")
    agent_delete.add_argument("name", type=str, help="Agent name")
    agent_delete.add_argument("--delete-profile", action="store_true", help="Also delete profile data")

    return parser


async def cmd_research(args: argparse.Namespace) -> int:
    """Execute research command."""
    # 並列数の検証
    parallel = min(max(1, args.parallel), MAX_PARALLEL)
    if parallel != args.parallel:
        console.print(f"[yellow]Adjusted parallel count to {parallel}[/yellow]")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # エージェントプロファイルを取得
    profile_dir = None
    if args.agent:
        registry = AgentRegistry()
        agent = registry.get(args.agent)
        if not agent:
            console.print(f"[red]Agent '{args.agent}' not found[/red]")
            return 1
        profile_dir = Path(agent.profile_dir)
        console.print(f"[green]Using agent: {agent.name}[/green]")
        console.print(f"[green]Profile: {profile_dir}[/green]")

    console.print(Panel(
        f"[bold blue]Starting Research Session[/bold blue]\n\n"
        f"Query: {args.query}\n"
        f"Parallel browsers: {parallel}\n"
        f"Output: {output_dir}\n"
        f"Screenshots: {'Enabled' if args.screenshot else 'Disabled'}\n"
        f"Agent: {args.agent or 'None'}",
        title="Daytona Agent"
    ))

    # オーケストレーター初期化
    orchestrator = Orchestrator(
        parallel=parallel,
        output_dir=output_dir,
        screenshot=args.screenshot,
        session_name=args.session,
        timeout=args.timeout,
        profile_dir=profile_dir
    )

    try:
        # 調査実行
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            result = await orchestrator.run(args.query, progress)

        # 結果表示
        console.print("\n")
        console.print(Panel(
            f"[bold green]Research Complete[/bold green]\n\n"
            f"Tasks completed: {result.get('completed', 0)}/{result.get('total', 0)}\n"
            f"Results saved to: {result.get('output_path', output_dir)}",
            title="Results"
        ))

        # 結果サマリーをテーブル表示
        if result.get('findings'):
            table = Table(title="Research Findings")
            table.add_column("Source", style="cyan")
            table.add_column("Summary", style="green")

            for finding in result.get('findings', [])[:10]:
                table.add_row(
                    finding.get('source', 'Unknown'),
                    finding.get('summary', '')[:100] + '...'
                )

            console.print(table)

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        await orchestrator.stop()
        return 130
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        await orchestrator.stop()
        return 1


async def cmd_status(args: argparse.Namespace) -> int:
    """Show status of running containers."""
    pool = BrowserPool()

    try:
        status = await pool.status(session=args.session)

        if not status.get('containers'):
            console.print("[yellow]No running containers[/yellow]")
            return 0

        table = Table(title="Running Containers")
        table.add_column("Container", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Ports", style="yellow")
        table.add_column("Session", style="blue")

        for container in status.get('containers', []):
            table.add_row(
                container.get('name', 'Unknown'),
                container.get('status', 'Unknown'),
                container.get('ports', ''),
                container.get('session', '')
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


async def cmd_stop(args: argparse.Namespace) -> int:
    """Stop running containers."""
    pool = BrowserPool()

    if not args.force:
        if args.session:
            confirm = console.input(f"Stop session '{args.session}'? [y/N] ")
        else:
            confirm = console.input("Stop all containers? [y/N] ")

        if confirm.lower() != 'y':
            console.print("[yellow]Cancelled[/yellow]")
            return 0

    try:
        await pool.stop(session=args.session)
        console.print("[green]Containers stopped[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


async def cmd_list(args: argparse.Namespace) -> int:
    """List sessions."""
    snapshot_manager = SnapshotManager()

    try:
        sessions = await snapshot_manager.list_sessions(include_completed=args.all)

        if not sessions:
            console.print("[yellow]No sessions found[/yellow]")
            return 0

        table = Table(title="Sessions")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Created", style="yellow")
        table.add_column("Tasks", style="blue")

        for session in sessions:
            table.add_row(
                session.get('name', 'Unknown'),
                session.get('status', 'Unknown'),
                session.get('created', ''),
                f"{session.get('completed', 0)}/{session.get('total', 0)}"
            )

        console.print(table)
        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


async def cmd_resume(args: argparse.Namespace) -> int:
    """Resume a session."""
    snapshot_manager = SnapshotManager()

    try:
        session = await snapshot_manager.load_session(args.session)
        if not session:
            console.print(f"[red]Session '{args.session}' not found[/red]")
            return 1

        console.print(f"[green]Resuming session '{args.session}'...[/green]")

        orchestrator = Orchestrator(
            parallel=session.get('parallel', DEFAULT_PARALLEL),
            output_dir=Path(session.get('output_dir', DEFAULT_OUTPUT_DIR)),
            screenshot=session.get('screenshot', False),
            session_name=args.session,
            timeout=session.get('timeout', 300)
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            result = await orchestrator.resume(session, progress)

        console.print(Panel(
            f"[bold green]Session Resumed and Complete[/bold green]\n\n"
            f"Tasks completed: {result.get('completed', 0)}/{result.get('total', 0)}",
            title="Results"
        ))

        return 0

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


async def cmd_agent(args: argparse.Namespace) -> int:
    """Manage agents."""
    registry = AgentRegistry()

    if args.agent_command == "register":
        try:
            agent = registry.register(
                name=args.name,
                agent_type=args.type,
                file_path=args.file,
                description=args.description
            )
            console.print(f"[green]Agent '{agent.name}' registered successfully[/green]")
            console.print(f"Profile directory: {agent.profile_dir}")
            return 0
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            return 1

    elif args.agent_command == "list":
        agents = registry.list(
            agent_type=args.type,
            enabled_only=args.enabled_only
        )

        if not agents:
            console.print("[yellow]No agents found[/yellow]")
            return 0

        table = Table(title="Registered Agents")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("File Path", style="yellow")
        table.add_column("Profile Dir", style="blue")
        table.add_column("Status", style="magenta")

        for agent in agents:
            table.add_row(
                agent.name,
                agent.agent_type,
                agent.file_path,
                agent.profile_dir,
                "✓ Enabled" if agent.enabled else "✗ Disabled"
            )

        console.print(table)
        return 0

    elif args.agent_command == "delete":
        if registry.delete(args.name, delete_profile=args.delete_profile):
            console.print(f"[green]Agent '{args.name}' deleted[/green]")
            return 0
        else:
            console.print(f"[red]Agent '{args.name}' not found[/red]")
            return 1

    return 0


async def async_main(args: argparse.Namespace) -> int:
    """Async main entry point."""
    if args.command == "research":
        return await cmd_research(args)
    elif args.command == "status":
        return await cmd_status(args)
    elif args.command == "stop":
        return await cmd_stop(args)
    elif args.command == "list":
        return await cmd_list(args)
    elif args.command == "resume":
        return await cmd_resume(args)
    elif args.command == "agent":
        return await cmd_agent(args)
    else:
        parser = create_parser()
        parser.print_help()
        return 0


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return asyncio.run(async_main(args))


if __name__ == "__main__":
    sys.exit(main())
