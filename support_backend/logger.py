import logging
from logging.handlers import RotatingFileHandler
import os
import json
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    # Очищаем существующие handlers чтобы избежать дублирования
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # JSON формат для Elasticsearch
    file_handler = RotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.json.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )

    # Простой handler для консоли
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_request(user: str, method: str, endpoint: str, status: int, details: str = "", request_body: dict = None,
                response_body: dict = None):
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "service": "support-backend",
        "type": "http_request",
        "user": user,
        "method": method,
        "endpoint": endpoint,
        "status_code": status,
        "details": details,
        "request_body": request_body,
        "response_body": response_body,
        "log_type": "application"
    }

    # Убираем None значения для чистоты JSON
    log_data = {k: v for k, v in log_data.items() if v is not None}

    logger = logging.getLogger("app")
    logger.info(json.dumps(log_data))


# Инициализируем логгер при импорте
logger = setup_logger()

# --- Пример использования ---
if __name__ == "__main__":
    # Пример лога с телом запроса
    log_request(
        user="admin",
        method="POST",
        endpoint="/api/users",
        status=201,
        details="User created successfully",
        request_body={"username": "john_doe", "email": "john@example.com"},
        response_body={"id": 123, "username": "john_doe"}
    )