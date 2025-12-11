# --- Stage 1: Build dependencies ---
FROM python:3.11-slim as builder

# Install system dependencies needed for asyncpg (PostgreSQL client)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry and configure paths
ENV POETRY_HOME="/opt/poetry"
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN pip install poetry

# Install the export plugin required for 'poetry export' command
RUN poetry self add poetry-plugin-export

# Copy project files for dependency resolution
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install main dependencies
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
RUN poetry install --no-root --only main

# Create a minimal requirements.txt for the final image
RUN poetry export --without-hashes --output requirements.txt

# --- Stage 2: Final minimal image ---
FROM python:3.11-slim

# Install system dependencies required by final image (PostgreSQL client)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set final working directory
WORKDIR /app

# Copy generated requirements.txt and install them efficiently
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose port
EXPOSE 8000