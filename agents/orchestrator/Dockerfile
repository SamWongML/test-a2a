FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files for dependency installation
COPY agents/orchestrator/pyproject.toml ./agents/orchestrator/

# Copy shared utilities
COPY shared/ ./shared/

# Copy agent code
COPY agents/orchestrator/ ./agents/orchestrator/

# Install dependencies using uv sync
RUN cd agents/orchestrator && uv sync --frozen --no-dev

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/agents/orchestrator/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the server
CMD ["python", "-m", "agents.orchestrator.a2a_server"]
