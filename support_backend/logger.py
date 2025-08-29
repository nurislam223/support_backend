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

    # JSON логгер для Elasticsearch
    json_handler = RotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.json.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    logger.addHandler(json_handler)

    # Стандартный логгер для текстовых логов (оставляем для обратной совместимости)
    text_handler = RotatingFileHandler(
        filename="app.log",  # корневой app.log
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    text_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    text_handler.setFormatter(text_formatter)
    logger.addHandler(text_handler)

    # Console handler для дебага
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def log_request(user: str, method: str, endpoint: str, status: int,
                details: str = "", request_body: dict = None, response_body: dict = None):
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

    logger = logging.getLogger("app")
    logger.info(json.dumps(log_data))


# Инициализация при импорте
logger = setup_logger()