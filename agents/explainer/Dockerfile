FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY agents/explainer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared/ ./shared/

# Copy agent code
COPY agents/explainer/ ./agents/explainer/

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the server
CMD ["python", "-m", "agents.explainer.a2a_server"]
