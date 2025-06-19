#!/bin/sh
set -e

# Генерируем миграцию (опционально)
alembic revision --autogenerate -m "Auto-generated migration"

# Применяем миграции
echo "Запускаем миграции..."
alembic upgrade head

# Запускаем приложение
echo "Запускаем FastAPI..."
exec "$@"
