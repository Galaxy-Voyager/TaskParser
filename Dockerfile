FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=2.3.2 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_HOME="/opt/poetry"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-root --only main

# Copy project files
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Create non-root user
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appgroup /app
USER appuser

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
