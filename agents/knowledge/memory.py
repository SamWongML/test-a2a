"""Session memory for maintaining conversation context."""

import json
import os
from datetime import datetime
from typing import Any


class SessionMemory:
    """Simple session memory for maintaining conversation context."""

    def __init__(self, storage_path: str = "./data/sessions"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def _get_session_file(self, session_id: str) -> str:
        """Get the file path for a session."""
        return os.path.join(self.storage_path, f"{session_id}.json")

    def load_session(self, session_id: str) -> list[dict[str, Any]]:
        """Load a session from disk."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        filepath = self._get_session_file(session_id)
        if os.path.exists(filepath):
            with open(filepath) as f:
                self._sessions[session_id] = json.load(f)
        else:
            self._sessions[session_id] = []

        return self._sessions[session_id]

    def save_session(self, session_id: str) -> None:
        """Save a session to disk."""
        if session_id not in self._sessions:
            return

        filepath = self._get_session_file(session_id)
        with open(filepath, "w") as f:
            json.dump(self._sessions[session_id], f, indent=2)

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add a message to session memory."""
        session = self.load_session(session_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

        session.append(message)
        self._sessions[session_id] = session
        self.save_session(session_id)

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get recent messages from a session."""
        session = self.load_session(session_id)
        return session[-limit:]

    def get_context_summary(self, session_id: str) -> str:
        """Get a summary of the session context."""
        messages = self.get_recent_messages(session_id, limit=5)
        if not messages:
            return "No previous conversation context."

        summary_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:200]
            summary_parts.append(f"{role}: {content}")

        return "\n".join(summary_parts)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]

        filepath = self._get_session_file(session_id)
        if os.path.exists(filepath):
            os.remove(filepath)
