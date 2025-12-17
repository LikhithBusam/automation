# Multi-stage Dockerfile for Production Deployment
# Optimized for size and security

# ============================================================================
# Stage 1: Builder - Install dependencies and compile Python packages
# ============================================================================
FROM python:3.11-slim as builder

LABEL maintainer="your-email@example.com"
LABEL description="Intelligent Development Assistant - Builder Stage"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    # Application settings
    APP_HOME=/app \
    APP_USER=appuser \
    APP_GROUP=appgroup \
    # Security settings
    DEBIAN_FRONTEND=noninteractive

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r ${APP_GROUP} && \
    useradd -r -g ${APP_GROUP} -u 1000 -m -s /sbin/nologin ${APP_USER}

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directory
WORKDIR ${APP_HOME}

# Copy application code
COPY --chown=${APP_USER}:${APP_GROUP} . ${APP_HOME}/

# Create necessary directories
RUN mkdir -p ${APP_HOME}/logs \
             ${APP_HOME}/data \
             ${APP_HOME}/models_cache \
             ${APP_HOME}/workspace && \
    chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}

# Switch to non-root user
USER ${APP_USER}

# Expose ports
# 8000 - Main application
# 3000 - GitHub MCP Server
# 3001 - Filesystem MCP Server
# 3002 - Memory MCP Server
# 3003 - Slack MCP Server
# 9090 - Prometheus metrics
EXPOSE 8000 3000 3001 3002 3003 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden)
CMD ["python", "main.py"]
