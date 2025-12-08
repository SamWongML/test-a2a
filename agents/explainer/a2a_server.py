"""A2A Server for the Explainer agent."""

import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .agent import ExplainerAgent
from .config import get_settings

sys.path.insert(0, "/app")
from shared.a2a_utils import create_a2a_error, create_a2a_response, create_agent_card
from shared.token_manager import TokenManager

app = FastAPI(title="Explainer Agent", version="1.0.0")
settings = get_settings()

# Initialize TokenManager before agent creation
TokenManager.initialize(settings)

agent = ExplainerAgent()


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """Return the A2A Agent Card for discovery."""
    card = create_agent_card(
        name=settings.agent_name,
        description=settings.agent_description,
        url=f"http://localhost:{settings.port}",
        skills=[
            {
                "id": "explain-technology",
                "name": "Explain Technology",
                "description": "Provide detailed explanations with code examples",
            },
            {
                "id": "code-snippets",
                "name": "Code Snippets",
                "description": "Generate practical code examples for technologies",
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

            # Parse for context (from orchestrator)
            context = ""
            if "\n\nContext from research:" in query:
                parts = query.split("\n\nContext from research:", 1)
                query = parts[0]
                context = parts[1] if len(parts) > 1 else ""

            # Generate explanation
            result = await agent.quick_explain(query)

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
        "agents.explainer.a2a_server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
