"""A2A Server for the Orchestrator agent."""

import sys

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .orchestrator import OrchestratorAgent
from .streaming import StreamingOrchestrator

sys.path.insert(0, "/app")
from shared.a2a_utils import create_a2a_error, create_a2a_response, create_agent_card
from shared.logging_config import setup_logging
from shared.token_manager import TokenManager

# Set up logging first
settings = get_settings()
logger = setup_logging("orchestrator-agent", level="INFO")

app = FastAPI(title="Orchestrator Agent", version="1.0.0")

# Add CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize TokenManager before agent creation
TokenManager.initialize(settings)

logger.info("Initializing Orchestrator Agent...")
agent = OrchestratorAgent()
streaming_orchestrator = StreamingOrchestrator()
logger.info("Orchestrator Agent initialized successfully")


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

            # Run the orchestrator workflow
            logger.debug("Running orchestrator workflow...")
            result = await agent.run(query)

            logger.info(
                f"Request {request_id}: Completed successfully, used agents: {result.agents_used}"
            )

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
            logger.debug(f"Request {request_id}: Getting task status for {task_id}")
            return JSONResponse(
                create_a2a_response({"status": "completed", "task_id": task_id}, request_id)
            )

        else:
            logger.warning(f"Request {request_id}: Unknown method '{method}'")
            return JSONResponse(create_a2a_error(-32601, f"Method not found: {method}", request_id))

    except Exception as e:
        request_id = body.get("id", "1") if body else "1"
        error_msg = f"Internal error: {str(e)}"
        logger.error(f"Request {request_id}: {error_msg}", exc_info=True)
        return JSONResponse(create_a2a_error(-32603, error_msg, request_id))


@app.post("/stream")
async def stream_a2a_request(request: Request):
    """Stream A2A responses via Server-Sent Events (SSE)."""
    try:
        body = await request.json()
        query = ""

        # Support both direct query and A2A format
        if "query" in body:
            query = body["query"]
        elif "params" in body:
            message = body.get("params", {}).get("message", {})
            parts = message.get("parts", [])
            query = parts[0].get("text", "") if parts else ""

        if not query:
            return JSONResponse({"error": "Missing query"}, status_code=400)

        logger.info(f"Starting SSE stream for query: {query[:100]}...")

        return StreamingResponse(
            streaming_orchestrator.stream(query),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.error(f"Stream error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


def main():
    """Run the A2A server."""
    logger.info(f"Starting Orchestrator Agent on {settings.host}:{settings.port}")
    uvicorn.run(
        "agents.orchestrator.a2a_server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
