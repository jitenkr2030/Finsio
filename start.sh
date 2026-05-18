#!/bin/bash
set -e

cd /home/runner/workspace/backend

export DJANGO_SETTINGS_MODULE=finsio.settings.development

echo "Running migrations..."
python3 manage.py migrate --run-syncdb

echo "Starting Django development server on 0.0.0.0:5000..."
python3 manage.py runserver 0.0.0.0:5000
