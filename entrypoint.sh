#!/bin/bash

set -e

sleep 10

cd /app/src

# Run Alembic migrations
echo "Running Alembic migrations..."
alembic upgrade head

cd ..

uvicorn main:app --host 0.0.0.0 --port 8000
