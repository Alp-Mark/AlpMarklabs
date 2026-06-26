FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies (minimal set for Railway)
COPY worker/requirements-railway.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (worker needs access to backend for DB models)
COPY backend ./backend
COPY worker ./worker

ENV REDIS_URL=redis://redis:6379/0

CMD ["celery", "-A", "worker.app.celery_app:celery_app", "worker", "--loglevel=info"]
