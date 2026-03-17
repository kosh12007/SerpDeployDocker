#!/bin/sh
# =============================================================
# Скрипт запуска Flask-приложения в Docker-контейнере
# Ожидает готовности MySQL через Python (работает в любом sh)
# затем запускает gunicorn
# =============================================================

set -e

# Хост и порт базы данных (берём из переменных окружения)
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-serp_user}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-serp_db}"

# Максимальное время ожидания MySQL (секунды)
MAX_WAIT=120
ELAPSED=0

echo "⏳ Ожидаем готовности MySQL на ${DB_HOST}:${DB_PORT}..."

# Используем Python для проверки подключения к MySQL
# (Python уже есть в контейнере, не нужен netcat или bash /dev/tcp)
until python -c "
import socket, sys
try:
    s = socket.create_connection(('${DB_HOST}', ${DB_PORT}), timeout=3)
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    if [ "${ELAPSED}" -ge "${MAX_WAIT}" ]; then
        echo "❌ MySQL не поднялся за ${MAX_WAIT} секунд. Выход."
        exit 1
    fi
    echo "   Ожидание MySQL... (${ELAPSED}/${MAX_WAIT} сек)"
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

echo "✅ MySQL порт доступен! Даём ещё 3 сек для инициализации..."
sleep 3

echo "🚀 Запускаем gunicorn..."

# Количество воркеров gunicorn
WORKERS="${GUNICORN_WORKERS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-120}"

# serp:application — модуль serp.py, объект application из app/__init__.py
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers "${WORKERS}" \
    --timeout "${TIMEOUT}" \
    --log-level info \
    --access-logfile /app/logs/gunicorn_access.log \
    --error-logfile /app/logs/gunicorn_error.log \
    "serp:application"
