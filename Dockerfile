# Lazarus Protocol — Production Dockerfile
# Multi-stage build for optimized container size

FROM python:3.11-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies
COPY pyproject.toml setup.py requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir .

# --- Production Stage ---
FROM python:3.11-slim-bookworm AS production

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    # Required for cryptography
    libssl3 \
    ca-certificates \
    # Optional: for debugging
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r lazarus && useradd -r -g lazarus lazarus

# Create app directory
RUN mkdir -p /app && chown lazarus:lazarus /app

# Copy virtual environment from builder
COPY --from=builder --chown=lazarus:lazarus /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LAZARUS_HOME="/app" \
    LAZARUS_CONFIG_DIR="/app/config" \
    LAZARUS_DATA_DIR="/app/data"

# Switch to non-root user
USER lazarus

# Create data directories
RUN mkdir -p /app/config /app/data /app/logs

# Copy application code
COPY --chown=lazarus:lazarus . /app

# Set working directory
WORKDIR /app

# Expose ports
EXPOSE 8000  # Web interface
EXPOSE 8080  # API server

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["lazarus", "run", "--host", "0.0.0.0", "--port", "8000"]

# --- Development Stage ---
FROM python:3.11-slim-bookworm AS development

# Install development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    curl \
    vim \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r lazarus && useradd -r -g lazarus lazarus

# Create app directory
RUN mkdir -p /app && chown lazarus:lazarus /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LAZARUS_HOME="/app" \
    LAZARUS_CONFIG_DIR="/app/config" \
    LAZARUS_DATA_DIR="/app/data"

# Switch to non-root user
USER lazarus

# Copy application code
COPY --chown=lazarus:lazarus . /app

# Set working directory
WORKDIR /app

# Install in development mode
RUN pip install --user --no-cache-dir -e .[dev]

# Expose ports
EXPOSE 8000 8001

# Default command for development
CMD ["lazarus", "run", "--host", "0.0.0.0", "--port", "8000", "--reload"]