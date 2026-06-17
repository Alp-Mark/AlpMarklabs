FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY worker ./worker

ENV REDIS_URL=redis://redis:6379/0

CMD ["celery", "-A", "worker.app.celery_app:celery_app", "worker", "--loglevel=info"]
