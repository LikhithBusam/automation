# ============================================================================
# Production Dockerfile for Main Application
# Multi-stage build for optimized size and security
# ============================================================================

# ============================================================================
# Stage 1: Builder - Install dependencies and compile Python packages
# ============================================================================
FROM python:3.11-slim as builder

LABEL maintainer="automaton-devops@example.com"
LABEL description="AutoGen Development Assistant - Application Builder"
LABEL version="2.0.0"

# Set build arguments
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=2.0.0

# Set environment variables for build
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    git \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ============================================================================
# Stage 2: Runtime - Minimal production image
# ============================================================================
FROM python:3.11-slim

# Metadata labels
LABEL maintainer="automaton-devops@example.com"
LABEL description="AutoGen Development Assistant - Production Application"
LABEL org.opencontainers.image.title="AutoGen Development Assistant"
LABEL org.opencontainers.image.description="Multi-agent AI system for code analysis and development automation"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app \
    APP_USER=appuser \
    APP_GROUP=appgroup \
    APP_UID=1000 \
    APP_GID=1000 \
    DEBIAN_FRONTEND=noninteractive \
    # Application ports
    APP_PORT=8000 \
    METRICS_PORT=9090

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r ${APP_GROUP} -g ${APP_GID} && \
    useradd -r -g ${APP_GROUP} -u ${APP_UID} -m -d ${APP_HOME} -s /sbin/nologin ${APP_USER}

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create application directory structure
WORKDIR ${APP_HOME}

# Copy application code with proper ownership
COPY --chown=${APP_USER}:${APP_GROUP} . ${APP_HOME}/

# Create necessary directories with proper permissions
RUN mkdir -p ${APP_HOME}/logs \
             ${APP_HOME}/data \
             ${APP_HOME}/data/memory \
             ${APP_HOME}/data/teachable \
             ${APP_HOME}/data/codebase_index \
             ${APP_HOME}/models_cache \
             ${APP_HOME}/workspace \
             ${APP_HOME}/state \
    && chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}

# Switch to non-root user
USER ${APP_USER}

# Expose application ports
# 8000 - Main application API
# 9090 - Prometheus metrics
EXPOSE ${APP_PORT} ${METRICS_PORT}

# Health check configuration
HEALTHCHECK --interval=30s \
            --timeout=10s \
            --start-period=40s \
            --retries=3 \
            CMD curl -f http://localhost:${APP_PORT}/health || exit 1

# Default command
CMD ["python", "main.py"]

