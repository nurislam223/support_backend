# Используем официальный образ Python
FROM python:3.11-slim

# Указываем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем зависимости
COPY ./support_backend/requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt
# Копируем исходный код приложения
COPY ./support_backend .

RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY wait-for-db-and-migrate.sh /usr/local/bin/wait-for-db-and-migrate.sh

RUN chmod +x /usr/local/bin/wait-for-db-and-migrate.sh
# Открываем порт 8000 для FastAPI
EXPOSE 8000

# Команда запуска приложения
CMD ["wait-for-db-and-migrate.sh", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
