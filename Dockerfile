# syntax=docker/dockerfile:1

# Backend image (FastAPI API + Celery worker share this image)
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer is cached across code changes
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Application code (frontend/, landing/, tests/ and .env are excluded by .dockerignore)
COPY . .

# Run as non-root user
RUN adduser --system --uid 1001 --group app && chown -R app:app /app
USER app

# Port is read from BACKEND_PORT (supplied by .env via docker compose)
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${BACKEND_PORT}"]
