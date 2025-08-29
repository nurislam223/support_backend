import logging
import json
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    # Очистка предыдущих handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # JSON логгер для Elasticsearch - ТОЛЬКО JSON!
    json_handler = RotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.json.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    # Важно: НЕ ставим formatter для JSON!
    logger.addHandler(json_handler)

    # Отдельный логгер для текстовых логов
    text_logger = logging.getLogger("text")
    text_logger.setLevel(logging.INFO)
    for handler in text_logger.handlers[:]:
        text_logger.removeHandler(handler)

    text_handler = RotatingFileHandler(
        filename="app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    text_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    text_handler.setFormatter(text_formatter)
    text_logger.addHandler(text_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    text_logger.addHandler(console_handler)

    return logger

SENSITIVE_KEYS = {"password", "passwd", "secret", "token", "api_key", "authorization", "refresh_token"}


def mask_sensitive_data(data, keys=SENSITIVE_KEYS):
    """
    Рекурсивно маскирует чувствительные поля в словаре или списке.
    """
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k.lower() in keys:
                result[k] = "***MASKED***"
            else:
                result[k] = mask_sensitive_data(v, keys)
        return result
    elif isinstance(data, list):
        return [mask_sensitive_data(item, keys) for item in data]
    else:
        return data

def log_request(user: str, method: str, endpoint: str, status: int,
                details: str = "", request_body: dict = None, response_body: dict = None):
    # JSON данные для Elasticsearch
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "service": "support-backend",
        "user": user,
        "method": method,
        "endpoint": endpoint,
        "status_code": status,
        "details": details,
        "request_body": request_body,
        "response_body": response_body,
        "log_type": "http_request"
    }

    # Убираем None значения
    log_data = {k: v for k, v in log_data.items() if v is not None}

    # Пишем JSON в app.json.log
    json_logger = logging.getLogger("app")
    json_logger.info(json.dumps(log_data))

    # Пишем текстовый лог в app.log
    text_logger = logging.getLogger("text")
    text_logger.info(
        f"[User: {user}] [Method: {method}] [Endpoint: {endpoint}] [Status: {status}] [Details: {details}]")


# Инициализация при импорте
logger = setup_logger()