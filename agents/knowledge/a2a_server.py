"""A2A Server for the Knowledge Manager agent."""

import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .agent import KnowledgeAgent
from .config import get_settings

sys.path.insert(0, "/app")
from shared.a2a_utils import create_a2a_error, create_a2a_response, create_agent_card

app = FastAPI(title="Knowledge Manager Agent", version="1.0.0")
settings = get_settings()
agent = KnowledgeAgent()


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Return the A2A Agent Card for discovery."""
    card = create_agent_card(
        name=settings.agent_name,
        description=settings.agent_description,
        url=f"http://localhost:{settings.port}",
        skills=[
            {
                "id": "store-knowledge",
                "name": "Store Knowledge",
                "description": "Store research findings and explanations",
            },
            {
                "id": "search-knowledge",
                "name": "Search Knowledge",
                "description": "Search for relevant past information",
            },
            {
                "id": "get-context",
                "name": "Get Context",
                "description": "Get conversation context for a session",
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

            # Extract session ID if provided
            session_id = params.get("session_id", "default")

            # Process the request
            result = await agent.process(query, session_id)

            return JSONResponse(
                create_a2a_response(
                    {
                        "message": {
                            "role": "assistant",
                            "parts": [{"text": result}],
                        },
                    },
                    request_id,
                )
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
        "agents.knowledge.a2a_server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
