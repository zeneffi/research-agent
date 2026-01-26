"""
Snapshot Manager - Session state persistence and recovery.

Handles saving and loading session states for resume functionality.
"""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class SnapshotManager:
    """
    Manages session snapshots for persistence and recovery.

    Provides:
    - Session state saving to JSON
    - Session loading and resumption
    - Session listing and cleanup
    """

    def __init__(self, data_dir: Path = Path("data")):
        self.data_dir = data_dir
        self.sessions_dir = data_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, session_name: str) -> Path:
        """Get path for a session file."""
        return self.sessions_dir / f"{session_name}.json"

    async def save_session(self, session: Any) -> Path:
        """
        Save session state to JSON file.

        Args:
            session: Session object with state to save

        Returns:
            Path to saved session file
        """
        filepath = self._session_path(session.id if hasattr(session, 'id') else str(session))

        # Convert session to dictionary
        if hasattr(session, '__dataclass_fields__'):
            session_dict = self._dataclass_to_dict(session)
        elif hasattr(session, '__dict__'):
            session_dict = self._object_to_dict(session)
        else:
            session_dict = {"data": session}

        # Add metadata
        session_dict["_saved_at"] = datetime.now().isoformat()
        session_dict["_version"] = "1.0"

        # Save to file
        filepath.write_text(
            json.dumps(session_dict, indent=2, ensure_ascii=False, default=str)
        )

        return filepath

    def _dataclass_to_dict(self, obj: Any) -> dict:
        """Convert dataclass to dictionary recursively."""
        result = {}
        for key, value in asdict(obj).items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, Path):
                result[key] = str(value)
            elif isinstance(value, list):
                result[key] = [
                    self._dataclass_to_dict(item) if hasattr(item, '__dataclass_fields__')
                    else self._serialize_value(item)
                    for item in value
                ]
            else:
                result[key] = self._serialize_value(value)
        return result

    def _object_to_dict(self, obj: Any) -> dict:
        """Convert regular object to dictionary."""
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue
            result[key] = self._serialize_value(value)
        return result

    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON."""
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, Path):
            return str(value)
        elif hasattr(value, '__dataclass_fields__'):
            return self._dataclass_to_dict(value)
        elif hasattr(value, '__dict__') and not isinstance(value, (str, int, float, bool, list, dict)):
            return self._object_to_dict(value)
        return value

    async def load_session(self, session_name: str) -> Optional[dict]:
        """
        Load session state from JSON file.

        Args:
            session_name: Name/ID of session to load

        Returns:
            Session dictionary or None if not found
        """
        # Try exact match first
        filepath = self._session_path(session_name)
        if filepath.exists():
            return json.loads(filepath.read_text())

        # Try finding by prefix
        for path in self.sessions_dir.glob(f"{session_name}*.json"):
            return json.loads(path.read_text())

        return None

    async def list_sessions(self, include_completed: bool = False) -> list[dict]:
        """
        List all sessions.

        Args:
            include_completed: Whether to include completed sessions

        Returns:
            List of session summary dictionaries
        """
        sessions = []

        for path in self.sessions_dir.glob("*.json"):
            try:
                session = json.loads(path.read_text())
                status = session.get("status", "unknown")

                if not include_completed and status == "completed":
                    continue

                sessions.append({
                    "name": path.stem,
                    "status": status,
                    "query": session.get("query", ""),
                    "created": session.get("created_at", ""),
                    "completed": session.get("completed", 0),
                    "total": session.get("total", 0),
                    "saved_at": session.get("_saved_at", "")
                })
            except (json.JSONDecodeError, KeyError):
                continue

        # Sort by creation time, newest first
        sessions.sort(key=lambda x: x.get("created", ""), reverse=True)
        return sessions

    async def delete_session(self, session_name: str) -> bool:
        """
        Delete a session.

        Args:
            session_name: Name/ID of session to delete

        Returns:
            True if deleted, False if not found
        """
        filepath = self._session_path(session_name)
        if filepath.exists():
            filepath.unlink()
            return True

        # Try finding by prefix
        for path in self.sessions_dir.glob(f"{session_name}*.json"):
            path.unlink()
            return True

        return False

    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Clean up sessions older than specified days.

        Args:
            days: Number of days to keep sessions

        Returns:
            Number of sessions deleted
        """
        import time

        deleted = 0
        cutoff = time.time() - (days * 24 * 60 * 60)

        for path in self.sessions_dir.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink()
                deleted += 1

        return deleted

    async def save_screenshot(
        self,
        session_name: str,
        task_id: str,
        image_data: bytes,
        suffix: str = ""
    ) -> Path:
        """
        Save a screenshot for a session.

        Args:
            session_name: Session name
            task_id: Task ID
            image_data: PNG image data
            suffix: Optional suffix for filename

        Returns:
            Path to saved screenshot
        """
        screenshots_dir = self.data_dir / "screenshots" / session_name
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{task_id}-{timestamp}{suffix}.png"
        filepath = screenshots_dir / filename

        filepath.write_bytes(image_data)
        return filepath

    async def get_session_screenshots(self, session_name: str) -> list[Path]:
        """
        Get all screenshots for a session.

        Args:
            session_name: Session name

        Returns:
            List of screenshot paths
        """
        screenshots_dir = self.data_dir / "screenshots" / session_name
        if not screenshots_dir.exists():
            return []

        return sorted(screenshots_dir.glob("*.png"))

    async def export_session(
        self,
        session_name: str,
        output_path: Path,
        include_screenshots: bool = True
    ) -> Path:
        """
        Export a session to a single archive.

        Args:
            session_name: Session name
            output_path: Path for output archive
            include_screenshots: Whether to include screenshots

        Returns:
            Path to created archive
        """
        import shutil
        import tempfile

        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy session file
            session_path = self._session_path(session_name)
            if session_path.exists():
                shutil.copy(session_path, temp_path / "session.json")

            # Copy results if exists
            results_path = self.data_dir / "results" / f"{session_name}.json"
            if results_path.exists():
                shutil.copy(results_path, temp_path / "results.json")

            results_md = self.data_dir / "results" / f"{session_name}.md"
            if results_md.exists():
                shutil.copy(results_md, temp_path / "results.md")

            # Copy screenshots
            if include_screenshots:
                screenshots_dir = self.data_dir / "screenshots" / session_name
                if screenshots_dir.exists():
                    shutil.copytree(screenshots_dir, temp_path / "screenshots")

            # Create archive
            archive_path = shutil.make_archive(
                str(output_path.with_suffix('')),
                'zip',
                temp_path
            )

            return Path(archive_path)

    async def import_session(self, archive_path: Path) -> str:
        """
        Import a session from an archive.

        Args:
            archive_path: Path to archive file

        Returns:
            Imported session name
        """
        import shutil
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract archive
            shutil.unpack_archive(archive_path, temp_path)

            # Read session data
            session_path = temp_path / "session.json"
            if not session_path.exists():
                raise ValueError("Invalid archive: no session.json found")

            session = json.loads(session_path.read_text())
            session_name = session.get("id", archive_path.stem)

            # Copy session file
            shutil.copy(session_path, self._session_path(session_name))

            # Copy results
            results_path = temp_path / "results.json"
            if results_path.exists():
                results_dir = self.data_dir / "results"
                results_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy(results_path, results_dir / f"{session_name}.json")

            results_md = temp_path / "results.md"
            if results_md.exists():
                shutil.copy(results_md, self.data_dir / "results" / f"{session_name}.md")

            # Copy screenshots
            screenshots_path = temp_path / "screenshots"
            if screenshots_path.exists():
                dest = self.data_dir / "screenshots" / session_name
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(screenshots_path, dest)

            return session_name
