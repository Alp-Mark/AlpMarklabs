#!/bin/bash
# Stop Celery worker and beat scheduler
#
# Usage:
#   ./scripts/stop_celery.sh

echo "🛑 Stopping AlpMark Celery Services..."
echo ""

# Kill Celery worker
echo "   Stopping Celery worker..."
pkill -f "celery.*worker.*alpmark_worker" && echo "   ✅ Worker stopped" || echo "   ℹ️  Worker not running"

# Kill Celery beat
echo "   Stopping Celery beat..."
pkill -f "celery.*beat.*alpmark_worker" && echo "   ✅ Beat stopped" || echo "   ℹ️  Beat not running"

echo ""
echo "✅ Cleanup complete"
echo ""
