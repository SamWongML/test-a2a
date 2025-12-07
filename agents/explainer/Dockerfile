FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files for dependency installation
COPY agents/explainer/pyproject.toml ./agents/explainer/

# Copy shared utilities
COPY shared/ ./shared/

# Copy agent code
COPY agents/explainer/ ./agents/explainer/

# Install dependencies using uv sync
RUN cd agents/explainer && uv sync --frozen --no-dev

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PATH="/app/agents/explainer/.venv/bin:$PATH"

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the server
CMD ["python", "-m", "agents.explainer.a2a_server"]
