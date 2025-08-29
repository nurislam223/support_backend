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

    # Удаляем старые обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        print(f"🗑️ Удалён handler: {handler}")  # Отладка

    # Создаём папку
    LOG_DIR = "logs"
    os.makedirs(LOG_DIR, exist_ok=True)
    print(f"📁 Папка {LOG_DIR} существует: {os.path.exists(LOG_DIR)}")

    # JSON handler
    json_log_path = os.path.join(LOG_DIR, "app.json.log")
    try:
        json_handler = RotatingFileHandler(
            filename=json_log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        logger.addHandler(json_handler)
        print(f"✅ JSON handler добавлен: {json_handler}")
        print(f"📄 JSON лог будет писаться в: {json_log_path}")
    except Exception as e:
        print(f"❌ Ошибка при создании JSON handler: {e}")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    print(f"✅ Console handler добавлен")

    # Проверим, можем ли мы записать
    logger.info("🔧 setup_logger: тестовая запись в логгер 'app'")

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
    print("🎯 log_request вызван!")  # ← ЭТО ДОЛЖНО БЫТЬ В КОНСОЛИ

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
    log_data = {k: v for k, v in log_data.items() if v is not None}

    json_line = json.dumps(log_data, ensure_ascii=False)

    # Пишем в логгер "app"
    json_logger = logging.getLogger("app")
    print(f"📝 Пишем в логгер 'app': {json_line}")  # Отладка
    print(f"📊 Handlers у логгера 'app': {json_logger.handlers}")  # Отладка

    json_logger.info(json_line)

    # Текстовый лог
    text_logger = logging.getLogger("text")
    text_logger.info(
        f"[User: {user}] [Method: {method}] [Endpoint: {endpoint}] [Status: {status}] [Details: {details}]"
    )
