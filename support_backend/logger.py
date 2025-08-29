# logger.py — ОТЛАДОЧНАЯ ВЕРСИЯ
import logging
import json
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler
from typing import Any

LOG_DIR = "logs"
LOG_FILE_PATH = os.path.join(LOG_DIR, "app.json.log")

print(f"📁 LOG_DIR: {os.path.abspath(LOG_DIR)}")
print(f"📄 LOG_FILE_PATH: {os.path.abspath(LOG_FILE_PATH)}")

# Проверяем права на запись
try:
    os.makedirs(LOG_DIR, exist_ok=True)
    test_file = os.path.join(LOG_DIR, ".test_write")
    with open(test_file, 'w') as f:
        f.write("test")
    os.remove(test_file)
    print("✅ Папка logs доступна для записи")
except Exception as e:
    print(f"❌ Нет прав на запись в папку {LOG_DIR}: {e}")

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


class JSONFormatter:
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
            if hasattr(record, "extra"):
                log_data.update(record.extra)

            # Пробуем сериализовать
            result = json.dumps(log_data, ensure_ascii=False, default=str, indent=None)
            print(f"🟢 JSON успешно сериализован: {result[:200]}...")  # Отладка
            return result
        except Exception as e:
            print(f"🔴 Ошибка в JSONFormatter: {e}")
            return json.dumps({"error": "failed to serialize log", "msg": record.getMessage()})


def setup_logger():
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)

    # Удаляем старые обработчики
    for handler in logger.handlers[:]:
        print(f"🗑️ Удалён handler: {handler}")
        logger.removeHandler(handler)

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
        logger.addHandler(file_handler)
        print(f"✅ File handler добавлен: {file_handler}")
    except Exception as e:
        print(f"❌ Ошибка при добавлении file handler: {e}")

    # === 2. Console Handler ===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    print(f"✅ Console handler добавлен")

    # Тестовая запись
    print("🔧 Выполняем тестовую запись в логгер 'app'...")
    logger.info("Test log entry", extra={"test": "setup_logger completed"})
    print("✅ Тестовая запись отправлена в логгер")

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
    logger = logging.getLogger("app")
    print(f"🎯 log_request вызван: {method} {endpoint} → status {status}")

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

    try:
        logger.info("HTTP request completed", extra=extra)
        print("🟢 Лог успешно отправлен в logger")
    except Exception as e:
        print(f"🔴 Ошибка при логировании: {e}")