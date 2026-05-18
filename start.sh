#!/bin/bash
set -e

cd /home/runner/workspace/backend

export DJANGO_SETTINGS_MODULE=finsio.settings.development

echo "Running migrations..."
python3 manage.py migrate --run-syncdb

echo "Starting Django API server on localhost:8000..."
python3 manage.py runserver localhost:8000 &
BACKEND_PID=$!

echo "Starting React frontend on 0.0.0.0:5000..."
cd /home/runner/workspace/frontend
npm run dev &
FRONTEND_PID=$!

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
