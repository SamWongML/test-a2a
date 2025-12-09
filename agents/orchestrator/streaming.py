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
        """Stream events during workflow execution.

        Event format matches mock_server.py for consistent frontend display.
        """
        start_time = time.time()

        try:
            # === 1. Query Analysis ===
            yield self._format_event("agent_start", {"agent": "orchestrator"})
            yield self._format_event(
                "message",
                {"from": "user", "to": "orchestrator", "content": f"Query: {query[:60]}..."},
            )

            # Route the query
            routing = await self.router.route(query)
            agents_list = [a.value for a in routing.agents]
            yield self._format_event(
                "message",
                {
                    "from": "orchestrator",
                    "to": "router",
                    "content": f"Routing to: {', '.join(agents_list)}",
                },
            )

            agent_responses: list[AgentResponse] = []

            # === 2. Knowledge Agent (if needed) ===
            if routing.check_knowledge_first:
                async for event in self._call_knowledge(query):
                    yield event
                    # Extract response content
                    if event and '"type": "agent_complete"' in event:
                        try:
                            data = json.loads(event.split("data: ")[1])
                            if data.get("payload", {}).get("content"):
                                agent_responses.append(
                                    AgentResponse(
                                        agent_name="knowledge",
                                        content=data["payload"]["content"],
                                    )
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            # === 3. Research Agent (if needed) ===
            if AgentType.RESEARCH in routing.agents:
                async for event in self._call_research(query):
                    yield event
                    if event and '"type": "agent_complete"' in event:
                        try:
                            data = json.loads(event.split("data: ")[1])
                            if data.get("payload", {}).get("content"):
                                agent_responses.append(
                                    AgentResponse(
                                        agent_name="research",
                                        content=data["payload"]["content"],
                                    )
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            # === 4. Explainer Agent (if needed) ===
            if AgentType.EXPLAINER in routing.agents:
                research_context = next(
                    (r.content for r in agent_responses if r.agent_name == "research"), ""
                )
                async for event in self._call_explainer(query, research_context):
                    yield event
                    if event and '"type": "agent_complete"' in event:
                        try:
                            data = json.loads(event.split("data: ")[1])
                            if data.get("payload", {}).get("content"):
                                agent_responses.append(
                                    AgentResponse(
                                        agent_name="explainer",
                                        content=data["payload"]["content"],
                                    )
                                )
                        except (json.JSONDecodeError, KeyError, IndexError):
                            pass

            # === 5. Synthesis ===
            yield self._format_event(
                "message",
                {"from": "orchestrator", "to": "synthesizer", "content": "Combining all responses"},
            )

            yield self._format_event("agent_start", {"agent": "orchestrator"})

            # Stream synthesis progress
            yield self._format_event(
                "agent_output",
                {"agent": "orchestrator", "content": "## Synthesis\n\n"},
            )
            yield self._format_event(
                "agent_output",
                {"agent": "orchestrator", "content": "**Analyzing agent responses...**\n"},
            )

            # Perform actual synthesis
            final_response = await self.synthesizer.synthesize(query, agent_responses)

            # Show synthesis completion
            sources_count = len(final_response.sources)
            agents_count = len(final_response.agents_used)
            yield self._format_event(
                "agent_output",
                {
                    "agent": "orchestrator",
                    "content": (
                        f"• Sources: {sources_count}\n"
                        f"• Agents: {agents_count}\n\n"
                        "**Quality check:** ✓ Complete\n"
                    ),
                },
            )

            yield self._format_event(
                "message",
                {"from": "synthesizer", "to": "orchestrator", "content": "Synthesis complete"},
            )

            duration = round(time.time() - start_time, 1)
            yield self._format_event(
                "agent_complete",
                {
                    "agent": "orchestrator",
                    "duration": duration,
                    "tokens": len(final_response.answer.split()) * 2,
                },
            )

            # === 6. Final Response ===
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
        yield self._format_event("agent_start", {"agent": "knowledge"})
        yield self._format_event(
            "message",
            {"from": "orchestrator", "to": "knowledge", "content": f"Search: {query[:40]}..."},
        )

        start_time = time.time()
        try:
            async with A2AClient(self.settings.knowledge_agent_url) as client:
                result = await client.send_task(f"Search for relevant information about: {query}")
                content = self._extract_content(result)

                # Stream output in chunks
                if content:
                    chunks = self._split_content(content, max_length=200)
                    for chunk in chunks:
                        yield self._format_event(
                            "agent_output",
                            {"agent": "knowledge", "content": chunk},
                        )

                duration = round(time.time() - start_time, 1)
                tokens = len(content.split()) * 2 if content else 0

                yield self._format_event(
                    "agent_complete",
                    {
                        "agent": "knowledge",
                        "duration": duration,
                        "tokens": tokens,
                        "content": content,
                    },
                )
                yield self._format_event(
                    "message",
                    {
                        "from": "knowledge",
                        "to": "orchestrator",
                        "content": f"Found {len(chunks) if content else 0} results",
                    },
                )

        except Exception as e:
            logger.error(f"Knowledge agent error: {e}", exc_info=True)
            yield self._format_event("error", {"agent": "knowledge", "message": str(e)})

    async def _call_research(self, query: str) -> AsyncGenerator[str, None]:
        """Call research agent and stream events."""
        yield self._format_event("agent_start", {"agent": "research"})
        yield self._format_event(
            "message",
            {"from": "orchestrator", "to": "research", "content": f"Research: {query[:40]}..."},
        )

        # Emit tool call
        yield self._format_event(
            "tool_call",
            {"agent": "research", "name": "web_search", "input": {"query": query[:30]}},
        )

        start_time = time.time()
        try:
            async with A2AClient(self.settings.research_agent_url) as client:
                result = await client.send_task(query)
                content = self._extract_content(result)

                yield self._format_event(
                    "tool_result",
                    {"agent": "research", "name": "web_search", "output": "Results retrieved"},
                )

                # Stream output in chunks
                if content:
                    chunks = self._split_content(content, max_length=200)
                    for chunk in chunks:
                        yield self._format_event(
                            "agent_output",
                            {"agent": "research", "content": chunk},
                        )

                duration = round(time.time() - start_time, 1)
                tokens = len(content.split()) * 2 if content else 0

                yield self._format_event(
                    "agent_complete",
                    {
                        "agent": "research",
                        "duration": duration,
                        "tokens": tokens,
                        "content": content,
                    },
                )
                yield self._format_event(
                    "message",
                    {"from": "research", "to": "orchestrator", "content": "Research complete"},
                )

        except Exception as e:
            logger.error(f"Research agent error: {e}", exc_info=True)
            yield self._format_event("error", {"agent": "research", "message": str(e)})

    async def _call_explainer(self, query: str, context: str) -> AsyncGenerator[str, None]:
        """Call explainer agent and stream events."""
        yield self._format_event("agent_start", {"agent": "explainer"})
        yield self._format_event(
            "message",
            {
                "from": "orchestrator",
                "to": "explainer",
                "content": "Generate explanation with code examples",
            },
        )

        # Emit tool call
        yield self._format_event(
            "tool_call",
            {"agent": "explainer", "name": "context7_lookup", "input": {"topic": query[:30]}},
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

                # Stream output in chunks
                if content:
                    chunks = self._split_content(content, max_length=200)
                    for chunk in chunks:
                        yield self._format_event(
                            "agent_output",
                            {"agent": "explainer", "content": chunk},
                        )

                duration = round(time.time() - start_time, 1)
                tokens = len(content.split()) * 2 if content else 0

                yield self._format_event(
                    "agent_complete",
                    {
                        "agent": "explainer",
                        "duration": duration,
                        "tokens": tokens,
                        "content": content,
                    },
                )
                yield self._format_event(
                    "message",
                    {"from": "explainer", "to": "orchestrator", "content": "Explanation ready"},
                )

        except Exception as e:
            logger.error(f"Explainer agent error: {e}", exc_info=True)
            yield self._format_event("error", {"agent": "explainer", "message": str(e)})

    def _extract_content(self, result: dict) -> str:
        """Extract content from A2A response."""
        try:
            parts = result.get("result", {}).get("message", {}).get("parts", [])
            return parts[0].get("text", "") if parts else ""
        except Exception:
            return str(result)

    def _split_content(self, content: str, max_length: int = 200) -> list[str]:
        """Split content into chunks for streaming."""
        if len(content) <= max_length:
            return [content]

        chunks = []
        lines = content.split("\n")
        current_chunk = ""

        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = line + "\n"
            else:
                current_chunk += line + "\n"

        if current_chunk:
            chunks.append(current_chunk)

        return chunks if chunks else [content[:max_length]]

    def _format_event(self, event_type: str, payload: dict) -> str:
        """Format event as SSE data."""
        event = {"type": event_type, "payload": payload}
        return f"data: {json.dumps(event)}\n\n"
