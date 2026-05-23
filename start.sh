#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Démarrage du backend..."
cd "$ROOT/backend"
nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!

echo "▶ Démarrage du frontend..."
cd "$ROOT/frontend"
nohup node node_modules/vite/bin/vite.js > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!

echo "  Backend PID : $BACKEND_PID  (logs : /tmp/backend.log)"
echo "  Frontend PID: $FRONTEND_PID  (logs : /tmp/frontend.log)"

# Attendre que les deux soient prêts
echo -n "  En attente..."
for i in $(seq 1 15); do
    sleep 1
    BACK_OK=false
    FRONT_OK=false
    curl -sf http://localhost:8000/health > /dev/null 2>&1 && BACK_OK=true
    curl -sf http://localhost:5173 > /dev/null 2>&1 && FRONT_OK=true
    if $BACK_OK && $FRONT_OK; then
        echo ""
        echo "✓ Backend  → http://localhost:8000"
        echo "✓ Frontend → http://localhost:5173"
        exit 0
    fi
    echo -n "."
done

echo ""
echo "⚠ Timeout — vérifiez /tmp/backend.log et /tmp/frontend.log"
exit 1
