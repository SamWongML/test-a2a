"""A2A Server for the Orchestrator agent."""

import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .agent import OrchestratorAgent
from .config import get_settings

sys.path.insert(0, "/app")
from shared.a2a_utils import create_a2a_error, create_a2a_response, create_agent_card

app = FastAPI(title="Orchestrator Agent", version="1.0.0")
settings = get_settings()
agent = OrchestratorAgent()


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Return the A2A Agent Card for discovery."""
    card = create_agent_card(
        name=settings.agent_name,
        description=settings.agent_description,
        url=f"http://localhost:{settings.port}",
        skills=[
            {
                "id": "route-query",
                "name": "Route Query",
                "description": "Analyzes user queries and routes to appropriate agents",
            },
            {
                "id": "synthesize-response",
                "name": "Synthesize Response",
                "description": "Combines responses from multiple agents into coherent answer",
            },
        ],
    )
    return card.model_dump()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "agent": settings.agent_name}


@app.post("/a2a")
async def handle_a2a_request(request: Request):
    """Handle A2A JSON-RPC requests."""
    try:
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {})
        request_id = body.get("id", "1")

        if method == "tasks/send":
            # Extract the message text
            message = params.get("message", {})
            parts = message.get("parts", [])
            query = parts[0].get("text", "") if parts else ""

            if not query:
                return JSONResponse(
                    create_a2a_error(-32602, "Invalid params: missing query text", request_id)
                )

            # Run the orchestrator workflow
            result = await agent.run(query)

            return JSONResponse(
                create_a2a_response(
                    {
                        "message": {
                            "role": "assistant",
                            "parts": [{"text": result.answer}],
                        },
                        "metadata": {
                            "sources": result.sources,
                            "agents_used": result.agents_used,
                        },
                    },
                    request_id,
                )
            )

        elif method == "tasks/get":
            # Return task status (simplified)
            task_id = params.get("id", "")
            return JSONResponse(
                create_a2a_response({"status": "completed", "task_id": task_id}, request_id)
            )

        else:
            return JSONResponse(create_a2a_error(-32601, f"Method not found: {method}", request_id))

    except Exception as e:
        return JSONResponse(
            create_a2a_error(-32603, f"Internal error: {str(e)}", body.get("id", "1"))
        )


def main():
    """Run the A2A server."""
    uvicorn.run(
        "agents.orchestrator.a2a_server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
