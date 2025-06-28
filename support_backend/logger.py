import logging
from logging.handlers import RotatingFileHandler
import os


# --- Настройка директории для логов ---
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)


# --- Формат лога ---
LOG_FORMAT = "%(asctime)s - %(levelname)s - [User: %(user)s] [Method: %(method)s] [Endpoint: %(endpoint)s] [Details: %(message)s]"


# --- Создаем кастомный фильтр для добавления своих атрибутов в log record ---
class ContextualFilter(logging.Filter):
    def filter(self, record):
        # Устанавливаем значения по умолчанию, если не переданы
        if not hasattr(record, 'user'):
            record.user = '-'
        if not hasattr(record, 'method'):
            record.method = '-'
        if not hasattr(record, 'endpoint'):
            record.endpoint = '-'
        return True


# --- Инициализация логгера ---
def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Очищаем старые обработчики (если были)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Форматтер
    formatter = logging.Formatter(LOG_FORMAT)

    # Файл-логгер
    file_handler = RotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,  # 10 МБ
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Консольный логгер
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Добавляем фильтр
    logger.addFilter(ContextualFilter())

    return logger


# --- Функция для логирования запросов ---
def log_request(user: str, method: str, endpoint: str, details: str = "", body: dict = None):
    extra = {
        "user": user,
        "method": method,
        "endpoint": endpoint
    }

    # Если есть тело запроса — добавим его к сообщению
    if body:
        details += f" Body: {body}"

    logging.info(details, extra=extra)


# --- Пример использования ---
if __name__ == "__main__":
    logger = setup_logger()

    # Пример лога с телом запроса
    log_request(
        user="admin",
        method="POST",
        endpoint="/api/users",
        details="User created",
        body={"username": "john_doe", "email": "john@example.com"}
    )

    # Пример GET-запроса без тела
    log_request(
        user="guest",
        method="GET",
        endpoint="/api/status",
        details="System status checked"
    )