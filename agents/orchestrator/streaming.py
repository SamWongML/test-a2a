"""Streaming orchestrator for SSE events."""

import json
import logging
import sys
import time
from collections.abc import AsyncGenerator

from .config import get_settings
from .router import AgentType, QueryRouter
from .synthesizer import AgentResponse, ResponseSynthesizer

sys.path.insert(0, "/app")
from shared.a2a_utils import A2AClient

logger = logging.getLogger("orchestrator-agent")


class StreamingOrchestrator:
    """Orchestrator that streams events during workflow execution."""

    def __init__(self):
        self.settings = get_settings()
        self.router = QueryRouter(settings=self.settings)
        self.synthesizer = ResponseSynthesizer(settings=self.settings)

    async def stream(self, query: str) -> AsyncGenerator[str, None]:
        """Stream events during workflow execution."""
        start_time = time.time()

        try:
            # Emit start event
            yield self._format_event(
                "agent_start",
                {"agent": "orchestrator", "message": "Analyzing query and routing to agents..."},
            )

            # Route the query
            routing = await self.router.route(query)
            yield self._format_event(
                "message",
                {
                    "from": "orchestrator",
                    "to": "router",
                    "content": f"Query classified, routing to: {[a.value for a in routing.agents]}",
                },
            )

            agent_responses: list[AgentResponse] = []

            # Check knowledge first if needed
            if routing.check_knowledge_first:
                async for event in self._call_knowledge(query):
                    yield event
                    if event and "agent_complete" in event:
                        try:
                            data = json.loads(event.split("data: ")[1])
                            if data.get("payload", {}).get("content"):
                                agent_responses.append(
                                    AgentResponse(
                                        agent_name="knowledge", content=data["payload"]["content"]
                                    )
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            # Call research agent if needed
            if AgentType.RESEARCH in routing.agents:
                async for event in self._call_research(query):
                    yield event
                    if event and "agent_complete" in event:
                        try:
                            data = json.loads(event.split("data: ")[1])
                            if data.get("payload", {}).get("content"):
                                agent_responses.append(
                                    AgentResponse(
                                        agent_name="research", content=data["payload"]["content"]
                                    )
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            # Call explainer agent if needed
            if AgentType.EXPLAINER in routing.agents:
                research_context = next(
                    (r.content for r in agent_responses if r.agent_name == "research"), ""
                )
                async for event in self._call_explainer(query, research_context):
                    yield event
                    if event and "agent_complete" in event:
                        try:
                            data = json.loads(event.split("data: ")[1])
                            if data.get("payload", {}).get("content"):
                                agent_responses.append(
                                    AgentResponse(
                                        agent_name="explainer", content=data["payload"]["content"]
                                    )
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            # Synthesize response
            yield self._format_event(
                "agent_start",
                {"agent": "orchestrator", "message": "Synthesizing final response..."},
            )

            final_response = await self.synthesizer.synthesize(query, agent_responses)

            duration = round(time.time() - start_time, 1)
            yield self._format_event(
                "agent_complete", {"agent": "orchestrator", "duration": duration}
            )

            yield self._format_event(
                "complete",
                {
                    "answer": final_response.answer,
                    "sources": final_response.sources,
                    "agents_used": final_response.agents_used,
                    "duration": duration,
                },
            )

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield self._format_event("error", {"agent": "orchestrator", "message": str(e)})

    async def _call_knowledge(self, query: str) -> AsyncGenerator[str, None]:
        """Call knowledge agent and stream events."""
        yield self._format_event(
            "agent_start", {"agent": "knowledge", "message": "Searching knowledge base..."}
        )
        yield self._format_event(
            "message",
            {"from": "orchestrator", "to": "knowledge", "content": f"Search for: {query[:100]}..."},
        )

        start_time = time.time()
        try:
            async with A2AClient(self.settings.knowledge_agent_url) as client:
                result = await client.send_task(f"Search for relevant information about: {query}")
                content = self._extract_content(result)

                yield self._format_event(
                    "agent_output",
                    {
                        "agent": "knowledge",
                        "content": content[:500] + "..." if len(content) > 500 else content,
                    },
                )

                duration = round(time.time() - start_time, 1)
                yield self._format_event(
                    "agent_complete",
                    {"agent": "knowledge", "duration": duration, "content": content},
                )
                yield self._format_event(
                    "message",
                    {"from": "knowledge", "to": "orchestrator", "content": "Search complete"},
                )
        except Exception as e:
            yield self._format_event("error", {"agent": "knowledge", "message": str(e)})

    async def _call_research(self, query: str) -> AsyncGenerator[str, None]:
        """Call research agent and stream events."""
        yield self._format_event(
            "agent_start", {"agent": "research", "message": "Initiating AI research..."}
        )
        yield self._format_event(
            "message",
            {"from": "orchestrator", "to": "research", "content": f"Research: {query[:100]}..."},
        )

        # Simulate tool calls for demonstration
        yield self._format_event(
            "tool_call",
            {"agent": "research", "name": "firecrawl_search", "input": {"query": query[:50]}},
        )

        start_time = time.time()
        try:
            async with A2AClient(self.settings.research_agent_url) as client:
                result = await client.send_task(query)
                content = self._extract_content(result)

                yield self._format_event(
                    "tool_result",
                    {
                        "agent": "research",
                        "name": "firecrawl_search",
                        "output": "Results retrieved successfully",
                    },
                )

                yield self._format_event(
                    "agent_output",
                    {
                        "agent": "research",
                        "content": content[:500] + "..." if len(content) > 500 else content,
                    },
                )

                duration = round(time.time() - start_time, 1)
                yield self._format_event(
                    "agent_complete",
                    {"agent": "research", "duration": duration, "content": content},
                )
                yield self._format_event(
                    "message",
                    {"from": "research", "to": "orchestrator", "content": "Research complete"},
                )
        except Exception as e:
            yield self._format_event("error", {"agent": "research", "message": str(e)})

    async def _call_explainer(self, query: str, context: str) -> AsyncGenerator[str, None]:
        """Call explainer agent and stream events."""
        yield self._format_event(
            "agent_start", {"agent": "explainer", "message": "Generating explanation..."}
        )
        yield self._format_event(
            "message",
            {
                "from": "orchestrator",
                "to": "explainer",
                "content": f"Explain: {query[:50]}... with context",
            },
        )

        yield self._format_event(
            "tool_call",
            {"agent": "explainer", "name": "context7_lookup", "input": {"topic": query[:50]}},
        )

        start_time = time.time()
        try:
            full_query = f"{query}\n\nContext from research:\n{context}"
            async with A2AClient(self.settings.explainer_agent_url) as client:
                result = await client.send_task(full_query)
                content = self._extract_content(result)

                yield self._format_event(
                    "tool_result",
                    {
                        "agent": "explainer",
                        "name": "context7_lookup",
                        "output": "Documentation retrieved",
                    },
                )

                yield self._format_event(
                    "agent_output",
                    {
                        "agent": "explainer",
                        "content": content[:500] + "..." if len(content) > 500 else content,
                    },
                )

                duration = round(time.time() - start_time, 1)
                yield self._format_event(
                    "agent_complete",
                    {"agent": "explainer", "duration": duration, "content": content},
                )
                yield self._format_event(
                    "message",
                    {"from": "explainer", "to": "orchestrator", "content": "Explanation complete"},
                )
        except Exception as e:
            yield self._format_event("error", {"agent": "explainer", "message": str(e)})

    def _extract_content(self, result: dict) -> str:
        """Extract content from A2A response."""
        try:
            parts = result.get("result", {}).get("message", {}).get("parts", [])
            return parts[0].get("text", "") if parts else ""
        except Exception:
            return str(result)

    def _format_event(self, event_type: str, payload: dict) -> str:
        """Format event as SSE data."""
        event = {"type": event_type, "payload": payload}
        return f"data: {json.dumps(event)}\n\n"
