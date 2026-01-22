#!/bin/bash
# Lint the entire portfolio tracker project with ruff

set -e

echo "🔍 Linting backend..."
cd backend && ruff check . && cd ..

echo ""
echo "🔍 Linting airflow DAGs..."
docker exec airflow_52c716-scheduler-1 ruff check /usr/local/airflow/dags/ 2>&1 || echo "⚠️  Airflow container not running"

echo ""
echo "✅ Linting complete!"
