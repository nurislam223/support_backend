#!/bin/sh
set -e

# Ожидаем доступности PostgreSQL
echo "Ожидаем поднятия PostgreSQL..."
until pg_isready -h db -p 5432 -U admin ; do
  echo "База данных ещё не готова — ждём..."
  sleep 2
done

echo "База данных готова!"

# Генерируем миграцию (опционально)
alembic revision --autogenerate -m "Auto-generated migration"

# Применяем миграции
echo "Запускаем миграции..."
alembic upgrade head

# Запускаем приложение
echo "Запускаем FastAPI..."
exec "$@"
