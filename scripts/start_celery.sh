#!/bin/bash
# Start Celery worker and beat scheduler for local development
#
# This runs both:
# - Celery worker (processes tasks)
# - Celery beat (schedules recurring tasks every 6 hours)
#
# Usage:
#   ./scripts/start_celery.sh

set -e

echo "🚀 Starting AlpMark Celery Worker + Beat Scheduler"
echo ""

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ ERROR: Redis is not running!"
    echo "   Start Redis first:"
    echo "   brew services start redis"
    echo ""
    exit 1
fi

echo "✅ Redis is running"
echo ""

# Set environment
export DATABASE_URL="${DATABASE_URL:-postgresql://sudeeppemmaraju@localhost:5432/alpmark_dev}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

echo "📊 Configuration:"
echo "   Database: ${DATABASE_URL}"
echo "   Redis: ${REDIS_URL}"
echo ""

# Kill any existing Celery processes
echo "🧹 Cleaning up existing Celery processes..."
pkill -f "celery.*alpmark_worker" || true
sleep 1

# Create log directory
mkdir -p logs

echo "🎯 Starting services..."
echo ""

# Start Celery worker in background
echo "   ▶️  Starting Celery worker..."
celery -A worker.app.celery_app worker \
    --loglevel=info \
    --logfile=logs/celery_worker.log \
    --detach

# Start Celery beat in background
echo "   ▶️  Starting Celery beat scheduler..."
celery -A worker.app.celery_app beat \
    --loglevel=info \
    --logfile=logs/celery_beat.log \
    --detach

sleep 2

echo ""
echo "✅ Celery services started!"
echo ""
echo "📋 Scheduled Tasks:"
echo "   • Demo data generation: Every 6 hours"
echo "   • Optimization engine: Every 6 hours"
echo "   • Connector sync: Every 15 minutes"
echo "   • KPI computation: Every 4 hours"
echo ""
echo "📊 Monitoring:"
echo "   Worker log:  tail -f logs/celery_worker.log"
echo "   Beat log:    tail -f logs/celery_beat.log"
echo ""
echo "🛑 To stop:"
echo "   ./scripts/stop_celery.sh"
echo ""
