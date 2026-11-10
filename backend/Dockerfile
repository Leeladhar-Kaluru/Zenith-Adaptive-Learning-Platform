# ==============================================================================
# ZENITH Backend Containerization — Multi-Stage Dockerfile
# Base: Python 3.12-slim
# Target: Production Render Web Service / Cloud Container Runtimes
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build & Dependencies Isolation
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevent python from writing bytecode and disable pip cache during build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies for C-extension wheel compilations
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for clean isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency specifications first for Docker layer caching
COPY requirements.txt .

# Install production Python dependencies
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Minimal Production Runtime
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

# Production environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000 \
    APP_ENV=production

# Install minimal runtime libraries (libpq5 for PostgreSQL client, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root application user and group (least privilege principle)
RUN groupadd -g 10001 -r appuser && \
    useradd -u 10001 -r -g appuser -d /app -s /sbin/nologin -c "ZENITH Application User" appuser

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy Alembic database migration files and configuration
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini
COPY --chown=appuser:appuser alembic/ /app/alembic/

# Copy application source code and runtime scripts
COPY --chown=appuser:appuser app/ /app/app/
COPY --chown=appuser:appuser scripts/ /app/scripts/
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh

# Ensure entrypoint script is executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Document exposed HTTP port
EXPOSE 8000

# Container health probe checking the Observable Health Endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/api/v1/health" || exit 1

# Container boot sequence: run database migrations followed by production uvicorn
ENTRYPOINT ["/app/entrypoint.sh"]
