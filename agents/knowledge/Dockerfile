FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY agents/knowledge/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared/ ./shared/

# Copy agent code
COPY agents/knowledge/ ./agents/knowledge/

# Create data directory
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

# Run the server
CMD ["python", "-m", "agents.knowledge.a2a_server"]
