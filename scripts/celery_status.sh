#!/bin/bash
# Check Celery worker and beat scheduler status
#
# Usage:
#   ./scripts/celery_status.sh

echo "📊 AlpMark Celery Status"
echo ""

# Check Redis
echo "🔴 Redis:"
if redis-cli ping > /dev/null 2>&1; then
    echo "   ✅ Running"
else
    echo "   ❌ Not running (required for Celery)"
fi
echo ""

# Check Celery Worker
echo "⚙️  Celery Worker:"
if pgrep -f "celery.*worker.*alpmark_worker" > /dev/null; then
    echo "   ✅ Running (PID: $(pgrep -f 'celery.*worker.*alpmark_worker'))"
    if [ -f logs/celery_worker.log ]; then
        echo "   📝 Last activity:"
        tail -n 3 logs/celery_worker.log | sed 's/^/      /'
    fi
else
    echo "   ❌ Not running"
fi
echo ""

# Check Celery Beat
echo "⏰ Celery Beat:"
if pgrep -f "celery.*beat.*alpmark_worker" > /dev/null; then
    echo "   ✅ Running (PID: $(pgrep -f 'celery.*beat.*alpmark_worker'))"
    if [ -f logs/celery_beat.log ]; then
        echo "   📝 Last scheduled:"
        tail -n 3 logs/celery_beat.log | sed 's/^/      /'
    fi
else
    echo "   ❌ Not running"
fi
echo ""

# Show scheduled tasks
echo "📋 Scheduled Tasks:"
echo "   • demo-data-generation-6h:  Every 6 hours"
echo "   • optimization-execution:   Every 6 hours"
echo "   • connector-sync-15min:     Every 15 minutes"
echo "   • kpi-computation-4h:       Every 4 hours"
echo ""

# Quick help
echo "💡 Commands:"
echo "   Start:    ./scripts/start_celery.sh"
echo "   Stop:     ./scripts/stop_celery.sh"
echo "   Trigger:  python3 scripts/trigger_demo_data.py"
echo "   Logs:     tail -f logs/celery_worker.log"
echo ""
