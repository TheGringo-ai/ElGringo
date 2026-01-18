# 🚀 AI TEAM PLATFORM - ULTIMATE APPLICATION GENERATOR
# Multi-stage Docker build optimized for production deployment
# Supports Google Cloud Run, AWS Lambda, Azure Functions, and Kubernetes

# =============================================================================
# Stage 1: Build Dependencies
# =============================================================================
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    musl-dev \
    libffi-dev \
    openssl \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Production Runtime
# =============================================================================
FROM python:3.11-slim as production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get autoremove -y \
    && apt-get autoclean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r aiplatform && useradd -r -g aiplatform aiplatform

# Create application directories
WORKDIR /app
RUN mkdir -p /app/templates /app/static /app/logs /app/data \
    && chown -R aiplatform:aiplatform /app

# Copy application code
COPY main.py .
COPY requirements.txt .

# Copy templates and static files (create if they don't exist)
RUN mkdir -p templates static

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV HOST=0.0.0.0
ENV WORKERS=1
ENV WORKER_CLASS=uvicorn.workers.UvicornWorker
ENV LOG_LEVEL=info
ENV AI_PLATFORM_ENV=production

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Switch to non-root user
USER aiplatform

# Expose port
EXPOSE 8080

# Command to run the application
CMD python main.py

# =============================================================================
# Stage 3: Development Environment (Optional)
# =============================================================================
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    postgresql-client \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    black \
    flake8 \
    mypy

# Development environment variables
ENV AI_PLATFORM_ENV=development
ENV LOG_LEVEL=debug

# Switch back to aiplatform user
USER aiplatform

# Development command with hot reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# =============================================================================
# Metadata and Labels
# =============================================================================
LABEL maintainer="Fred Taylor <fred@aiplatform.com>"
LABEL version="1.0.0"
LABEL description="AI Team Platform - Ultimate Application Generator"
LABEL org.opencontainers.image.source="https://github.com/fredtaylor/AITeamPlatform"
LABEL org.opencontainers.image.documentation="https://docs.aiplatform.com"
LABEL org.opencontainers.image.licenses="MIT"
LABEL ai.platform.value="$250M+"
LABEL ai.platform.models="5"
LABEL ai.platform.capabilities="application-generation,deployment,management"