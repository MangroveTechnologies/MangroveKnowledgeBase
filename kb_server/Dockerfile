# MangroveKnowledgeBase KB Server Dockerfile
# Trading Knowledge Base Document Server with Full-Text Search
#
# Build context should be the MangroveKnowledgeBase repo root:
#   docker build -f kb_server/Dockerfile -t mangrove-kb .

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install the mangrove_knowledge_base signals/indicators package
COPY pyproject.toml README.md ./
COPY mangrove_knowledge_base/ ./mangrove_knowledge_base/
RUN pip install --no-cache-dir -e .

# Copy kb_server requirements and install
COPY kb_server/requirements.txt /tmp/kb-requirements.txt
RUN pip install --no-cache-dir -r /tmp/kb-requirements.txt

# Copy the kb_server application code
COPY kb_server/ ./kb_server/

# Create data directory for SQLite database
RUN mkdir -p /app/kb_server/data

# Copy the knowledge-base markdown files
COPY knowledge-base/ /kb/

# Set environment variables for paths
ENV KB_SERVER_KB_PATH=/kb \
    KB_SERVER_DB_PATH=/app/kb_server/data/knowledge.db \
    KB_SERVER_PORT=8080 \
    KB_SERVER_HOST=0.0.0.0 \
    PYTHONPATH=/app

# Expose the port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/status')" || exit 1

# Default command: Initialize DB and start server
CMD ["sh", "-c", "cd /app/kb_server && python init_db.py --force && cd /app && python -m uvicorn kb_server.main:app --host 0.0.0.0 --port 8080"]
