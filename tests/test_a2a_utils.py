"""Tests for A2A utilities."""

import pytest

from shared.a2a_utils import (
    AgentCard,
    AgentSkill,
    create_a2a_error,
    create_a2a_response,
    create_agent_card,
)


def test_create_agent_card():
    """Test creating an agent card."""
    card = create_agent_card(
        name="test-agent",
        description="A test agent",
        url="http://localhost:8000",
        skills=[{"id": "skill-1", "name": "Test Skill", "description": "A test skill"}],
    )

    assert card.name == "test-agent"
    assert card.description == "A test agent"
    assert card.url == "http://localhost:8000"
    assert len(card.skills) == 1
    assert card.skills[0].id == "skill-1"


def test_create_a2a_response():
    """Test creating an A2A response."""
    response = create_a2a_response("Hello, world!", "123")

    assert response["jsonrpc"] == "2.0"
    assert response["id"] == "123"
    assert "result" in response
    assert response["result"]["message"]["parts"][0]["text"] == "Hello, world!"


def test_create_a2a_error():
    """Test creating an A2A error response."""
    error = create_a2a_error(-32600, "Invalid request", "456")

    assert error["jsonrpc"] == "2.0"
    assert error["id"] == "456"
    assert error["error"]["code"] == -32600
    assert error["error"]["message"] == "Invalid request"
