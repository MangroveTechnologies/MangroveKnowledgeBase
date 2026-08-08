FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml PKG_README.md ./
COPY mangrove_kb/ ./mangrove_kb/

RUN pip install --no-cache-dir -e ".[dev]"

COPY tests/ ./tests/

# Default: run tests
CMD ["pytest", "tests/", "-v"]
