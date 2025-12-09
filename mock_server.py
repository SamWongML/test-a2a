"""Standalone mock SSE server for testing frontend event handlers."""

import asyncio
import json
from typing import Optional  # noqa: F401 - may be used for type hints

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

app = FastAPI(title="Mock SSE Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def format_event(event_type: str, payload: dict) -> str:
    return f"data: {json.dumps({'type': event_type, 'payload': payload})}\n\n"


async def mock_stream_generator(query: str):
    """Generate mock SSE events for testing all frontend event handlers."""

    # === 1. Query Analysis ===
    yield format_event("agent_start", {"agent": "router"})
    yield format_event(
        "message",
        {"from": "user", "to": "router", "content": f"Query: {query[:60]}..."},
    )
    await asyncio.sleep(0.3)

    yield format_event(
        "message",
        {
            "from": "router",
            "to": "agents",
            "content": "Dispatching to: knowledge, research, explainer",
        },
    )
    await asyncio.sleep(0.2)

    # === 2. Knowledge Agent ===
    yield format_event("agent_start", {"agent": "knowledge"})
    yield format_event(
        "message",
        {"from": "router", "to": "knowledge", "content": f"Search: {query[:40]}..."},
    )
    await asyncio.sleep(0.3)

    knowledge_chunks = [
        "Found 3 relevant documents:\n",
        "• AI Agent Architectures\n",
        "• Multi-Agent Systems\n",
        "• LLM Integration Patterns",
    ]
    for chunk in knowledge_chunks:
        yield format_event("agent_output", {"agent": "knowledge", "content": chunk})
        await asyncio.sleep(0.1)

    yield format_event("agent_complete", {"agent": "knowledge", "duration": 0.8, "tokens": 156})
    yield format_event(
        "message",
        {"from": "knowledge", "to": "synthesizer", "content": "Found 3 documents"},
    )
    await asyncio.sleep(0.2)

    # === 3. Research Agent ===
    yield format_event("agent_start", {"agent": "research"})
    yield format_event(
        "message",
        {"from": "router", "to": "research", "content": f"Research: {query[:40]}..."},
    )
    await asyncio.sleep(0.2)

    yield format_event(
        "tool_call",
        {"agent": "research", "name": "web_search", "input": {"query": query[:30]}},
    )
    await asyncio.sleep(0.4)

    yield format_event(
        "tool_result",
        {"agent": "research", "name": "web_search", "output": "Found 5 relevant sources"},
    )
    await asyncio.sleep(0.2)

    yield format_event(
        "tool_call",
        {"agent": "research", "name": "github_search", "input": {"topic": "AI agents"}},
    )
    await asyncio.sleep(0.3)

    yield format_event(
        "tool_result",
        {"agent": "research", "name": "github_search", "output": "Found 12 repositories"},
    )
    await asyncio.sleep(0.2)

    research_chunks = [
        "## Research Findings\n\n",
        "**Web Sources:** 5 papers analyzed\n",
        "**GitHub:** 12 repos reviewed\n\n",
        "Key frameworks: CrewAI, LangGraph, AutoGPT\n",
        "Trend: Multi-agent collaboration\n",
    ]
    for chunk in research_chunks:
        yield format_event("agent_output", {"agent": "research", "content": chunk})
        await asyncio.sleep(0.1)

    yield format_event("agent_complete", {"agent": "research", "duration": 2.3, "tokens": 487})
    yield format_event(
        "message",
        {
            "from": "research",
            "to": "synthesizer",
            "content": "Research complete: 5 sources, 12 repos",
        },
    )
    await asyncio.sleep(0.2)

    # === 4. Explainer Agent ===
    yield format_event("agent_start", {"agent": "explainer"})
    yield format_event(
        "message",
        {
            "from": "router",
            "to": "explainer",
            "content": "Generate explanation with code examples",
        },
    )
    await asyncio.sleep(0.2)

    yield format_event(
        "tool_call",
        {"agent": "explainer", "name": "context7_lookup", "input": {"topic": "AI agents"}},
    )
    await asyncio.sleep(0.3)

    yield format_event(
        "tool_result",
        {"agent": "explainer", "name": "context7_lookup", "output": "Documentation retrieved"},
    )
    await asyncio.sleep(0.2)

    explainer_chunks = [
        "## AI Agents Explained\n\n",
        "AI agents are systems that can:\n",
        "• **Perceive**: Understand context\n",
        "• **Reason**: Make LLM decisions\n",
        "• **Act**: Execute via tools\n\n",
        "```python\n",
        "from crewai import Agent\n",
        "agent = Agent(role='Researcher')\n",
        "```",
    ]
    for chunk in explainer_chunks:
        yield format_event("agent_output", {"agent": "explainer", "content": chunk})
        await asyncio.sleep(0.08)

    yield format_event("agent_complete", {"agent": "explainer", "duration": 1.8, "tokens": 623})
    yield format_event(
        "message",
        {
            "from": "explainer",
            "to": "synthesizer",
            "content": "Explanation ready with code examples",
        },
    )
    await asyncio.sleep(0.2)

    # === 5. Synthesis ===
    yield format_event("agent_start", {"agent": "synthesizer"})
    yield format_event(
        "message",
        {"from": "synthesizer", "to": "user", "content": "Combining all responses..."},
    )
    await asyncio.sleep(0.2)

    synthesis_chunks = [
        "## Synthesis\n\n",
        "**Sources analyzed:**\n",
        "• Knowledge: 3 docs\n",
        "• Research: 5 web + 12 repos\n",
        "• Explainer: Technical breakdown\n\n",
        "**Quality checks:** ✓ All passed\n",
    ]
    for chunk in synthesis_chunks:
        yield format_event("agent_output", {"agent": "synthesizer", "content": chunk})
        await asyncio.sleep(0.08)

    yield format_event("agent_complete", {"agent": "synthesizer", "duration": 4.5, "tokens": 1266})
    yield format_event("agent_complete", {"agent": "router", "duration": 0.5, "tokens": 120})
    await asyncio.sleep(0.1)

    # === 6. Final Response ===
    answer = f"""# Response to: {query}

## Key Insights

1. **Knowledge Base**: Found 3 relevant documents on AI architectures
2. **Research**: Analyzed 5 web sources and 12 GitHub repositories
3. **Explanation**: Detailed technical breakdown with code examples

## Summary

AI agents are autonomous systems using LLMs for reasoning and tools for action. 
Popular frameworks include CrewAI, LangGraph, and PydanticAI.

---
*Generated by Multi-Agent A2A System*"""

    yield format_event(
        "complete",
        {
            "answer": answer,
            "sources": [
                "https://docs.crewai.com",
                "https://langchain-ai.github.io/langgraph",
                "https://github.com/pydantic/pydantic-ai",
            ],
            "agents_used": ["knowledge", "research", "explainer", "orchestrator"],
            "duration": 4.5,
        },
    )


@app.post("/stream")
@app.post("/stream/mock")
async def mock_stream(request: Request):
    """Mock SSE stream for testing frontend."""
    try:
        body = await request.json()
        query = body.get("query", "Tell me about AI agents")
    except Exception:
        query = "Tell me about AI agents"

    print(f"Starting mock stream for: {query[:50]}...")

    return StreamingResponse(
        mock_stream_generator(query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "mock-server"}


if __name__ == "__main__":
    print("Starting Mock SSE Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
