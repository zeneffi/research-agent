"""
Agent Registry - Manages agent definitions and browser profiles.

Provides registration, lookup, and profile management for research agents.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AgentDefinition:
    """Definition of a research agent."""
    name: str
    agent_type: str  # search, scraper, analyzer, etc.
    file_path: str
    profile_dir: str  # ブラウザプロファイルディレクトリ
    description: str = ""
    enabled: bool = True
    config: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


class AgentRegistry:
    """
    Registry for managing research agent definitions.

    Provides:
    - Agent registration and lookup
    - Browser profile management
    - Agent configuration management
    """

    def __init__(
        self,
        config_dir: Path = Path("config"),
        profiles_dir: Path = Path("data/profiles")
    ):
        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.profiles_dir = profiles_dir
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        self.registry_path = config_dir / "agents.json"
        self.agents: dict[str, AgentDefinition] = {}
        self._load()

    def _load(self) -> None:
        """Load agents from registry file."""
        if not self.registry_path.exists():
            self._save()
            return

        try:
            data = json.loads(self.registry_path.read_text())
            for agent_data in data.get("agents", []):
                agent = AgentDefinition(**agent_data)
                self.agents[agent.name] = agent
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to load agents registry: {e}")

    def _save(self) -> None:
        """Save agents to registry file."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "agents": [asdict(agent) for agent in self.agents.values()]
        }

        self.registry_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False)
        )

    def register(
        self,
        name: str,
        agent_type: str,
        file_path: str,
        description: str = "",
        config: Optional[dict] = None,
        enabled: bool = True
    ) -> AgentDefinition:
        """
        Register a new agent.

        Args:
            name: Agent name (must be unique)
            agent_type: Type of agent (search, scraper, etc.)
            file_path: Path to agent implementation file
            description: Agent description
            config: Agent-specific configuration
            enabled: Whether agent is enabled

        Returns:
            Created AgentDefinition

        Raises:
            ValueError: If agent with same name already exists
        """
        if name in self.agents:
            raise ValueError(f"Agent '{name}' already exists")

        # プロファイルディレクトリを作成
        safe_name = name.lower().replace(" ", "-").replace("_", "-")
        profile_dir = self.profiles_dir / safe_name
        profile_dir.mkdir(parents=True, exist_ok=True)

        agent = AgentDefinition(
            name=name,
            agent_type=agent_type,
            file_path=file_path,
            profile_dir=str(profile_dir),
            description=description,
            config=config or {},
            enabled=enabled
        )

        self.agents[name] = agent
        self._save()
        return agent

    def get(self, name: str) -> Optional[AgentDefinition]:
        """Get an agent by name."""
        return self.agents.get(name)

    def list(
        self,
        agent_type: Optional[str] = None,
        enabled_only: bool = False
    ) -> list[AgentDefinition]:
        """List all agents."""
        agents = list(self.agents.values())

        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]

        if enabled_only:
            agents = [a for a in agents if a.enabled]

        return sorted(agents, key=lambda a: a.created_at)

    def delete(self, name: str, delete_profile: bool = False) -> bool:
        """
        Delete an agent.

        Args:
            name: Agent name
            delete_profile: Whether to delete the profile directory

        Returns:
            True if deleted, False if not found
        """
        if name not in self.agents:
            return False

        agent = self.agents[name]

        # プロファイルディレクトリを削除
        if delete_profile:
            profile_path = Path(agent.profile_dir)
            if profile_path.exists():
                import shutil
                shutil.rmtree(profile_path)

        del self.agents[name]
        self._save()
        return True

    def get_profile_dir(self, name: str) -> Optional[Path]:
        """Get profile directory for an agent."""
        agent = self.agents.get(name)
        if agent:
            return Path(agent.profile_dir)
        return None

    def exists(self, name: str) -> bool:
        """Check if an agent exists."""
        return name in self.agents
