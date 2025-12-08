"""A2A Server for the Explainer agent."""

import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .agent import ExplainerAgent
from .config import get_settings

sys.path.insert(0, "/app")
from shared.a2a_utils import create_a2a_error, create_a2a_response, create_agent_card
from shared.logging_config import setup_logging
from shared.token_manager import TokenManager

# Set up logging first
settings = get_settings()
logger = setup_logging("explainer-agent", level="INFO")

app = FastAPI(title="Explainer Agent", version="1.0.0")

# Initialize TokenManager before agent creation
TokenManager.initialize(settings)

logger.info("Initializing Explainer Agent...")
agent = ExplainerAgent()
logger.info("Explainer Agent initialized successfully")


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
    body = None
    try:
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {})
        request_id = body.get("id", "1")

        logger.info(f"Received A2A request: method={method}, id={request_id}")

        if method == "tasks/send":
            # Extract the message text
            message = params.get("message", {})
            parts = message.get("parts", [])
            query = parts[0].get("text", "") if parts else ""

            if not query:
                logger.warning(f"Request {request_id}: Missing query text in params")
                return JSONResponse(
                    create_a2a_error(-32602, "Invalid params: missing query text", request_id)
                )

            logger.info(f"Processing query: {query[:100]}...")

            # Parse for context (from orchestrator)
            context = ""
            if "\n\nContext from research:" in query:
                query_parts = query.split("\n\nContext from research:", 1)
                query = query_parts[0]
                context = query_parts[1] if len(query_parts) > 1 else ""
                logger.debug(f"Extracted context from research: {len(context)} chars")

            # Generate explanation
            logger.debug("Generating explanation...")
            result = await agent.quick_explain(query)

            logger.info(f"Request {request_id}: Completed successfully")

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
            logger.warning(f"Request {request_id}: Unknown method '{method}'")
            return JSONResponse(create_a2a_error(-32601, f"Method not found: {method}", request_id))

    except Exception as e:
        request_id = body.get("id", "1") if body else "1"
        error_msg = f"Internal error: {str(e)}"
        logger.error(f"Request {request_id}: {error_msg}", exc_info=True)
        return JSONResponse(create_a2a_error(-32603, error_msg, request_id))


def main():
    """Run the A2A server."""
    logger.info(f"Starting Explainer Agent on {settings.host}:{settings.port}")
    uvicorn.run(
        "agents.explainer.a2a_server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
