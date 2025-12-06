"""A2A protocol utilities for all agents."""

import json
from typing import Any

import httpx
from pydantic import BaseModel


class AgentSkill(BaseModel):
    """A2A Agent Skill definition."""

    id: str
    name: str
    description: str


class AgentCapabilities(BaseModel):
    """A2A Agent capabilities."""

    streaming: bool = True
    push_notifications: bool = False


class AgentCard(BaseModel):
    """A2A Agent Card for discovery."""

    name: str
    version: str
    description: str
    url: str
    capabilities: AgentCapabilities = AgentCapabilities()
    skills: list[AgentSkill] = []


def create_agent_card(
    name: str,
    description: str,
    url: str,
    skills: list[dict[str, str]],
    version: str = "1.0.0",
) -> AgentCard:
    """Create an A2A Agent Card."""
    return AgentCard(
        name=name,
        version=version,
        description=description,
        url=url,
        skills=[AgentSkill(**skill) for skill in skills],
    )


class A2AClient:
    """Client for calling other A2A agents."""

    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def get_agent_card(self) -> AgentCard | None:
        """Discover agent capabilities via Agent Card."""
        try:
            response = await self._client.get(f"{self.base_url}/.well-known/agent.json")
            response.raise_for_status()
            return AgentCard(**response.json())
        except Exception:
            return None

    async def send_task(
        self,
        message: str,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a task to the agent using A2A protocol."""
        payload = {
            "jsonrpc": "2.0",
            "method": "tasks/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"text": message}],
                }
            },
            "id": task_id or "1",
        }

        response = await self._client.post(
            f"{self.base_url}/a2a",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


def create_a2a_response(
    result: str | dict[str, Any],
    request_id: str = "1",
) -> dict[str, Any]:
    """Create a JSON-RPC 2.0 response."""
    if isinstance(result, str):
        result = {
            "message": {
                "role": "assistant",
                "parts": [{"text": result}],
            }
        }
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": request_id,
    }


def create_a2a_error(
    code: int,
    message: str,
    request_id: str = "1",
) -> dict[str, Any]:
    """Create a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": code,
            "message": message,
        },
        "id": request_id,
    }
