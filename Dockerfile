# Multi-stage or optimized Debian slim base for Python 3.12
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered output for real-time logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies:
# - curl: for container healthchecks
# - gcc, g++, libpq-dev: for C-extensions (psycopg2, fast numeric libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Ensure required runtime storage directories exist
RUN mkdir -p /app/data/tenants \
             /app/data/knowledge \
             /app/data/vectorstore \
             /app/data/prescriptions \
             /app/data/invoices \
             /app/logs

# Fix line endings and make entrypoint script executable
RUN tr -d '\r' < /app/entrypoint.sh > /app/entrypoint_unix.sh && \
    mv /app/entrypoint_unix.sh /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Expose FastAPI application port
EXPOSE 8000

# Healthcheck against /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]

