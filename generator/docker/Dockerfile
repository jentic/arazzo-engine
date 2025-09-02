FROM python:3.13-slim AS base

LABEL maintainer="vladimir@jentic.com" \
      org.opencontainers.image.authors="sophie@jentic.com" \
      org.opencontainers.image.url="https://ghcr.io/jentic/arazzo-generator" \
      org.opencontainers.image.source="https://github.com/jentic/arazzo-engine/tree/main/generator/docker" \
      org.opencontainers.image.description="Arazzo Generator Docker image"  \
      org.opencontainers.image.licenses="Apache-2.0"

WORKDIR /app
    
# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
    
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
    
# Install pip
RUN python -m pip install --upgrade pip
    
# Install PDM (project uses PDM for dependency management)
RUN pip install --no-cache-dir pdm
    
# Copy only the metadata first – enables Docker layer caching
COPY pyproject.toml pdm.lock ./
    
# Install production dependencies (no dev deps, no editable mode)
# Export locked prod deps to requirements.txt and install with pip (no venv)
RUN pdm export --prod --without-hashes -o requirements.txt \
    && pip install --no-cache-dir -r requirements.txt
    
# Copy the source code
COPY . .
    
# Create a non-root user
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser
    
# Expose the API port
EXPOSE 8000
    
# Default command runs the API server
CMD ["uvicorn", "arazzo_generator.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
