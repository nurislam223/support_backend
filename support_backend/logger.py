import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = "%(asctime)s - %(levelname)s - [User: %(user)s] [Method: %(method)s] [Endpoint: %(endpoint)s] [Status: %(status)s] [Details: %(message)s]"

class ContextualFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, 'user'):
            record.user = '-'
        if not hasattr(record, 'method'):
            record.method = '-'
        if not hasattr(record, 'endpoint'):
            record.endpoint = '-'
        if not hasattr(record, 'status'):
            record.status = '-'
        return True

def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        filename=os.path.join(LOG_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.addFilter(ContextualFilter())
    return logger

def log_request(user: str, method: str, endpoint: str, status: int, details: str = "", body: dict = None):
    extra = {
        "user": user,
        "method": method,
        "endpoint": endpoint,
        "status": status
    }

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