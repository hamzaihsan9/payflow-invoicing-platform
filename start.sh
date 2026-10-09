#!/usr/bin/env bash
# ==============================================================================
# PayFlow Pro — Development & Standalone Boot Script
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== Booting PayFlow Services ==="

# 1. Start Node.js Event Worker in background
echo "-> Starting Node.js Worker on port 5001..."
node worker-service/server.js > /tmp/payflow-worker.log 2>&1 &
WORKER_PID=$!
echo "   Node worker started (PID: $WORKER_PID)"

# 2. Start FastAPI Backend in background
echo "-> Starting FastAPI Backend on port 8000..."
PYTHONPATH="$DIR/backend/venv/lib/python3.14/site-packages:$DIR/backend" \
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/payflow-backend.log 2>&1 &
BACKEND_PID=$!
echo "   FastAPI backend started (PID: $BACKEND_PID)"

sleep 2

# Verify Health
echo "=== Health Diagnostics ==="
curl -s http://127.0.0.1:8000/health || echo "Backend initializing..."
echo ""
curl -s http://127.0.0.1:5001/health || echo "Worker initializing..."
echo ""

echo "--------------------------------------------------"
echo "PayFlow is live!"
echo "• Dashboard:  file://$DIR/frontend/index.html"
echo "• API Docs:   http://localhost:8000/docs"
echo "• Client App: file://$DIR/client-portal-vue/index.html"
echo "--------------------------------------------------"
echo "To stop services: kill $BACKEND_PID $WORKER_PID"
