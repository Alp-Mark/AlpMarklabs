web: uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
release: alembic -c backend/alembic.ini upgrade head
worker: celery -A worker.app.celery_app worker --loglevel=info
beat: celery -A worker.app.celery_app beat --loglevel=info
