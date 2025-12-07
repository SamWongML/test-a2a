FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files for dependency installation
COPY agents/knowledge/pyproject.toml ./agents/knowledge/

# Copy shared utilities
COPY shared/ ./shared/

# Copy agent code
COPY agents/knowledge/ ./agents/knowledge/

# Create data directory
RUN mkdir -p /app/data

# Install dependencies using uv sync
RUN cd agents/knowledge && uv sync --frozen --no-dev

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/agents/knowledge/.venv/bin:$PATH"

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the server
CMD ["python", "-m", "agents.knowledge.a2a_server"]
