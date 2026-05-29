#!/bin/bash
set -e

echo "==> Waiting for database..."
while ! python -c "
import psycopg2
try:
    conn = psycopg2.connect(
        dbname='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}',
        host='${DB_HOST}',
        port='${DB_PORT}'
    )
    conn.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; do
    sleep 1
done

echo "==> Enabling pgvector extension..."
python -c "
import psycopg2
conn = psycopg2.connect(
    dbname='${DB_NAME}',
    user='${DB_USER}',
    password='${DB_PASSWORD}',
    host='${DB_HOST}',
    port='${DB_PORT}'
)
conn.autocommit = True
cur = conn.cursor()
cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
cur.close()
conn.close()
print('pgvector extension enabled.')
"

echo "==> Making migrations..."
python manage.py makemigrations --noinput

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "==> Starting development server..."
python manage.py runserver 0.0.0.0:8000
