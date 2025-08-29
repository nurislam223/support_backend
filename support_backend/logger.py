import logging
import json
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler
from typing import Any

LOG_DIR = "logs"
LOG_FILE_PATH = os.path.join(LOG_DIR, "app.json.log")

# Создаем папку для логов
os.makedirs(LOG_DIR, exist_ok=True)

SENSITIVE_KEYS = {"password", "passwd", "secret", "token", "api_key", "authorization", "refresh_token"}


def mask_sensitive_data(data, keys=SENSITIVE_KEYS):
    if isinstance(data, dict):
        return {
            k: "***MASKED***" if k.lower() in keys else mask_sensitive_data(v, keys)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [mask_sensitive_data(item, keys) for item in data]
    else:
        return data


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        try:
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

            # Добавляем extra данные если они есть
            if hasattr(record, 'extra_data'):
                log_data.update(record.extra_data)

            return json.dumps(log_data, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": "failed to serialize log", "message": record.getMessage()})


def setup_logger():
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Очищаем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # === 1. File Handler (JSON) ===
    try:
        file_handler = RotatingFileHandler(
            filename=LOG_FILE_PATH,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error creating file handler: {e}")

    # === 2. Console Handler ===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Также настраиваем конкретный логгер для приложения
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)

    # Тестовая запись
    app_logger.info("Logger setup completed")

    return app_logger


def log_request(
        user: str,
        method: str,
        endpoint: str,
        status: int,
        details: str = "",
        request_body: Any = None,
        response_body: Any = None
):
    logger = logging.getLogger("app")

    extra_data = {
        "user": user,
        "method": method,
        "endpoint": endpoint,
        "status_code": status,
        "details": details,
        "request_body": request_body,
        "response_body": response_body,
        "log_type": "http_request"
    }

    # Создаем новую запись с extra данными
    log_record = logging.LogRecord(
        name="app",
        level=logging.INFO,
        pathname=__file__,
        lineno=0,
        msg=f"HTTP {method} {endpoint} - {status}",
        args=(),
        exc_info=None
    )
    log_record.extra_data = extra_data

    logger.handle(log_record)