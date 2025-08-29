# logger.py
import logging
import json
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler
from typing import Any

# === НАСТРОЙКИ ===
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOG_DIR, "app.json.log")

# Чувствительные поля
SENSITIVE_KEYS = {"password", "passwd", "secret", "token", "api_key", "authorization", "refresh_token"}


def mask_sensitive_data(data, keys=SENSITIVE_KEYS):
    """Рекурсивно маскирует чувствительные данные."""
    if isinstance(data, dict):
        return {
            k: "***MASKED***" if k.lower() in keys else mask_sensitive_data(v, keys)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item, keys) for item in data]
    else:
        return data


class JSONFormatter:
    """Кастомный JSON-форматтер для логов"""
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "support-backend",
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        # Дополнительные поля из extra
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data, ensure_ascii=False, default=str)


def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    # Очищаем старые обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # === 1. JSON в файл (для Logstash) ===
    try:
        file_handler = RotatingFileHandler(
            filename=LOG_FILE_PATH,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        print(f"✅ JSON логгер настроен: {LOG_FILE_PATH}")
    except Exception as e:
        print(f"❌ Ошибка при создании file handler: {e}")

    # === 2. Консоль (опционально, для отладки) ===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    print(f"✅ Console handler добавлен")

    # Тестовая запись
    logger.info("🔧 Logger initialized", extra={"event": "startup"})

    return logger


def log_request(
    user: str,
    method: str,
    endpoint: str,
    status: int,
    details: str = "",
    request_body: Any = None,
    response_body: Any = None
):
    """Логирует HTTP-запрос в JSON-файл"""
    logger = logging.getLogger("app")

    # Маскируем чувствительные данные
    safe_request = mask_sensitive_data(request_body)
    safe_response = mask_sensitive_data(response_body)

    extra = {
        "extra": {
            "user": user,
            "method": method,
            "endpoint": endpoint,
            "status_code": status,
            "details": details,
            "request_body": safe_request,
            "response_body": safe_response,
            "log_type": "http_request"
        }
    }

    logger.info("HTTP request completed", extra=extra)