FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies for scipy and ML packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (full ML stack)
COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir "numpy>=1.24.0,<1.27.0" && \
    pip install --no-cache-dir "scipy>=1.11.0,<1.12.0" && \
    pip install --no-cache-dir "scikit-learn>=1.3.0,<1.4.0" && \
    pip install --no-cache-dir "statsmodels>=0.14.0,<0.15.0" && \
    pip install --no-cache-dir celery redis sqlalchemy "psycopg[binary]" boto3 "sentry-sdk[celery]"

# Copy application code (worker needs access to backend for DB models)
COPY backend ./backend
COPY worker ./worker

ENV REDIS_URL=redis://redis:6379/0

CMD ["celery", "-A", "worker.app.celery_app:celery_app", "worker", "--loglevel=info"]
