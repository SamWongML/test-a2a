# Multi-Agent A2A System

A microservice-based multi-agent AI system featuring intelligent orchestration, research capabilities, technology explanation, and persistent knowledge management—all communicating via the A2A protocol and powered by Azure OpenAI.

## Architecture

| Agent            | Framework  | Port | Description                                               |
| ---------------- | ---------- | ---- | --------------------------------------------------------- |
| **Orchestrator** | LangGraph  | 8000 | Routes queries, coordinates agents, synthesizes responses |
| **Research**     | CrewAI     | 8001 | Researches AI projects via Firecrawl and GitHub MCP       |
| **Explainer**    | PydanticAI | 8002 | Explains technologies with code snippets via Context7     |
| **Knowledge**    | Agno       | 8003 | Persistent memory, RAG, semantic search                   |

## Quick Start

```bash
# Copy environment template
cp .env.example .env
# Edit .env with your Azure OpenAI and API keys

# Start all services
docker compose up --build

# Test the system
curl -X POST http://localhost:8000/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tasks/send","params":{"message":{"role":"user","parts":[{"text":"What are the latest AI agent frameworks?"}]}},"id":"1"}'
```

## Environment Variables

| Variable                            | Required | Description                     |
| ----------------------------------- | -------- | ------------------------------- |
| `AZURE_OPENAI_ENDPOINT`             | Yes      | Azure OpenAI endpoint URL       |
| `AZURE_TENANT_ID`                   | Yes      | Azure Entra ID tenant ID        |
| `AZURE_CLIENT_ID`                   | Yes      | Azure Entra ID client ID        |
| `AZURE_CLIENT_SECRET`               | Yes      | Azure Entra ID client secret    |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Yes      | Embedding model deployment name |
| `FIRECRAWL_API_KEY`                 | Yes      | Firecrawl web search API        |
| `GITHUB_TOKEN`                      | Yes      | GitHub personal access token    |
| `CONTEXT7_API_KEY`                  | Yes      | Context7 documentation API      |

## Development

```bash
# Install all dependencies
pip install -e ".[all]"

# Run tests
pytest tests/ -v

# Lint
ruff check .
```

## License

MIT
